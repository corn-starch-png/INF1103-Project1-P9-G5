from datetime import date
from .ItemRecord import ItemRecord
from .ItemFunctions import ItemFunctions
from .AIRecData import AIRecData
from .FridgeItem import FridgeItem


class CartItem(ItemRecord, ItemFunctions):
    """A grocery item the user entered before it is sent to the AI."""

    def __init__(self, name: str, quantity: float, unit: str):
        super().__init__(name, quantity, unit)
        self.__ai_data = ""

    @property
    def ai_data(self) -> AIRecData:
        return self.__ai_data

    def set_confidence_score(self, score: float) -> None:
        if self.__ai_data == "":
            raise NotImplementedError("Cannot set Confidence score without AI data")
        self.__ai_data.set_confidence_score(score)

    def set_ai_data(self, recommended_qty: float, consumption_rate: float, est_expiry_date: str) -> None:
        self.__ai_data = AIRecData(recommended_qty, consumption_rate, est_expiry_date)
        
    def validate(self) -> bool:
        return self._validate_item_fields()

    def to_dict(self) -> dict:
        return {
            "Item_Name": self._name,
            "Quantity": self._quantity,
            "Unit": self._unit,
        }

    @property
    def get_ai_data(self) -> AIRecData:
      """Returns the AI recommendation data associated with this item."""
      return self.__ai_data  
    
    @classmethod
    def from_dict(cls, data: dict) -> "CartItem":
        return cls(data["Item_Name"], data["Quantity"], data["Unit"])

    def set_quantity(self, amount: float) -> None:
        self._set_quantity(amount)

    def to_fridge_item(self, remarks: str = "") -> "FridgeItem":
        return FridgeItem(
            name=self._name,
            quantity=self._quantity,
            unit=self._unit,
            purchase_date=date.today().isoformat(),
            expiry_date=self.__ai_data.est_expiry_date,
            remarks=remarks,
        )

    def is_enhanced(self) -> bool:
        if self.__ai_data == "":
            return False
        return True
