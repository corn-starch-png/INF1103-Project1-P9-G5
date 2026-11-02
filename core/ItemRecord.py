from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from Record import Record


class ItemRecord(Record):
    """
    Abstract record for anything that has a name, a quantity and a unit.

    It stays abstract because it does not implement Record's abstract methods
    (validate / to_dict / from_dict); concrete subclasses must.
    """

    MAX_NAME_LENGTH = 50
    MAX_QUANTITY = 1_000_000
    QUANTITY_STEP = Decimal("0.0001")
    VALID_UNITS = ("kg", "g", "l", "ml", "pcs")

    def __init__(self, name: str, quantity: float, unit: str):
        self._name = name
        self._quantity = quantity
        self._unit = unit

    # --- read-only accessors for the protected attributes -----------------
    @property
    def name(self) -> str:
        return self._name

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def unit(self) -> str:
        return self._unit

    # --- protected helpers shared by the subclasses -----------------------
    @staticmethod
    def _parse_quantity(value):
        """Return value as a Decimal if it is a finite number in [0, MAX_QUANTITY], else None."""
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            return None
        try:
            amount = Decimal(str(value))
        except InvalidOperation:
            return None
        if not amount.is_finite() or amount < 0 or amount > ItemRecord.MAX_QUANTITY:
            return None
        return amount

    def _validate_item_fields(self, allow_zero_quantity: bool = False) -> bool:
        """Validate name, unit and quantity using the rules from the original database checks."""
        if not isinstance(self._name, str) or not self._name.strip():
            return False
        if len(self._name) > self.MAX_NAME_LENGTH:
            return False
        if self._unit not in self.VALID_UNITS:
            return False

        amount = self._parse_quantity(self._quantity)
        if amount is None:
            return False
        if amount == 0 and not allow_zero_quantity:
            return False
        if amount != amount.quantize(self.QUANTITY_STEP, rounding=ROUND_HALF_UP):
            return False
        if self._unit == "pcs" and amount != amount.to_integral_value():
            return False
        return True

    def _set_quantity(self, new_amount: float) -> None:
        """Replace the quantity with new_amount (must be > 0). Raises ValueError if invalid."""
        amount = self._parse_quantity(new_amount)
        if amount is None or amount == 0:
            raise ValueError("Quantity must be a number greater than 0 and at most 1,000,000.")
        amount = amount.quantize(self.QUANTITY_STEP, rounding=ROUND_HALF_UP)
        if amount == 0:
            raise ValueError("Quantity is too small.")
        if self._unit == "pcs" and amount != amount.to_integral_value():
            raise ValueError("Quantity in pcs must be a whole number.")
        self._quantity = float(amount)
