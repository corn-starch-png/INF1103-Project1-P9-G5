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
        """should run after every addition or removal of items to ensure the fridge is valid."""
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
        return True

    def add_item(self, item: FridgeItem) -> None:
        if not isinstance(item, FridgeItem):
            raise TypeError("Only FridgeItem objects can be added to the Fridge.")
        if not item.validate():
            raise ValueError("Cannot add an invalid item to the fridge.")
        self.__items.append(item)
        self.remove_duplicates()

    def add_or_merge(self, item: FridgeItem) -> tuple:
        """
        Add the item, or merge it with a batch that has the same name, unit and expiry date.
        Raises ValueError if the total is over MAX_QUANTITY or the combined remarks are over MAX_REMARKS_LENGTH.
        """
        for index in range(len(self.__items)):
            existing = self.__items[index]
            if (
                existing.name.lower() == item.name.lower()
                and existing.unit == item.unit
                and existing.expiry_date == item.expiry_date
            ):
                # Add quantities using Decimal
                combined_quantity = Decimal(str(existing.quantity)) + Decimal(str(item.quantity))
                if combined_quantity > FridgeItem.MAX_QUANTITY:
                    raise ValueError(f"Total quantity cannot exceed {FridgeItem.MAX_QUANTITY:,}.")

                # Merge remarks safely
                new_remarks = existing.remarks
                if item.remarks != "none" and item.remarks != new_remarks:
                    if new_remarks == "none":
                        new_remarks = item.remarks
                    else:
                        new_remarks += ", " + item.remarks
                if len(new_remarks) > FridgeItem.MAX_REMARKS_LENGTH:
                    raise ValueError(f"Combined remarks cannot exceed {FridgeItem.MAX_REMARKS_LENGTH} characters.")

                # Update the existing item after validation
                existing = FridgeItem(existing.name, float(combined_quantity), existing.unit,
                                      existing.purchase_date, existing.expiry_date, new_remarks)
                self.__items[index] = existing
                return True, existing

        self.add_item(item)
        return False, item

    def change_expiry(self, item: FridgeItem, new_expiry_date: str) -> bool:
        """
        Change the expiry date of an item in the fridge. If the new expiry date causes it to match another batch (same name, unit, purchase date, expiry date and remarks), merge them into one batch.
        Returns true if batches were merged. Raises ValueError and reverts the change if the merged quantity would be over MAX_QUANTITY.
        """
        matching_items = []
        total_quantity = Decimal(str(item.quantity))

        for existing in self.__items:
            if existing is item:
                continue

            if (
                existing.name.lower() == item.name.lower()
                and existing.unit == item.unit
                and existing.purchase_date == item.purchase_date
                and existing.expiry_date == new_expiry_date
                and existing.remarks == item.remarks
            ):
                matching_items.append(existing)
                total_quantity += Decimal(str(existing.quantity))

        if total_quantity > FridgeItem.MAX_QUANTITY:
            raise ValueError(f"Total quantity cannot exceed {FridgeItem.MAX_QUANTITY:,}. Expiry date was not changed.")

        item.edit_expiry_date(new_expiry_date)
        item.edit_quantity(total_quantity)

        for existing in matching_items:
            self.remove_item(existing)
        return len(matching_items) > 0

    def get_item_totals(self) -> list:
        """
        Add up each item across all its batches and return a list of dictionaries 
        with keys 'item_name', 'quantity', and 'units'.
        """
        totals = {}
        for item in self.__items:
            key = (item.name.lower(), item.unit)
            if key in totals:
                totals[key]["quantity"] += Decimal(str(item.quantity))
            else:
                totals[key] = {
                    "item_name": item.name,
                    "quantity": Decimal(str(item.quantity)),
                    "units": item.unit
                }
        return list(totals.values())

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
        Return a ConsumptionRecord of the consumption.
        """
        
        # Validation
        if item_name.strip() == "" or item_name.casefold() not in [item.name.strip().casefold() for item in self.__items]:
            raise ValueError("Item does not exist in the fridge.")
        if type(amount) not in (int, float) or amount <= 0:
            raise ValueError(f"Invalid consumption quantity for {item_name}.")

        total_quantity = self.get_total_quantity(item_name, include_expired=False)
        if amount > total_quantity:
            raise ValueError(f"Cannot consume {amount}{units} of {item_name};\nonly {total_quantity} available.")
        
        # Save the requested amount for the record before we mutate it
        requested_amount = amount
        
        i = 0
        while amount > 0 and i < len(self.__items):
            item = self.__items[i]
            if item.name.strip().casefold() == item_name.strip().casefold():
                if item.quantity <= amount:
                    amount -= item.quantity
                    self.__items.pop(i)  # Remove item and let index stay in place for the shifted element
                else:
                    item.quantity -= amount
                    amount = 0
                    i += 1  # Move to the next item since this one still has remaining quantity
            else:
                i += 1
                
        return ConsumptionRecord(item_name, requested_amount, units, date_range, consumption_remarks)

    def remove_duplicates(self):
        """
        should run after every addition or removal of items to ensure the fridge is valid.
        checks for duplicate items with different units, and duplicate items where only the quantity is different 
        (same name, unit, purchase date, expiry date, remarks)
        MUST RUN when expiry date changes
        """
        #check for duplicate items where only the quantity is different 
        #(same name, unit, purchase date, expiry date, remarks)
        for item in self.__items:
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