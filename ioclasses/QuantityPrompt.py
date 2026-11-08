from decimal import Decimal
from ioclasses.Prompt import Prompt


# Asks for a quantity

class QuantityPrompt(Prompt):
    def __init__(self, question, max_value=None, allow_zero=False, whole_number=False,
                 normalize=False, max_message=None):
        super().__init__(question)
        self.__max = max_value
        self.__allow_zero = allow_zero
        self.__whole_number = whole_number
        self.__normalize = normalize
        self.__max_message = max_message

    def _validate(self, text):
        if not text.replace(".", "", 1).isdecimal():
            return "Please enter a valid number."
        if self.__whole_number and not text.isdecimal():
            return "Quantity in pcs must be a whole number."
        if Decimal(text) == 0:
            if self.__allow_zero:
                return ""
            return "Quantity must be more than 0."
        if self.__max is not None and Decimal(text) > Decimal(str(self.__max)):
            if self.__max_message is not None:
                return self.__max_message
            return f"Quantity cannot be more than {self.__max}."
        if self.__normalize is True:
            try:
                rounded = self.normalize_quantity(text)
            except ValueError:
                return "Invalid or excessively large quantity."
            if rounded == 0:
                return "Quantity is too small after rounding to 4 decimal places."
        return ""

    def _convert(self, text):
        if self.__normalize is True:
            return self.normalize_quantity(text)
        return float(text)