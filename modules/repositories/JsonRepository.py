# Store only the current household using process locks and recoverable replacements.
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4
from filelock import FileLock
from .AppPaths import AppPaths
from .HouseholdDocument import HouseholdDocument as Doc
from .StorageErrors import HouseholdNotFound, LocalConflict


class JsonRepository:
    # Every process using this folder shares the same lock and revision token.
    def __init__(self, folder=AppPaths.DATABASE_DIR):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.folder / ".household.lock"), timeout=15)
        self.paths = {"snapshot": self.folder / "households/current.json",
                      "pending": self.folder / "pending_households/current.json",
                      "state": self.folder / "sync_state/current.json"}
        self.journal = self.folder / ".household_transaction.json"
        self.settings = self.folder / "device_settings.json"

    # Flush a unique temporary file before replacing its destination atomically.
    @staticmethod
    def atomic_write(path, value):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".household-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    # Missing files are allowed; corrupt household data must not be overwritten.
    @staticmethod
    def read_json(path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as error:
            raise RuntimeError(f"Invalid local JSON: {path.name}. Data was retained.") from error

    # Coordinate reads, saves, and switches under the same process lock.
    @contextmanager
    def locked(self):
        with self.lock:
            self._recover()
            yield

    # Snapshot, pending draft and revision must all belong to the same household.
    @staticmethod
    def validate_bundle(bundle):
        snapshot, pending, state = (bundle[key] for key in ("snapshot", "pending", "state"))
        if snapshot is None:
            if pending is not None or state is not None:
                raise RuntimeError("Local household files are incomplete; data was retained.")
            return
        Doc.to_stores(snapshot)
        if not isinstance(state, dict) or set(state) != {"household_id", "revision", "unregistered"}:
            raise RuntimeError("Invalid household synchronization state.")
        if state["household_id"] != snapshot["_id"] or not isinstance(state["revision"], str) or not state["revision"] or type(state["unregistered"]) is not bool:
            raise RuntimeError("Local household identity/revision does not match.")
        if pending is not None:
            Doc.to_stores(pending)
            if pending["_id"] != snapshot["_id"] or pending["version"] != snapshot["version"]:
                raise RuntimeError("Pending draft does not match its base household/version.")

    # Replay a committed journal before exposing any partially replaced files.
    def _recover(self):
        bundle = self.read_json(self.journal)
        if bundle is not None:
            self.validate_bundle(bundle)
            self._apply(bundle)
            self.journal.unlink()

    # Replace the three files and remove obsolete drafts without deleting cloud data.
    def _apply(self, bundle):
        for key, path in self.paths.items():
            if bundle[key] is None:
                path.unlink(missing_ok=True)
            else:
                self.atomic_write(path, bundle[key])

    # Read a consistent snapshot of local storage after recovery.
    def read(self):
        with self.locked():
            bundle = {key: self.read_json(path) for key, path in self.paths.items()}
            self.validate_bundle(bundle)
            return bundle

    # Missing cache files must not trap startup; preserve survivors before resetting locally.
    def prepare_startup(self):
        # Acquire the raw lock first so a damaged journal is caught and backed up too.
        with self.lock:
            try:
                self._recover()
                self.read()
                return None
            except (RuntimeError, ValueError, KeyError, TypeError):
                backup = self.folder / "recovery" / uuid4().hex
                backup.mkdir(parents=True)
                for path in [*self.paths.values(), self.settings, self.journal]:
                    if path.exists():
                        target = backup / path.relative_to(self.folder)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, target)
                # Backups finish before reset; the journal makes a partial reset recoverable.
                empty = dict.fromkeys(self.paths)
                # Avoid replaying the damaged journal after every survivor has been backed up.
                self.atomic_write(self.settings, {})
                self.atomic_write(self.journal, empty)
                self._apply(empty)
                self.journal.unlink()
                return backup

    # Offline access never falls back to another household's cached data.
    def load(self, household_id):
        bundle = self.read()
        if bundle["snapshot"] is None or bundle["snapshot"]["_id"] != Doc.normalize_id(household_id):
            raise HouseholdNotFound("Only the current cached household is available offline.")
        return deepcopy(bundle["pending"] or bundle["snapshot"])

    # Reject stale local writers before beginning a recoverable transaction.
    def write(self, snapshot, pending, unregistered, expected_revision):
        with self.locked():
            current = self.read()
            actual = current["state"]["revision"] if current["state"] else None
            if actual != expected_revision:
                raise LocalConflict("Another instance saved or switched households. Your in-memory draft was not written.")
            bundle = {"snapshot": deepcopy(snapshot), "pending": deepcopy(pending),
                      "state": {"household_id": snapshot["_id"], "revision": uuid4().hex,
                                "unregistered": unregistered}}
            self.validate_bundle(bundle)
            self.atomic_write(self.journal, bundle)
            self._apply(bundle)
            self.journal.unlink()
            return bundle

    # Invalid preferences reset the menu without deleting household data.
    def read_settings(self):
        with self.locked():
            try:
                settings = self.read_json(self.settings)
                if not isinstance(settings, dict):
                    return None
                settings["last_household_id"] = Doc.normalize_id(settings["last_household_id"])
                if not isinstance(settings["last_household_name"], str):
                    return None
                return settings
            except (KeyError, ValueError, RuntimeError):
                return None

    # Remembering and forgetting do not alter household documents or pending drafts.
    def remember(self, document=None):
        with self.locked():
            self.atomic_write(self.settings, {} if document is None else {
                "last_household_id": document["_id"], "last_household_name": document["name"]})
