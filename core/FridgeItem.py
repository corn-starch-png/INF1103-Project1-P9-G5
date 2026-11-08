from datetime import date

from core.ItemRecord import ItemRecord
from core.ItemFunctions import ItemFunctions
from core.ConsumptionRecord import ConsumptionRecord


class FridgeItem(ItemRecord, ItemFunctions):
    """One batch of an item stored in the fridge."""
    
    def __init__(self, name: str, quantity: float, unit: str, purchase_date: str,
                 expiry_date: str, remarks: str = ""):
        super().__init__(name, quantity, unit)
        self.__purchase_date = purchase_date  # "YYYY-MM-DD" or "" if unknown
        self.__expiry_date = expiry_date      # "YYYY-MM-DD"
        self.__remarks = remarks
        
    @property
    def purchase_date(self) -> str:
        return self.__purchase_date

    @property
    def expiry_date(self) -> str:
        return self.__expiry_date

    @property
    def remarks(self) -> str:
        return self.__remarks        

    @staticmethod
    def __is_valid_date(value, allow_blank: bool = False) -> bool:
        if not isinstance(value, str):
            return False
        if allow_blank and value == "":
            return True
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False

    def validate(self) -> bool:
        if not self._validate_item_fields():  # fridge quantity must be greater than 0
            return False
        if not self.__is_valid_date(self.__purchase_date, allow_blank=True):
            return False
        if not self.__is_valid_date(self.__expiry_date):
            return False
        if self.__purchase_date != "":
            if date.fromisoformat(self.__purchase_date) > date.fromisoformat(self.__expiry_date):
                return False
        if not isinstance(self.__remarks, str) or len(self.__remarks) > ItemRecord.MAX_REMARKS_LENGTH:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "Item_Name": self._name,
            "Quantity": self._quantity,
            "Unit": self._unit,
            "Purchase_Date": self.__purchase_date,
            "Expiry_Date": self.__expiry_date,
            "Remarks": self.__remarks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FridgeItem":
        return cls(
            data["Item_Name"],
            data["Quantity"],
            data["Unit"],
            data["Purchase_Date"],
            data["Expiry_Date"],
            data.get("Remarks", ""),
        )
    

    def set_quantity(self, amount: float) -> None:
        self._set_quantity(amount)

    def edit_expiry_date(self, new_expiry_date: str) -> None:
        if not self.__is_valid_date(new_expiry_date):
            raise ValueError("Expiry date must be in YYYY-MM-DD format.")
        if self.__purchase_date != "":
            if date.fromisoformat(self.__purchase_date) > date.fromisoformat(new_expiry_date):
                raise ValueError("Expiry date cannot be before purchase date.")
        self.__expiry_date = new_expiry_date

    def is_expired(self) -> bool:
        """An item is expired once today is after its expiry date (same rule as the original code)."""
        return date.fromisoformat(self.__expiry_date) < date.today()

