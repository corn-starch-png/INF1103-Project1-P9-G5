from decimal import Decimal
from .Prompt import Prompt

class EditQuantityPrompt(Prompt):
    def __init__(self, question, whole_number, max_quantity):
        super().__init__(question)
        self.__whole_number = whole_number
        self.__max_quantity = max_quantity

    def _validate(self, text):
        if not text.replace(".", "", 1).isdecimal():
            return "Invalid input. Enter a positive number"
        # Treat only an exact zero as the delete command.
        if Decimal(text) == 0:
            return ""
        if self.__whole_number and not text.isdigit():
            return "quantity must be a whole number for unit pcs"
        try:
            new_qty = self.normalize_quantity(text)
        except ValueError:
            return f"Quantity cannot exceed {self.__max_quantity:,}."
        if new_qty == 0:
            return "Quantity is too small after rounding to 4 decimal places."
        return ""

    def _convert(self, text):
        if float(text) == 0:
            return 0
        return self.normalize_quantity(text)
