from .Prompt import Prompt

class QuantityUnitPrompt(Prompt):
    def __init__(self, item_name, valid_units, locked_unit, max_quantity):
        self.__units = ", ".join(valid_units)
        if locked_unit != "":
            question = f"Quantity in {locked_unit} (e.g. 3): "
        else:
            question = f"Quantity and unit (e.g. 6kg, 500 g, 3 pcs) - units: {self.__units}: "
        super().__init__(question)
        self.__item_name = item_name
        self.__valid_units = valid_units
        self.__locked_unit = locked_unit
        self.__max_quantity = max_quantity

    def __split(self, text):
        # Split where the number ends and the unit begins
        text = text.lower()
        split_at = 0
        while split_at < len(text) and (text[split_at].isdecimal() or text[split_at] == "."):
            split_at += 1
        return text[:split_at], text[split_at:].strip()

    def _validate(self, text):
        number_part, unit = self.__split(text)
        if not number_part.replace(".", "", 1).isdecimal():
            return "Please start with a valid number, e.g. 6kg."
        if float(number_part) <= 0:
            return "Quantity must be more than 0."
        if unit == "" and self.__locked_unit == "":
            return f"Please include a unit ({self.__units}), e.g. 6kg."
        if unit != "" and unit not in self.__valid_units:
            return f"'{unit}' is not a valid unit. Please use one of: {self.__units}."
        if self.__locked_unit != "" and unit != "" and unit != self.__locked_unit:
            return f"{self.__item_name} must be entered in {self.__locked_unit}."
        if (unit or self.__locked_unit) == "pcs" and not number_part.isdigit():
            return "Items in pcs must be a whole number."
        try:
            quantity = self.normalize_quantity(number_part)
        except ValueError:
            return f"Quantity must be a valid number no greater than {self.__max_quantity:,}."
        if quantity == 0:
            return "Quantity is too small after rounding to 4 decimal places."
        return ""

    def _convert(self, text):
        number_part, unit = self.__split(text)
        if unit == "":
            unit = self.__locked_unit
        return self.normalize_quantity(number_part), unit
