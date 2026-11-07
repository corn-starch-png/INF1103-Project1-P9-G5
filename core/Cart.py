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
        
        #check if item with same name and units exists, then merge the quantites
        merging = False
        for existing in self.__items:
            if existing.name.lower() == item.name.lower() and existing.unit == item.unit:
                combined_quantity = Decimal(str(existing.quantity)) + Decimal(str(item.quantity))
                if combined_quantity > CartItem.MAX_QUANTITY:
                    raise ValueError(f"Total quantity cannot exceed {CartItem.MAX_QUANTITY:,}.")
                existing.set_quantity(combined_quantity)
                merging = True
                    
        self.__items.append(item)
        return merging

    def remove_item(self, item: CartItem) -> None:
        if item not in self.__items:
            raise ValueError("Item is not in the cart.")
        self.__items.remove(item)

    def get_items(self) -> list:
        return list(self.__items)

    def search_item(self, item_name: str) -> CartItem:
        for item in self.__items:
            if item.name == item_name:
                return item
        raise ValueError("Error, item does not exist in cart")

    def set_remarks(self, remarks: str) -> None:
        self.__remarks = remarks

    def get_remarks(self) -> str:
        return self.__remarks

    def checkout(self, fridge: Fridge) -> None:
        """
        Move all items from the cart to the fridge, converting them to FridgeItem.
        The cart is cleared after checkout.
        """
        for item in self.__items:
            fridge_item = item.to_fridge_item(self.__remarks)
            fridge.add_item(fridge_item)
        self.__items.clear()
