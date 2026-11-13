from decimal import Decimal
from .ItemRecord import ItemRecord
from .ListFunctions import ListFunctions
from .FridgeItem import FridgeItem
from .ConsumptionRecord import ConsumptionRecord
from .CanBeStored import CanBeStored


class Fridge(ListFunctions, CanBeStored):
    """Everything currently stored in the fridge (aggregation of FridgeItem)."""

    def __init__(self):
        self.__items = []

    # Enforce one unit for each normalized food name at the domain boundary.
    def validate(self) -> bool:
        units = {}
        for item in self.__items:
            key = item.name.strip().casefold()
            if not item.validate() or (key in units and units[key] != item.unit):
                return False
            units[key] = item.unit
        return True

    def add_item(self, item: FridgeItem) -> bool:
        if not isinstance(item, FridgeItem):
            raise TypeError("Only FridgeItem objects can be added to the Fridge.")
        if not item.validate():
            raise ValueError("Cannot add an invalid item to the fridge.")
        # Reject mixed units before mutating stock, including data loaded from storage.
        for existing in self.__items:
            if existing.name.strip().casefold() == item.name.strip().casefold() and existing.unit != item.unit:
                raise ValueError(f"{item.name} must use {existing.unit}; mixed units cannot be combined.")
        self.__items.append(item)
        try:
            merged = self.remove_duplicates()
            return merged
        except ValueError as e:
            self.__items.remove(item)
            raise ValueError(str(e)) from e

    def change_expiry(self, item: FridgeItem, new_expiry_date: str) -> bool:
        """
        Change the expiry date of an item in the fridge. If the new expiry date causes it to match another batch (same name, unit, purchase date, expiry date and remarks), merge them into one batch.
        Returns true if batches were merged. Raises ValueError and reverts the change if the merged quantity would be over MAX_QUANTITY.
        """
        # Unchanged expiry dates must not trigger merging or quantity updates.
        if item.expiry_date == new_expiry_date:
            return False
        matching_items = []
        total_quantity = Decimal(str(item.quantity))

        # Match equivalent batches inside the loop while skipping this item.
        for existing in self.__items:
            if existing is item:
                continue

            if (existing.name.strip().casefold() == item.name.strip().casefold()
                and existing.unit.strip().casefold() == item.unit.strip().casefold()
                and existing.purchase_date == item.purchase_date
                and existing.expiry_date == new_expiry_date
                and existing.remarks.strip().casefold() == item.remarks.strip().casefold()):
                matching_items.append(existing)
                total_quantity += Decimal(str(existing.quantity))

        if total_quantity > FridgeItem.MAX_QUANTITY:
            raise ValueError(f"Total quantity cannot exceed {FridgeItem.MAX_QUANTITY:,}. Expiry date was not changed.")

        item.edit_expiry_date(new_expiry_date)
        item.set_quantity(total_quantity)

        for existing in matching_items:
            self.remove_item(existing)
        return len(matching_items) > 0

    def remove_item(self, item: FridgeItem) -> None:
        if item not in self.__items:
            raise ValueError("Item is not in the fridge.")
        self.__items.remove(item)

    def get_items(self) -> list:
        return list(self.__items)

    def get_item_at(self, index: int) -> FridgeItem:
        # Safely get the item from the private list by index
        return self.__items[index]
    
    def remove_duplicates(self) -> bool:
        """
        should run after every addition or removal of items to ensure the fridge is valid.
        checks for duplicate items where only the quantity is different 
        (same name, unit, purchase date, expiry date, remarks)
        MUST RUN when expiry date changes
        """
        # check for duplicate items where only the quantity is different
        #(same name, unit, purchase date, expiry date, remarks)
        duplicate_found = False
        for item in self.__items:
            for other_item in self.__items:
                if item is not other_item:
                    if (item.name.strip().casefold() == other_item.name.strip().casefold() and
                        item.unit.strip().casefold() == other_item.unit.strip().casefold() and
                        item.purchase_date == other_item.purchase_date and
                        item.expiry_date == other_item.expiry_date and
                        item.remarks.strip().casefold() == other_item.remarks.strip().casefold()): # change this if we are merging remarks again
                        # merge remarks
                        # new_remarks = other_item.remarks
                        # if item.remarks != "none" and item.remarks != new_remarks:
                        #     if new_remarks == "none":
                        #         new_remarks = item.remarks
                        #     else:
                        #         new_remarks += ", " + item.remarks
                        # if len(new_remarks) > FridgeItem.MAX_REMARKS_LENGTH:
                        #     raise ValueError(f"Combined remarks cannot exceed {FridgeItem.MAX_REMARKS_LENGTH} characters.")
                        # merge the two items by adding their quantities
                        new_amt = item.quantity + other_item.quantity
                        if new_amt > ItemRecord.MAX_QUANTITY:
                            raise ValueError("Error, item is similar to another and merging them will exceed the max quantity")
                        item.set_quantity(new_amt)
                        self.__items.remove(other_item)
                        duplicate_found = True
        return duplicate_found

    def get_fridge_totals(self) -> list:
        """
        Add up each item across all its batches and return a list of dictionaries 
        with keys 'item_name', 'quantity', and 'units'.
        """
        totals = {}
        for item in self.__items:
            key = (item.name.strip().casefold(), item.unit)
            if key in totals:
                totals[key]["quantity"] += Decimal(str(item.quantity))
            else:
                totals[key] = {
                    "item_name": item.name,
                    "quantity": Decimal(str(item.quantity)),
                    "units": item.unit
                }
        return list(totals.values())
     
    def get_item_total(self, item_name: str, include_expired: bool) -> float:
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

        # Count available stock only in the requested measurement unit.
        total_quantity = sum(Decimal(str(item.quantity)) for item in self.__items if item.name.strip().casefold() == item_name.strip().casefold() and item.unit == units)
        # Compare quantities as decimals to avoid float precision errors.
        if Decimal(str(amount)) > total_quantity:
            raise ValueError(f"Cannot consume {amount}{units} of {item_name};\nonly {total_quantity} available.")
        
        # Consume batches using decimal arithmetic while retaining the requested amount for history.
        # Preserve the original quantity for the ConsumptionRecord.
        requested_amount = amount
        # Track the remaining quantity without binary floating-point subtraction errors.
        amount = Decimal(str(amount))
        
        i = 0
        while amount > 0 and i < len(self.__items):
            item = self.__items[i]
            # Reduce matching batches using exact decimal quantities.
            # Consume only batches matching both the item name and unit.
            if (item.name.strip().casefold() == item_name.strip().casefold() and item.unit == units):
                item_quantity = Decimal(str(item.quantity))
                # Remove a fully consumed batch and keep the index on the next shifted batch.
                if item_quantity <= amount:
                    amount -= item_quantity
                    self.__items.pop(i)
                else:
                    # Keep the unconsumed portion and finish processing the requested amount.
                    item.set_quantity(item_quantity - amount)
                    amount = Decimal("0")
                    i += 1
            else:
                # Skip unrelated items so the loop can reach the requested stock.
                i += 1
        return ConsumptionRecord(item_name, requested_amount, units, date_range, consumption_remarks)

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
