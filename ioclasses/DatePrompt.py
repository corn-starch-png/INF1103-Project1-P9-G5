from datetime import date
from ioclasses.Prompt import Prompt


# Asks for an expiry date in YYYY-MM-DD format between min_date and max_date (inclusive),
# and not before purchase_date if one is given. Warns the user if the date has already passed.
class DatePrompt(Prompt):
    def __init__(self, question, min_date, max_date, purchase_date=""):
        super().__init__(question)
        self.__min_date = min_date
        self.__max_date = max_date
        self.__purchase_date = purchase_date

    def _validate(self, text):
        if (
            len(text) != 10
            or text[4] != "-"
            or text[7] != "-"
            or not text[:4].isdigit()
            or not text[5:7].isdigit()
            or not text[8:].isdigit()
        ):
            return "Please enter a date in YYYY-MM-DD format."
        try:
            entered_date = date.fromisoformat(text)
        except ValueError:
            return "Invalid calendar date. Please try again."
        if entered_date < self.__min_date:
            return f"Expiry date cannot be earlier than {self.__min_date.isoformat()}."
        if entered_date > self.__max_date:
            return f"Expiry date cannot be later than {self.__max_date.isoformat()}."
        if self.__purchase_date and entered_date < date.fromisoformat(self.__purchase_date):
            return "Expiry date cannot be earlier than the recorded purchase date."
        return ""

    def _convert(self, text):
        if date.fromisoformat(text) < date.today():
            print("Warning: this item has already expired. Do not consume it.")
        return text