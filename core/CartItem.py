from datetime import date

from core.ItemRecord import ItemRecord
from core.ItemFunctions import ItemFunctions
from core.AIRecData import AIRecData
from core.FridgeItem import FridgeItem


class CartItem(ItemRecord, ItemFunctions):
    """A grocery item the user entered before it is sent to the AI."""

    def __init__(self, name: str, quantity: float, unit: str):
        super().__init__(name, quantity, unit)
        self.__ai_data = ""

    def set_ai_data(self, ai_data: AIRecData) -> None:
        self.__ai_data = ai_data

    def validate(self) -> bool:
        return self._validate_item_fields()

    def to_dict(self) -> dict:
        return {
            "Item_Name": self._name,
            "Quantity": self._quantity,
            "Unit": self._unit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CartItem":
        return cls(data["Item_Name"], data["Quantity"], data["Unit"])

    def edit_quantity(self, amount: float) -> None:
        self._set_quantity(amount)

    def to_fridge_item(self, remarks: str = "") -> "FridgeItem":
        return FridgeItem(
            name=self._name,
            quantity=self._quantity,
            unit=self._unit,
            purchase_date=date.today().isoformat(),
            expiry_date=self.__ai_data.est_expiry_date(),
            remarks=remarks,
        )
