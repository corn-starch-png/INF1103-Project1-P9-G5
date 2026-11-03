from core.ConsumptionRecord import ConsumptionRecord
from core.CanBeStored import CanBeStored

class ConsumptionHistory(CanBeStored):
    """Past consumption records (aggregation of ConsumptionRecord)."""

    def __init__(self):
        self.__records = []

    def add_record(self, record: ConsumptionRecord) -> None:
        if not isinstance(record, ConsumptionRecord):
            raise TypeError("Only ConsumptionRecord objects can be added to the history.")
        if not record.validate():
            raise ValueError("Cannot add an invalid record to the consumption history.")
        self.__records.append(record)

    def search_records(self, item_name: str) -> list:
        wanted = item_name.strip().casefold()
        wanted_records = []
        for record in self.__records:
            if record.name.strip().casefold() == wanted:
                wanted_records.append(record)
        return wanted_records

    def get_normalized_records(self, item_name: str) -> list:
        """
        Return one daily-consumption value per day for the given item, e.g. a record of
        14 kg over 7 days adds seven values of 2.0.
        """
        wanted = item_name.strip().casefold()
        normalized = []
        for record in self.__records:
            if record.name.strip().casefold() == wanted:
                normalized.extend([record.daily_rate()] * record.date_range)
        return normalized

    def to_dicts(self) -> list:
        return [record.to_dict() for record in self.__records]
 
    def load_dicts(self, rows: list) -> list:
        errors = []
        for row in rows:
            try:
                self.add_record(ConsumptionRecord.from_dict(row))
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"Skipped invalid consumption history row {row!r}: {error!r}")
        return errors
 
