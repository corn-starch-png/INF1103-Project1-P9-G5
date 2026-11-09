from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from modules.core.Cart import Cart
from modules.core.CartItem import CartItem
from modules.core.ConsumptionHistory import ConsumptionHistory
from modules.core.Fridge import Fridge
from modules.core.ItemRecord import ItemRecord

class CartRecommender:
    """
    returns a Cart of items that the user frequently consumes, and is running out
    """
    RECENT_DAYS_THRESHOLD = 14  # Number of days to consider a record as recent

    def __init__(self, fridge: Fridge, history: ConsumptionHistory):
        self.__fridge = fridge
        self.__history = history

    def generate_recommendation(self) -> Cart:
        recommendations = Cart()
        history_items = self.__history.get_unique_item_names()
        for name in sorted(history_items):
            item_records = self.__history.search_records(name)
            if item_records:
                latest_record = max(item_records, key=lambda record: record.record_date)
                if self.__check_item_recent(latest_record.record_date):
                    if self.__check_item_consumption(name):
                        # recommended amount is average_consumption * average_days_between_trips
                        amount = self.__get_recommended_amount(name, latest_record.unit)
                        if amount > 0:
                            recommendations.add_item(CartItem(latest_record.name, amount, latest_record.unit))
        return recommendations

    def __check_item_recent(self, record_date: str) -> bool:
        """
        Check if the record date is within the recent days threshold.
        user won't be recommended items they haven't consumed in a long time
        """
        record_date_obj = date.fromisoformat(record_date)
        return (date.today() - record_date_obj).days <= self.RECENT_DAYS_THRESHOLD

    def __get_expected_consumption(self, name: str) -> float:
        """
        Average daily consumption of the item multiplied by the average number of days between trips.
        Returns 0 if there are no consumption records.
        """
        normalized_records = self.__history.get_normalized_records(name)
        if not normalized_records:
            return 0  # No consumption records found

        average_consumption = sum(normalized_records) / len(normalized_records)
        item_records = self.__history.search_records(name)
        average_days_between_trips = sum(record.date_range for record in item_records)/len(item_records)
        return average_consumption * average_days_between_trips

    def __check_item_consumption(self, name: str) -> bool:
        """
        Check the average consumption rate of the item and determine if it should be 
        recommended based on stock levels.
        """
        fridge_quantity = self.__fridge.get_item_total(name, include_expired=False)

        # Recommend if the average consumption is greater than the current stock
        return self.__get_expected_consumption(name) > fridge_quantity

    def __get_recommended_amount(self, name: str, unit: str) -> float:
        """
        Expected consumption rounded so it is a valid cart quantity:
        pcs is rounded up to a whole number, other units to 4 decimal places.
        Capped at MAX_QUANTITY.
        """
        # Recommend only the expected consumption not already covered by usable fridge stock.
        # Recommend only the expected consumption that usable fridge stock cannot cover.
        # Calculate demand and available stock using decimal arithmetic.
        expected_consumption = Decimal(str(self.__get_expected_consumption(name)))
        available_stock = Decimal(str(self.__fridge.get_item_total(name, include_expired=False)))
        # Subtract existing stock and prevent a negative purchase quantity.
        amount = max(Decimal("0"), expected_consumption - available_stock)        
        amount = amount.quantize(ItemRecord.QUANTITY_STEP, rounding=ROUND_HALF_UP)
        if unit == "pcs":
            amount = amount.to_integral_value(rounding=ROUND_CEILING)
        amount = min(amount, Decimal(ItemRecord.MAX_QUANTITY))
        return float(amount)