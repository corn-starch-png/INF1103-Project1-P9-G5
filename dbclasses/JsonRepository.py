import json
import os

from RepositoryFunctions import RepositoryFunctions
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory


class JsonRepository(RepositoryFunctions):
    def __init__(self, fridge: Fridge, household: Household, history: ConsumptionHistory, folder="database"):
        self.__folder = folder
        # aggregation: the three objects are created outside and injected
        self.__stores = {
            "fridge.json": fridge,
            "household.json": household,
            "consumption_history.json": history,
        }

    def load(self) -> list:
        """Returns a list of problems; an empty list means everything loaded."""
        os.makedirs(self.__folder, exist_ok=True)
        errors = []
        for filename, store in self.__stores.items():
            path = os.path.join(self.__folder, filename)
            if not os.path.exists(path):
                continue                                  # first run
            try:
                with open(path, encoding="utf-8") as f:
                    rows = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"Could not read {filename}: {e}")
                continue
            if not isinstance(rows, list):
                errors.append(f"{filename} must contain a list")
                continue
            errors.extend(store.load_dicts(rows))
        return errors

    def save(self) -> None:
        os.makedirs(self.__folder, exist_ok=True)
        for filename, store in self.__stores.items():
            self.__write_atomic(os.path.join(self.__folder, filename), store.to_dicts())

    @staticmethod
    def __write_atomic(path, data):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)          # a crash mid-write can't corrupt the real file