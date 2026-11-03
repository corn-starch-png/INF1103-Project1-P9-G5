from decimal import Decimal

from core.ListFunctions import ListFunctions
from core.FridgeItem import FridgeItem
from core.ConsumptionRecord import ConsumptionRecord
from core.CanBeStored import CanBeStored


class Fridge(ListFunctions, CanBeStored):
    """Everything currently stored in the fridge (aggregation of FridgeItem)."""

    def __init__(self):
        self.__items = []

    def validate(self) -> bool:
        """
        should run after every addition or removal of items to ensure the fridge is valid.
        checks for duplicate items with different units, and duplicate items where only the quantity is different 
        (same name, unit, purchase date, expiry date, remarks)
        """
        item_unit_pairs = list()
        for item in self.__items:
            if not item.validate():
                return False
            #check for duplicate items with different units
            if (item.name.strip().casefold()) not in item_unit_pairs:
                item_unit_pairs.append((item.name.strip().casefold(), item.unit.strip().casefold()))
            else:
                if (item.name.strip().casefold(), item.unit.strip().casefold()) in item_unit_pairs:
                    return False
            #check for duplicate items where only the quantity is different 
            #(same name, unit, purchase date, expiry date, remarks)
            for other_item in self.__items:
                if item is not other_item:
                    if (item.name.strip().casefold() == other_item.name.strip().casefold() and
                        item.unit.strip().casefold() == other_item.unit.strip().casefold() and
                        item.purchase_date == other_item.purchase_date and
                        item.expiry_date == other_item.expiry_date and
                        item.remarks.strip().casefold() == other_item.remarks.strip().casefold()):
                        #merge the two items by adding their quantities
                        item.quantity += other_item.quantity
                        self.__items.remove(other_item)
        return True

    def add_item(self, item: FridgeItem) -> None:
        if not isinstance(item, FridgeItem):
            raise TypeError("Only FridgeItem objects can be added to the Fridge.")
        if not item.validate():
            raise ValueError("Cannot add an invalid item to the fridge.")
        self.__items.append(item)

    def remove_item(self, item: FridgeItem) -> None:
        if item not in self.__items:
            raise ValueError("Item is not in the fridge.")
        self.__items.remove(item)

    def get_items(self) -> list:
        return list(self.__items)

    def consume(self, item_name: str, amount: float, units: str, date_range: int, consumption_remarks: str) -> ConsumptionRecord:
        """
        Consume a certain amount of an item in the fridge FIFO, reducing its quantity.
        If the quantity reaches zero, remove the item from the fridge.
        return a ConsumptionRecord of the consumption.
        """
        total_quantity = self.get_total_quantity(item_name, include_expired=False)
        #validation start (not validating units, assumed to be correct)
        if item_name.strip() == "" or item_name not in [item.name for item in self.__items]:
            raise ValueError("Item does not exist in the fridge.")
        if type(amount) not in (int, float):
            raise ValueError(f"Invalid consumption quantity for {item_name}.")
        if amount > total_quantity:
            raise ValueError(f"Cannot consume {amount}{units} of {item_name};\nonly {total_quantity} available.")
        #validation end
        
        for item in self.__items:
            if item.name.strip().casefold() == item_name.strip().casefold():
                if item.quantity < amount:
                    amount -= item.quantity
                    self.__items.remove(item)
                else:
                    item.quantity -= amount

                if item.quantity == 0:
                    self.__items.remove(item)
        return ConsumptionRecord(item_name, amount, units, date_range, consumption_remarks)

    def get_total_quantity(self, item_name: str, include_expired: bool) -> float:
        """
        Total non-expired quantity in the fridge of the same item as `item`
        """
        total = Decimal("0")
        for stored in self.__items:
            if stored.name.strip().casefold() != item_name.strip().casefold():
                continue
            if stored.is_expired() and not include_expired:
                continue
            total += Decimal(str(stored.quantity))
        return float(total)
    
    def to_dicts(self) -> list:
        return [item.to_dict() for item in self.__items]
 
    def load_dicts(self, rows: list) -> list:
        errors = []
        for row in rows:
            try:
                self.add_item(FridgeItem.from_dict(row))
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"Skipped invalid fridge row {row!r}: {error!r}")
        return errors