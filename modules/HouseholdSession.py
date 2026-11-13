# Coordinate household navigation and recovery choices separately from persistence operations.
from .repositories.StorageErrors import CloudUnavailable, HouseholdNotFound
from enum import Enum

# Separate purchase acceptance from successful recovery for navigation.
class SaveOutcome(Enum):
    SAVED = "saved"
    OFFLINE = "offline"
    CLOUD_ADOPTED = "cloud_adopted"
    KEPT = "kept"

class HouseholdSession:
    # Collaborate with the data manager through its public operations and the UI through prompts.
    def __init__(self, data_manager, ui):
        self._data = data_manager
        self._ui = ui

    # Coordinate read-only conflict presentation without making a persistence decision.
    def review(self):
        try:
            comparison = self._data.comparison()
            self._ui.show_conflict_review(comparison["base"], comparison["draft"], comparison["cloud"])
        except (CloudUnavailable, HouseholdNotFound) as error:
            self._ui.send_message(str(error))
            self._ui.send_message("Cannot compare without the latest cloud household. Your draft is retained; try Review again when it is available.")

    # Confirm replacement directly; explicit review owns the table and persistence retains race checks.
    def resolve_food_conflict(self, source):
        proposal = self._data.prepare_food_resolution(source)
        if proposal.get("replaces_device_draft"):
            self._ui.send_message("This device has another pending draft. Confirming replacement also discards that cached draft.")
        if not self._ui.confirm_food_replacement(source, proposal["cloud"]["version"]):
            self._data.cancel_food_resolution(proposal["token"])
            return False
        self._data.apply_food_resolution(proposal["token"])
        # Report successful replacement only after persistence completes.
        if source == "cloud":
            self._ui.send_message("Local data has been successfully replaced with the latest cloud data.")
        else:
            self._ui.send_message("Cloud data has been successfully replaced with your local data.")
        return True

    # Review and cancelled choices stay in recovery without repeatedly attempting a stale save.
    def save_interactive(self):
        # Preserve callers' checkout bool while navigation consumes the explicit outcome.
        return self.save_outcome() in (SaveOutcome.SAVED, SaveOutcome.OFFLINE)

    # Confirm setup only after a successful save, never after offline or discarded edits.
    def save_setup(self):
        outcome = self.save_outcome()
        if outcome == SaveOutcome.SAVED:
            self._ui.send_message("Your setup has been saved to the cloud.")
        return outcome

    # Report cloud adoption independently from accepting a locally planned purchase.
    def save_outcome(self):
        while True:
            try:
                result = self._data.save()
                return SaveOutcome.OFFLINE if result == "offline" else SaveOutcome.SAVED
            except (RuntimeError, ValueError, OSError) as error:
                self._ui.send_message(str(error))
            while True:
                choice = self._ui.ask_save_recovery()
                try:
                    if choice == "review":
                        self.review()
                    elif choice in ("local", "cloud"):
                        if self.resolve_food_conflict(choice):
                            # Cloud selection returns to the app so discarded purchases are not treated as accepted.
                            return SaveOutcome.SAVED if choice == "local" else SaveOutcome.CLOUD_ADOPTED
                    elif choice == "retry":
                        break
                    elif choice == "keep":
                        return SaveOutcome.KEPT
                except (RuntimeError, ValueError, OSError) as error:
                    self._ui.send_message(str(error))

    # Keep failed synchronization in the switch flow until the user explicitly resumes.
    def select_household(self, switching=False):
        discard = False
        bundle = self._data.read_cache()
        if switching or bundle["pending"] is not None:
            dirty = self._data.has_changes() or bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
            while dirty:
                # Identify the owner of edits before asking permission to sync during selection.
                owner = self._data.base or bundle["snapshot"]
                self._ui.send_message(f"Pending edits belong to {owner['name']} ({owner['_id']}). Sync saves only this household, not a different selected or remembered household.")
                choice = self._ui.ask_switch_resolution()
                if choice == "cancel":
                    return self._data.stores if self._data.stores is not None else self._data.resume_cached()
                if choice == "sync":
                    if self._data.base is None:
                        self._data.resume_cached()
                    if self.save_outcome() not in (SaveOutcome.SAVED, SaveOutcome.CLOUD_ADOPTED) or self._data.read_cache()["pending"] is not None:
                        self._ui.send_message("Switch has not completed: current edits are not synced. Retry sync, explicitly discard, or choose Resume current household.")
                        continue
                    break
                elif choice == "discard":
                    discard = self._ui.confirm_discard()
                    if discard:
                        break
        while True:
            action = self._ui.ask_household_access(switching=switching)
            if action == "exit":
                return None
            try:
                if action == "create":
                    stores = self._data.create_household(self._ui.ask_household_name(), discard=discard)
                else:
                    # Re-entering the active code is not a household switch.
                    household_id = self._data.authorize_household(self._ui.ask_household_id())
                    current_id = self._data.base["_id"] if self._data.base else (bundle["snapshot"]["_id"] if bundle["snapshot"] else None)
                    if switching and household_id == current_id:
                        self._ui.send_message("That is the current Household Space ID. Enter a different ID to switch.")
                        continue
                    stores = self._data.open_household(household_id, discard=discard)
                # Automatically remember only a successfully opened or created space.
                self._data.remember(self._data.base)
                if self._data.is_local:
                    self._ui.send_message("Using the current Household Space locally. Use Save/sync when cloud access is available.")
                if switching:
                    self._ui.send_message(f"Switched to {self._data.base['name']} ({self._data.base['_id']}).")
                return stores
            except (RuntimeError, ValueError, OSError) as error:
                self._ui.send_message(str(error))

    # Repair incomplete local storage before offering remembered access or selection.
    def start(self):
        backup = self._data.prepare_startup()
        if backup is not None:
            self._ui.send_message(f"Local household cache was incomplete or invalid. Starting with an empty local cache. Surviving files were backed up to: {backup}. MongoDB was not changed.")
        settings = self._data.read_preferences()
        # Preferences never determine which household owns a cached draft.
        bundle = self._data.read_cache()
        if settings and bundle["pending"] and settings["last_household_id"] != bundle["pending"]["_id"]:
            self._ui.send_message(f"Remembered Household Space: {settings['last_household_name']} ({settings['last_household_id']}). Local pending edits belong to {bundle['pending']['name']} ({bundle['pending']['_id']}); they will not be uploaded to the remembered household.")
        while settings:
            choice = self._ui.ask_remembered_household(settings["last_household_name"])
            if choice == "exit":
                return None
            if choice == "forget":
                if self.forget_household():
                    break
                continue
            if choice == "switch":
                # Back returns here; only an explicit Continue opens the remembered space.
                selected = self.select_household(switching=True)
                if selected is not None:
                    return selected
                continue
            try:
                # Explicit Continue can resume a draft activated during a cancelled sync attempt.
                if self._data.base and self._data.base["_id"] == settings["last_household_id"] and self._data.has_changes():
                    return self._data.stores
                return self._data.open_household(settings["last_household_id"])
            except (RuntimeError, ValueError, OSError) as error:
                self._ui.send_message(str(error))
                settings = None
        return self.select_household()

    # Sync pending edits before signing out; leave the cache and cloud household intact.
    def forget_household(self):
        bundle = self._data.read_cache()
        settings = self._data.read_preferences()
        if self._data.base is None and settings and bundle["snapshot"] and settings["last_household_id"] != bundle["snapshot"]["_id"]:
            self._data.remember()
            self._ui.send_message("Remembered Household Space cleared. Another household's local draft was retained without syncing; resolve it separately before switching.")
            return True
        if self._data.base is None and bundle["snapshot"] is not None:
            self._data.resume_cached()
        dirty = self._data.has_changes() or bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
        if dirty:
            if self.save_outcome() not in (SaveOutcome.SAVED, SaveOutcome.CLOUD_ADOPTED) or self._data.read_cache()["pending"] is not None:
                self._ui.send_message("Cannot forget yet: pending edits must reach MongoDB first. Your household and draft are retained; retry when cloud access is available.")
                return False
        self._data.remember()
        self._data.clear_selection()
        self._ui.send_message("Household Space forgotten. Local files and MongoDB data are retained. You can now enter another Household Space ID.")
        return True

