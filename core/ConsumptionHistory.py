from core.ConsumptionRecord import ConsumptionRecord


class ConsumptionHistory:
    """Past consumption records (aggregation of ConsumptionRecord)."""

    def __init__(self):
        self.__records = []

    def add_record(self, record: ConsumptionRecord) -> None:
        if not isinstance(record, ConsumptionRecord):
            raise TypeError("Only ConsumptionRecord objects can be added to the history.")
        if not record.validate():
            raise ValueError("Cannot add an invalid record to the consumption history.")
        self.__records.append(record)

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
