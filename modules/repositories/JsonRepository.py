import json
import os
from .RepositoryFunctions import RepositoryFunctions
from .AppPaths import AppPaths
from modules.core.Household import Household
from modules.core.Fridge import Fridge
from modules.core.ConsumptionHistory import ConsumptionHistory

class JsonRepository(RepositoryFunctions):
    def __init__(self, folder=AppPaths.DATABASE_DIR):
        self.__folder = folder
        self.__stores = {
            "fridge": Fridge(),
            "household": Household(),
            "consumption_history": ConsumptionHistory(),
        }

    def load(self) -> list:
        """Returns a list of problems; an empty list means everything loaded."""
        os.makedirs(self.__folder, exist_ok=True)
        self.__stores = {"fridge": Fridge(), "household": Household(), "consumption_history": ConsumptionHistory(),}
        errors = []
        for filename, store in self.__stores.items():
            path = os.path.join(self.__folder, filename + ".json")
            if not os.path.exists(path):
                continue                                  # first run
            try:
                with open(path, encoding="utf-8") as f:
                    rows = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
                errors.append(f"Could not read {filename}: {e}")
                continue
            if not isinstance(rows, list):
                errors.append(f"{filename} must contain a list")
                continue
            errors.extend(store.load_dicts(rows))
        return errors, self.__stores

    def save(self) -> None:
        os.makedirs(self.__folder, exist_ok=True)
        for filename, store in self.__stores.items():
            self.__write_atomic(os.path.join(self.__folder, filename + ".json"), store.to_dicts())

    @staticmethod
    def __write_atomic(path, data):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)          # a crash mid-write can't corrupt the real file