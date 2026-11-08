from datetime import date

from core.ItemRecord import ItemRecord


class ConsumptionRecord(ItemRecord):
    """Quantity of an item the household consumed over a number of days."""

    MIN_DATE_RANGE = 1
    MAX_DATE_RANGE = 365

    def __init__(self, name: str, quantity: float, unit: str, date_range: int,
                 remarks: str = "", record_date: str = None):
        super().__init__(name, quantity, unit)
        self.__date_range = date_range
        self.__record_date = record_date if record_date is not None else date.today().isoformat()
        self.__remarks = remarks

    @property
    def record_date(self) -> str:
        return self.__record_date

    @property
    def date_range(self) -> int:
        return self.__date_range

    def validate(self) -> bool:
        if not self._validate_item_fields(allow_zero_quantity=True):
            return False
        if type(self.__date_range) is not int:
            return False
        if not self.MIN_DATE_RANGE <= self.__date_range <= self.MAX_DATE_RANGE:
            return False
        try:
            if date.fromisoformat(self.__record_date).isoformat() != self.__record_date:
                return False
        except (TypeError, ValueError):
            return False
        if not isinstance(self.__remarks, str) or len(self.__remarks) > ItemRecord.MAX_REMARKS_LENGTH:
            return False
        return True

    # NOTE: not drawn in the diagram, but required: Record declares these as abstract,
    # so without them ConsumptionRecord could not be instantiated.
    def to_dict(self) -> dict:
        return {
            "Date_Range": self.__date_range,
            "Item_Name": self._name,
            "Quantity": self._quantity,
            "Unit": self._unit,
            "Remarks": self.__remarks,
            "Record_Date": self.__record_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConsumptionRecord":
        return cls(
            data["Item_Name"],
            data["Quantity"],
            data["Unit"],
            data["Date_Range"],
            data.get("Remarks", ""),
            data.get("Record_Date"),
        )

    def daily_rate(self) -> float:
        """Average quantity consumed per day over the record's date range."""
        if type(self.__date_range) is not int or self.__date_range < 1:
            raise ValueError("date_range must be a positive integer.")
        return self._quantity / self.__date_range
