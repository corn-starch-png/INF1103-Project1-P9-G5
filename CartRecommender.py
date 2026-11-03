from datetime import date, timedelta

from core.ConsumptionHistory import ConsumptionHistory
from core.Fridge import Fridge
from core.Cart import Cart
from core.CartItem import CartItem

class CartRecommender:

    RECENT_DAYS_THRESHOLD = 14  # Number of days to consider a record as recent

    def __init__(self, fridge: Fridge, history: ConsumptionHistory):
        self.__fridge = fridge
        self.__history = history

    def recommend_cart(self) -> list:
        recommendations = Cart()
        fridge_items = self.__fridge.get_unique_item_names()
        for name in fridge_items:
            item_records = self.__history.search_records(name)
            if item_records:
                latest_record_date = max(record.record_date for record in item_records)
                if self.__check_item_recent(latest_record_date) and latest_record_date != 0:
                    if self.__check_item_consumption(name):
                        pass
                        #TODO: add logic to determine quantity to recommend
                        #TODO: create CartItem and add to recommendations

    def __check_item_recent(self, record_date: str) -> bool:
        """
        Check if the record date is within the recent days threshold.
        user won't be recommended items they haven't consumed in a long time
        """
        record_date_obj = date.fromisoformat(record_date)
        return (date.today() - record_date_obj).days <= self.RECENT_DAYS_THRESHOLD


    def __check_item_consumption(self, name: str) -> bool:
        """
        Check the average consumption rate of the item and determine if it should be 
        recommended based on stock levels.
        """
        normalized_records = self.__history.get_normalized_records(name)
        if not normalized_records:
            return False  # No consumption records found

        average_consumption = sum(normalized_records) / len(normalized_records)
        fridge_quantity = self.__fridge.get_total_quantity(name, True)

        # Recommend if the average consumption is greater than the current stock
        return average_consumption > fridge_quantity
            