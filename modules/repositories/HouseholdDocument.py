# Share one validated document mapping between MongoDB and local JSON.
from copy import deepcopy
from datetime import datetime, timezone
import re
import secrets
from bson import BSON
from modules.core.Household import Household
from modules.core.Person import Person
from modules.core.Fridge import Fridge
from modules.core.FridgeItem import FridgeItem
from modules.core.ConsumptionHistory import ConsumptionHistory
from modules.core.ConsumptionRecord import ConsumptionRecord

class HouseholdDocument:
    EDITABLE = ("name", "household_members", "fridge", "consumption_history")
    ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    WARNING_BYTES = 8 * 1024 * 1024
    MAX_BYTES = 16 * 1024 * 1024

    # Normalize human input before lookup; malformed IDs never reach MongoDB.
    @classmethod
    def normalize_id(cls, value):
        value = value.strip().upper() if isinstance(value, str) else ""
        if not re.fullmatch(r"HS-(?:[" + cls.ALPHABET + r"]{4}-){2}[" + cls.ALPHABET + r"]{4}", value):
            raise ValueError("Use a household ID such as HS-7K9M-2X4P-8R6T.")
        return value

    # Generate a random shared access code; MongoDB confirms uniqueness on insert.
    @classmethod
    def generate_id(cls):
        return "HS-" + "-".join("".join(secrets.choice(cls.ALPHABET) for _ in range(4)) for _ in range(3))

    # Use millisecond UTC timestamps so BSON and JSON round trips agree.
    @staticmethod
    def timestamp(value=None):
        value = datetime.now(timezone.utc) if value is None else value
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime):
            raise ValueError("Invalid household timestamp.")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Create an empty household before collecting dietary profiles and stock.
    @classmethod
    def new(cls, name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ValueError("Household name must contain 1 to 100 characters.")
        now = cls.timestamp()
        return {"_id": cls.generate_id(), "name": name.strip(), "version": 1,
                "created_at": now, "updated_at": now,
                "household_members": [], "fridge": [], "consumption_history": []}

    # Compare user-editable data only, ignoring timestamps and version metadata.
    @classmethod
    def editable(cls, document):
        return deepcopy({key: document[key] for key in cls.EDITABLE})

    # Normalize only metadata dates; food dates remain calendar-date strings.
    @classmethod
    def from_cloud(cls, document):
        result = deepcopy(document)
        for key in ("created_at", "updated_at"):
            if not isinstance(result.get(key), (str, datetime)):
                raise ValueError("Household timestamps must be UTC dates.")
            result[key] = cls.timestamp(result[key])
        cls.to_stores(result)
        return result

    # Store real BSON dates in MongoDB while keeping ordinary JSON locally.
    @classmethod
    def to_cloud(cls, document):
        cls.to_stores(document)
        result = deepcopy(document)
        for key in ("created_at", "updated_at"):
            result[key] = datetime.fromisoformat(cls.timestamp(result[key]).replace("Z", "+00:00"))
        return result

    # Reject oversized cloud documents and expose an early warning threshold.
    @classmethod
    def size(cls, document):
        size = len(BSON.encode(cls.to_cloud(document)))
        if size >= cls.MAX_BYTES:
            raise ValueError("Household reaches MongoDB's 16 MiB limit. Export history before restructuring storage; no records were removed.")
        return size

    # Reject incomplete or invalid documents rather than silently dropping records.
    @classmethod
    def to_stores(cls, document):
        required = {"_id", "version", "created_at", "updated_at", *cls.EDITABLE}
        if not isinstance(document, dict) or set(document) != required:
            raise ValueError("Household document fields do not match the supported schema.")
        if cls.normalize_id(document["_id"]) != document["_id"]:
            raise ValueError("Stored household ID must be normalized.")
        if type(document["version"]) is not int or document["version"] < 1:
            raise ValueError("Household version must be a positive integer.")
        if not isinstance(document["name"], str) or not document["name"].strip() or len(document["name"]) > 100:
            raise ValueError("Invalid household name.")
        for key in ("created_at", "updated_at"):
            if not isinstance(document[key], (str, datetime)):
                raise ValueError("Household timestamps must be dates.")
            cls.timestamp(document[key])
        household = Household(document["_id"], document["name"])
        fridge, history, ids = Fridge(), ConsumptionHistory(), set()
        for field in cls.EDITABLE[1:]:
            if not isinstance(document[field], list):
                raise ValueError(f"{field} must be an array.")
            for index, row in enumerate(document[field]):
                if not isinstance(row, dict) or not isinstance(row.get("_id"), str) or not row["_id"].strip() or row["_id"] in ids:
                    raise ValueError("Embedded IDs must be nonempty and unique within a household.")
                ids.add(row["_id"])
                if field == "household_members":
                    if set(row) != {"_id", "name", "age", "gender", "dietary_restriction"}:
                        raise ValueError("Invalid member fields.")
                    if not isinstance(row["gender"], str):
                        raise ValueError("Member gender must be a string.")
                    record = Person(index + 1, row["name"], row["age"], row["gender"].capitalize(), row["dietary_restriction"])
                    household.add_member(record)
                elif field == "fridge":
                    if set(row) != {"_id", "Item_Name", "Quantity", "Unit", "Purchase_Date", "Expiry_Date", "Remarks"}:
                        raise ValueError("Invalid fridge fields.")
                    record = FridgeItem.from_dict(row)
                    if fridge.add_item(record):
                        raise ValueError("Duplicate fridge batches must be resolved before storage.")
                else:
                    if set(row) != {"_id", "Item_Name", "Quantity", "Unit", "Date_Range", "Record_Date", "Remarks"}:
                        raise ValueError("Invalid history fields.")
                    record = ConsumptionRecord.from_dict(row)
                    history.add_record(record)
                record.restore_storage_id(row["_id"])
        # Check units across both food arrays before exposing a household to calculations.
        units = {}
        for record in [*fridge.get_items(), *history.get_records()]:
            key = record.name.strip().casefold()
            if key in units and units[key] != record.unit:
                raise ValueError(f"{record.name} has incompatible units across stock and history.")
            units[key] = record.unit
        if len(household.get_members()) > Household.MAX_PAX:
            raise ValueError("Too many household members.")
        return {"household": household, "fridge": fridge, "consumption_history": history}

    # Preserve object IDs across edits while retaining the original cloud version.
    @classmethod
    def from_stores(cls, original, stores):
        result = deepcopy(original)
        household = stores["household"]
        if household.household_id != original["_id"]:
            raise ValueError("Active household identity changed unexpectedly.")
        result["name"] = household.name
        result["household_members"] = [
            {"_id": p.storage_id, "name": p.get_name(), "age": p.get_age(),
             "gender": p.get_gender().lower(), "dietary_restriction": p.get_dietary_restriction()}
            for p in household.get_members()]
        result["fridge"] = [{"_id": item.storage_id, **item.to_dict()} for item in stores["fridge"].get_items()]
        result["consumption_history"] = [{"_id": item.storage_id, **item.to_dict()} for item in stores["consumption_history"].get_records()]
        cls.to_stores(result)
        return result
