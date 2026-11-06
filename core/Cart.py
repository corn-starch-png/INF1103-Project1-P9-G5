from decimal import Decimal

from core.ListFunctions import ListFunctions
from core.CartItem import CartItem
from core.Fridge import Fridge


class Cart(ListFunctions):
    """The user's grocery cart before it is sent to the AI (aggregation of CartItem)."""

    def __init__(self, remarks: str = ""):
        self.__items = []
        self.__remarks = remarks

    def add_item(self, item: CartItem) -> None:
        if not isinstance(item, CartItem):
            raise TypeError("Only CartItem objects can be added to a Cart.")
        if not item.validate():
            raise ValueError("Cannot add an invalid item to the cart.")
        self.__items.append(item)

    def add_or_merge(self, item: CartItem) -> tuple:
        """
        Add the item, or merge it with an item that has the same name and unit.
        Raises ValueError if the total is over MAX_QUANTITY.
        """
        # If the same item with the same unit was already entered, add to it
        for existing in self.__items:
            if existing.name.lower() == item.name.lower() and existing.unit == item.unit:
                combined_quantity = Decimal(str(existing.quantity)) + Decimal(str(item.quantity))
                if combined_quantity > CartItem.MAX_QUANTITY:
                    raise ValueError(f"Total quantity cannot exceed {CartItem.MAX_QUANTITY:,}.")
                existing.edit_quantity(combined_quantity)
                return True, existing
        self.add_item(item)
        return False, item

    def remove_item(self, item: CartItem) -> None:
        if item not in self.__items:
            raise ValueError("Item is not in the cart.")
        self.__items.remove(item)

    def get_items(self) -> list:
        return list(self.__items)

    def set_remarks(self, remarks: str) -> None:
        self.__remarks = remarks

    def checkout(self, fridge: Fridge) -> None:
        """
        Move all items from the cart to the fridge, converting them to FridgeItem.
        The cart is cleared after checkout.
        """
        for item in self.__items:
            fridge_item = item.to_fridge_item()
            fridge.add_item(fridge_item)
        self.__items.clear()
