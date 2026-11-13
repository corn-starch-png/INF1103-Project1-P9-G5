from abc import ABC, abstractmethod
from modules.core.ItemRecord import ItemRecord
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

class Prompt(ABC):
    def __init__(self, question):
        self._question = question

    def ask(self):
        while True:
            text = input(self._question).strip()
            error = self._validate(text)
            if error == "":
                return self._convert(text)
            print(error)

    # used by Quantity and Quantityunit
    def normalize_quantity(self, value):
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or not 0 <= amount <= ItemRecord.MAX_QUANTITY:
                raise ValueError("Quantity must be between 0 and 1,000,000.")
            return float(amount.quantize(ItemRecord.QUANTITY_STEP,rounding=ROUND_HALF_UP))
        except (InvalidOperation, TypeError) as error:
            raise ValueError("Invalid quantity.") from error

    @abstractmethod
    def _validate(self, text):
        pass

    # Turn valid text into the value to return.
    @abstractmethod
    def _convert(self, text):
        pass