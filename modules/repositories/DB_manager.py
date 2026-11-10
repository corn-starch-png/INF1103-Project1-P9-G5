from datetime import datetime
from pathlib import Path
import shutil
from .AppPaths import AppPaths
from .JsonRepository import JsonRepository

# Coordinate repository selection, local backups and recovery from cloud failures.
class DB_manager:
    STORE_NAMES = ("fridge", "household", "consumption_history")

    def __init__(self, ui, database_dir=None, use_mongo=True, mongo_factory=None, json_factory=None):
        # Allow tests to supply temporary storage and mocked repository factories.
        self.ui = ui
        self.database_dir = Path(database_dir) if database_dir is not None else AppPaths.DATABASE_DIR
        self.offline_marker = self.database_dir / ".offline_changes"
        self.use_mongo = use_mongo
        self.mongo_factory = mongo_factory if mongo_factory is not None else self._create_mongo_repository
        self.json_factory = json_factory if json_factory is not None else JsonRepository
        self.repository = None
        self.stores = None
        self.is_local = True

    # Delay MongoDB construction until application startup actually requests it.
    @staticmethod
    def _create_mongo_repository():
        from .MongoDBRepository import MongoDBRepository
        return MongoDBRepository()

    # Construct a local repository using the configured storage directory.
    def _new_local_repository(self):
        return self.json_factory(folder=self.database_dir)

    # Select cloud storage when available, otherwise load local JSON.
    def start(self):
        if self.use_mongo:
            try:
                repository = self.mongo_factory()
                errors, stores = repository.load()
                if errors:
                    raise RuntimeError("Cloud data could not be loaded completely: " + "; ".join(errors))
            except Exception as error:
                self.ui.send_message(f"MongoDB unavailable ({error}). Using local JSON instead.")
            else:
                self.repository = repository
                self.stores = stores
                self.is_local = False
                self.ui.send_message("Connected to the shared MongoDB database.")

        # Use local storage if cloud initialization did not succeed.
        if self.repository is None:
            self.repository = self._new_local_repository()
            errors, self.stores = self.repository.load()
            if errors:
                raise RuntimeError("Could not load local data completely: " + "; ".join(errors))
            self.is_local = True

        # Resolve pending local changes before refreshing the cloud mirror.
        if not self.is_local:
            if self.offline_marker.exists():
                self.resolve_offline_changes(self.ui.ask_upload_offline_changes())
            self.mirror_to_json(backup=True)

        return self.stores

    # Preserve existing local files before overwriting the local mirror.
    def _backup_local_files(self):
        existing = [self.database_dir / f"{name}.json" for name in self.STORE_NAMES]
        existing = [path for path in existing if path.exists()]
        if not existing:
            return

        destination = self.database_dir / ("backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        destination.mkdir(parents=True, exist_ok=True)
        for source in existing:
            shutil.copy2(source, destination)

    # Write all current domain objects into the configured local repository.
    def _write_local_copy(self):
        local_repository = self._new_local_repository()
        _, local_stores = local_repository.load()

        # Replace all stores because the current in-memory objects are authoritative here.
        local_stores.update(self.stores)
        local_repository.save()

    # Refresh the local mirror without claiming failure of an already successful cloud save.
    def mirror_to_json(self, backup=False):
        if self.is_local:
            return

        try:
            if backup:
                self._backup_local_files()
            self._write_local_copy()
        except Exception as error:
            self.ui.send_message(f"Warning: could not update the local JSON backup: {error}")

    # Upload pending local changes or explicitly retain the cloud version.
    def resolve_offline_changes(self, upload):
        if self.is_local or not self.offline_marker.exists():
            return

        # Back up the local files before resolving the pending changes.
        self._backup_local_files()

        if not upload:
            self.offline_marker.unlink()
            self.ui.send_message("Offline changes discarded. Using the shared database data.")
            return

        # Do not replace cloud data with an incomplete local dataset.
        required_files = [self.database_dir / f"{name}.json" for name in self.STORE_NAMES]
        if not all(path.is_file() for path in required_files):
            raise RuntimeError("Offline upload stopped because a local database file is missing.")

        local_repository = self._new_local_repository()
        errors, local_stores = local_repository.load()
        if errors:
            raise RuntimeError("Offline upload stopped because local data is invalid: " + "; ".join(errors))

        # Both repository implementations return their actual store dictionary.
        previous_stores = self.stores.copy()
        self.stores.update(local_stores)

        try:
            self.repository.save()
        except Exception as error:
            # Restore the previous in-memory mapping; keep local files and marker for retry.
            self.stores.clear()
            self.stores.update(previous_stores)
            raise RuntimeError(f"Offline upload failed. Local changes are preserved: {error}") from error

        # Remove the marker only after the cloud save succeeds.
        self.offline_marker.unlink()
        self.ui.send_message("Offline changes uploaded to the shared database.")

    # Save current data and recover locally if the cloud save fails.
    def save(self):
        if self.repository is None or self.stores is None:
            raise RuntimeError("Database manager must be started before saving.")

        try:
            self.repository.save()
        except Exception as error:
            if self.is_local:
                raise RuntimeError(f"Could not save local data: {error}") from error

            self.ui.send_message(f"Cloud save failed: {error}. Saving changes locally.")
            try:
                self._write_local_copy()
                self.database_dir.mkdir(parents=True, exist_ok=True)
                self.offline_marker.touch()
            except Exception as local_error:
                raise RuntimeError(f"Could not save the local fallback: {local_error}") from local_error

            self.ui.send_message("Changes saved locally. Upload them when the shared database is available.")
            return

        if self.is_local:
            # Record that successfully saved local changes have not been uploaded.
            self.database_dir.mkdir(parents=True, exist_ok=True)
            self.offline_marker.touch()
        else:
            self.mirror_to_json()