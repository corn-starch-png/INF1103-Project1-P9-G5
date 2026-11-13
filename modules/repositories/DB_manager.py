# Coordinate the active household, offline drafts, remembered access, and safe switching.
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from .AppPaths import AppPaths
from .JsonRepository import JsonRepository
from .RepositoryFunctions import RepositoryFunctions
from .HouseholdDocument import HouseholdDocument as Doc
from .StorageErrors import CloudUnavailable, HouseholdNotFound, SaveConflict, LocalConflict


class DB_manager:
    # Persistence is injectable so validation never uses real household data.
    def __init__(self, ui, database_dir=None, use_mongo=True, mongo_factory=None, json_factory=None):
        self.ui = ui
        self.database_dir = Path(database_dir) if database_dir else AppPaths.DATABASE_DIR
        self.use_mongo = use_mongo
        self._mongo_factory = mongo_factory or self._create_mongo_repository
        self._local = (json_factory or JsonRepository)(folder=self.database_dir)
        self._repository: RepositoryFunctions | None = None
        self._stores = None
        self._base = None
        self._revision = None
        self._unregistered = False
        self._is_local = True
        self._prepared_resolution = None

    # Delay cloud connection until a household operation needs it.
    @staticmethod
    def _create_mongo_repository():
        from .MongoDBRepository import MongoDBRepository
        return MongoDBRepository()

    # Kept access policy separate so better authentication can be implemented in future.
    def authorize_household(self, household_id):
        return Doc.normalize_id(household_id)

    # Explicit local mode supports offline creation and the current cache.
    def cloud(self) -> RepositoryFunctions:
        if not self.use_mongo:
            raise CloudUnavailable("Cloud access is disabled (USE_MONGO=0).")
        if self._repository is None:
            self._repository = self._mongo_factory()
        return self._repository

    # Bind domain objects to the original cloud version and local revision.
    def _activate(self, bundle):
        # A changed active snapshot invalidates any earlier replacement proposal.
        self._prepared_resolution = None
        self._base = deepcopy(bundle["snapshot"])
        self._unregistered = bundle["state"]["unregistered"]
        self._revision = bundle["state"]["revision"]
        self._stores = Doc.to_stores(bundle["pending"] or self._base)
        return self.stores

    # Detect unsaved edits without including generated timestamps in comparisons.
    def has_changes(self):
        return self._stores is not None and Doc.editable(Doc.from_stores(self._base, self._stores)) != Doc.editable(self._base)

    # Refuse to overwrite another process's revision or silently abandon pending edits.
    def _check_selection(self, bundle, discard):
        actual = bundle["state"]["revision"] if bundle["state"] else None
        if self._base is not None and actual != self._revision:
            raise LocalConflict("Local selection changed in another instance. Your draft remains in memory.")
        pending = bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
        if not discard and (pending or self.has_changes()):
            raise SaveConflict("Save/sync the current household or explicitly discard its edits before switching.")
        return actual

    # Load a target successfully before replacing the one-household local cache.
    def open_household(self, household_id, discard=False):
        household_id = self.authorize_household(household_id)
        with self._local.locked():
            bundle = self._local.read()
            same = bundle["snapshot"] is not None and bundle["snapshot"]["_id"] == household_id
            if self._base is not None and self.has_changes() and not discard:
                raise SaveConflict("Save or discard your in-memory edits before reopening.")
            actual = bundle["state"]["revision"] if bundle["state"] else None
            if self._base is not None and actual != self._revision:
                raise LocalConflict("Local household changed in another instance; your draft remains in memory.")
            if not same:
                self._check_selection(bundle, discard)
            if same and bundle["state"]["unregistered"] and not discard:
                self._is_local = True
                self.ui.send_message("Opening the current local-only household. Use Save/sync to register it in MongoDB.")
                return self._activate(bundle)
            try:
                loaded = self.cloud().load(household_id)
                self._is_local = False
            except CloudUnavailable:
                if not same:
                    raise CloudUnavailable("Cannot switch offline. Only the current cached household is available.")
                self._is_local = True
                if discard:
                    raise CloudUnavailable("Cannot reload cloud data while offline; your draft was retained.")
                self.ui.send_message("MongoDB is unavailable. Opening only this household's current local data.")
                return self._activate(bundle)
            if same and bundle["pending"] is not None and not discard:
                self.ui.send_message("A local draft is available. It retains its original cloud version; use Save/sync to upload or review conflicts.")
                return self._activate(bundle)
            # Merely opening an unchanged household must not invalidate another active session.
            if not (same and bundle["snapshot"] == loaded and bundle["pending"] is None and not bundle["state"]["unregistered"]):
                bundle = self._local.write(loaded, None, False, actual)
            settings = self._local.read_settings()
            if settings and settings["last_household_id"] == household_id:
                self._local.remember(loaded)
            return self._activate(bundle)

    # Offline creation persists first; cloud registration can be retried later.
    def create_household(self, name, discard=False):
        document = Doc.new(name)
        with self._local.locked():
            previous = self._local.read()
            revision = self._check_selection(previous, discard)
            bundle = self._local.write(document, document, True, revision)
            self._activate(bundle)
        self.ui.send_message(f"Household Space created: {document['name']} — {document['_id']}")
        result = self.save()
        if result == "offline":
            self.ui.send_message("This household is local only until its first successful cloud sync. Save the displayed ID; it may change if MongoDB detects a collision.")
        return self.stores

    # Preserve a local draft before cloud writes and never retry with a newer version.
    def save(self):
        if self._base is None:
            raise RuntimeError("Select a household before saving.")
        draft = Doc.from_stores(self._base, self._stores)
        if Doc.size(draft) >= Doc.WARNING_BYTES:
            self.ui.send_message("Household exceeds 8 MiB. Export history and plan separate history storage before 16 MiB; nothing is deleted automatically.")
        with self._local.locked():
            bundle = self._local.read()
            actual = bundle["state"]["revision"] if bundle["state"] else None
            if actual != self._revision or bundle["snapshot"]["_id"] != self._base["_id"]:
                raise LocalConflict("Another instance saved or switched households. Your draft remains in memory; review it before reloading.")
            changed = Doc.editable(draft) != Doc.editable(self._base)
            if not changed and not self._unregistered:
                if bundle["pending"] is not None:
                    bundle = self._local.write(self._base, None, False, self._revision)
                    self._revision = bundle["state"]["revision"]
                    self.ui.send_message("Changes were reverted. The pending draft was cleared; no cloud write was made.")
                else:
                    # Save/sync must acknowledge a no-op instead of silently returning to the menu.
                    self.ui.send_message("No new changes to save since the last successful save.")
                return "unchanged"
            if bundle["pending"] != draft:
                bundle = self._local.write(self._base, draft, self._unregistered, self._revision)
                self._revision = bundle["state"]["revision"]
            try:
                cloud = self.cloud()
                if self._unregistered:
                    for attempt in range(8):
                        try:
                            registered = cloud.create(self._base)
                            break
                        except DuplicateKeyError:
                            self._base["_id"] = Doc.generate_id()
                            draft["_id"] = self._base["_id"]
                            self._stores["household"].household_id = self._base["_id"]
                            bundle = self._local.write(self._base, draft, True, self._revision)
                            self._revision = bundle["state"]["revision"]
                            self.ui.send_message(f"Household ID collision: your new ID is {self._base['_id']}.")
                            if self._local.read_settings():
                                self._local.remember(self._base)
                    else:
                        raise SaveConflict("Could not allocate a unique household ID. Local data is retained.")
                    saved = cloud.save(draft, self._base["version"]) if changed else registered
                else:
                    current = cloud.load(self._base["_id"])
                    if current["version"] == self._base["version"] + 1 and Doc.editable(current) == Doc.editable(draft):
                        saved = current  # The earlier write may have succeeded before its reply was lost.
                    else:
                        saved = cloud.save(draft, self._base["version"])
            except CloudUnavailable as error:
                self._is_local = True
                self.ui.send_message(str(error))
                self.ui.send_message("Your changes are saved on this device and will sync when cloud access is available.")
                self.ui.send_message(f"Pending draft: {self._local.paths['pending']}")
                return "offline"
            bundle = self._local.write(saved, None, False, self._revision)
            self._activate(bundle)
            self._is_local = False
            settings = self._local.read_settings()
            if settings and settings["last_household_id"] == saved["_id"]:
                self._local.remember(saved)
            self.ui.send_message("Your data has been saved to the cloud.")
            return "saved"

    # Return detached comparison data; presentation belongs to the session and IO layers.
    def comparison(self):
        if self._base is None:
            raise HouseholdNotFound("Select a household before reviewing changes.")
        draft = Doc.from_stores(self._base, self._stores)
        current = self.cloud().load(self._base["_id"])
        return {"base": deepcopy(self._base), "draft": draft, "cloud": current}

    # Prepare a version-bound proposal without prompting or writing household data.
    def prepare_food_resolution(self, source):
        if source not in ("local", "cloud"):
            raise ValueError("Choose local or cloud food data.")
        return self._prepare_resolution(source)

    # Bind consent to the current device revision without silently adopting another household.
    def _prepare_resolution(self, source):
        self._prepared_resolution = None
        with self._local.locked():
            bundle = self._local.read()
            if self._base is None or bundle["snapshot"] is None or bundle["snapshot"]["_id"] != self._base["_id"]:
                raise LocalConflict("This device selected another household. Restart to resume that household; this draft was not uploaded.")
            comparison = self.comparison()
            draft, current = comparison["draft"], comparison["cloud"]
            for field in ("name", "household_members"):
                # Local replacement remains food-only; cloud adoption may discard setup profiles.
                if source == "local" and draft[field] != self._base[field] and draft[field] != current[field]:
                    raise SaveConflict("Local household name or member edits also exist. Food-only replacement cannot discard these edits; choose Use cloud data to discard local edits, or keep editing.")
            token = uuid4().hex
            self._prepared_resolution = {**deepcopy(comparison), "token": token,
                                         "revision": bundle["state"]["revision"], "session_revision": self._revision, "source": source}
            return {**comparison, "token": token, "replaces_device_draft": bundle["pending"] is not None and bundle["state"]["revision"] != self._revision}

    # Cancellation invalidates the proposal without touching local or cloud records.
    def cancel_food_resolution(self, token):
        if self._prepared_resolution and self._prepared_resolution["token"] == token:
            self._prepared_resolution = None

    # Apply exactly the confirmed proposal; reject changed local drafts and newer cloud versions.
    def apply_food_resolution(self, token):
        with self._local.locked():
            proposal = self._prepared_resolution
            if proposal is None or proposal["token"] != token:
                raise LocalConflict("The replacement proposal is no longer active. Review the conflict again.")
            self._prepared_resolution = None
            current, draft, source = proposal["cloud"], proposal["draft"], proposal["source"]
            bundle = self._local.read()
            if (self._base is None or not bundle["state"]
                    or bundle["state"]["revision"] != proposal["revision"]
                    or self._revision != proposal["session_revision"]
                    or bundle["snapshot"]["_id"] != current["_id"]
                    or self._base["_id"] != current["_id"]
                    or Doc.from_stores(self._base, self._stores) != draft):
                raise LocalConflict("Local household changed while deciding. No replacement was made.")
            # Only after validating consent may this session use the observed device revision.
            revision = proposal["revision"]
            if source == "cloud":
                latest = self.cloud().load(current["_id"])
                if latest != current:
                    raise SaveConflict("Cloud data changed during confirmation. Review the latest copy before discarding edits.")
                saved = current
            else:
                resolved = deepcopy(current)
                for field in ("fridge", "consumption_history"):
                    resolved[field] = deepcopy(draft[field])
                bundle = self._local.write(current, resolved, False, revision)
                self._activate(bundle)
                revision = self._revision
                saved = self.cloud().save(resolved, current["version"])
            bundle = self._local.write(saved, None, False, revision)
            self._activate(bundle)
            self._is_local = False
            settings = self._local.read_settings()
            if settings and settings["last_household_id"] == saved["_id"]:
                self._local.remember(saved)
            return deepcopy(saved)

    # A failed reload must not grant an old session the new selection's revision.
    def reload_current(self):
        with self._local.locked():
            bundle = self._local.read()
            if bundle["snapshot"] is None:
                raise HouseholdNotFound("There is no current household to reload.")
            loaded = self.cloud().load(bundle["snapshot"]["_id"])
            bundle = self._local.write(loaded, None, False, bundle["state"]["revision"])
            self._is_local = False
            return self._activate(bundle)

    # Expose base without allowing callers to replace manager-owned state.
    @property
    def base(self):
        return deepcopy(self._base)

    # Expose stores without allowing callers to replace manager-owned state.
    @property
    def stores(self):
        return dict(self._stores) if self._stores is not None else None

    # Expose revision without allowing callers to replace manager-owned state.
    @property
    def revision(self):
        return self._revision

    # Expose unregistered without allowing callers to replace manager-owned state.
    @property
    def unregistered(self):
        return self._unregistered

    # Expose is_local without allowing callers to replace manager-owned state.
    @property
    def is_local(self):
        return self._is_local

    # Expose repository without allowing callers to replace manager-owned state.
    @property
    def repository(self):
        return self._repository

    # Expose local without allowing callers to replace manager-owned state.
    @property
    def local(self):
        return self._local

    # Supply a detached local bundle for navigation decisions.
    def read_cache(self):
        return self._local.read()

    # Keep preference persistence behind the data manager boundary.
    def read_preferences(self):
        return self._local.read_settings()

    # Remember a selected household or clear the startup preference.
    def remember(self, document=None):
        self._local.remember(document)

    # Perform storage repair before the session presents navigation choices.
    def prepare_startup(self):
        return self._local.prepare_startup()

    # Restore cached domain objects while retaining their original revision and version.
    def resume_cached(self):
        with self._local.locked():
            bundle = self._local.read()
            if bundle["snapshot"] is None:
                raise HouseholdNotFound("There is no cached household to resume.")
            return self._activate(bundle)

    # Detach only a clean, current selection; never discard pending edits implicitly.
    def clear_selection(self):
        with self._local.locked():
            self._check_selection(self._local.read(), False)
            self._base = self._stores = self._revision = None
            self._unregistered = False

    # Retain existing callers while the dedicated session owns all navigation implementation.
    def session(self):
        from modules.HouseholdSession import HouseholdSession
        return HouseholdSession(self, self.ui)

    # Delegate startup navigation to the session controller.
    def start(self):
        return self.session().start()

    # Delegate household selection to the session controller.
    def select_household(self, switching=False):
        return self.session().select_household(switching)

    # Delegate interactive recovery while save() retains persistence responsibility.
    def save_interactive(self):
        return self.session().save_interactive()

    # Delegate forget choices to the session controller.
    def forget_household(self):
        return self.session().forget_household()
