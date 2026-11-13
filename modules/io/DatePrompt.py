from datetime import date
from .Prompt import Prompt
from modules.core.ItemRecord import ItemRecord

# Asks for an expiry date in YYYY-MM-DD format between min_date and max_date (inclusive),
# and not before purchase_date if one is given. Warns the user if the date has already passed.
class DatePrompt(Prompt):
    # Editing may keep the existing date or cancel without changing the record.
    def __init__(self, question, allow_past=False, purchase_date="", current_date=None):
        super().__init__(question)
        self.__current_date = current_date

        today = date.today()
        earliest = ItemRecord.shift_calendar_years(today, -1) if allow_past else today
        latest = ItemRecord.shift_calendar_years(today, 3)

        self.__min_date = earliest
        self.__max_date = latest
        self.__purchase_date = purchase_date

    # An unchanged historical date is valid even outside today's input window.
    def _validate(self, text):
        if self.__current_date is not None and (text.lower() in ("", "cancel") or text == self.__current_date):
            return ""
        if (len(text) != 10
            or text[4] != "-"
            or text[7] != "-"
            or not text[:4].isdigit()
            or not text[5:7].isdigit()
            or not text[8:].isdigit()):
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

    # Cancellation returns no replacement date; ordinary date warnings remain.
    def _convert(self, text):
        if self.__current_date is not None and text.lower() in ("", "cancel"):
            return None
        if date.fromisoformat(text) < date.today():
            print("Warning: this item has already expired. Do not consume it.")
        return text
