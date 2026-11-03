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
