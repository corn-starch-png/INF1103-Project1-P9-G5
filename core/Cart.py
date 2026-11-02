from ListFunctions import ListFunctions
from CartItem import CartItem


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
