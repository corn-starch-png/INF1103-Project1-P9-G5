from datetime import date

from core.Cart import Cart
from core.ConsumptionHistory import ConsumptionHistory
from core.Fridge import Fridge

class CartRecommender:
    """
    returns a list of item_names that the user frequently consumes, and is running out
    """
    RECENT_DAYS_THRESHOLD = 14  # Number of days to consider a record as recent

    def __init__(self, fridge: Fridge, history: ConsumptionHistory):
        self.__fridge = fridge
        self.__history = history

    def generate_recommendation(self) -> list:
        recommendations = Cart() 
        history_items = self.__history.get_unique_item_names()
        for name in history_items:
            item_records = self.__history.search_records(name)
            if item_records:
                latest_record_date = max(record.record_date for record in item_records)
                if self.__check_item_recent(latest_record_date) and latest_record_date != 0:
                    if self.__check_item_consumption(name):
                        pass
                        #TODO create CartItem from past consumption history
                        #recommendations.add_item()
        return recommendations

    def display_recommendation(self) -> str:
        recommendations = self.generate_recommendation()
        message = f"Recommended items to buy: \n"
        longest_string = max(max(len(name) for name in recommendations), len(message))
        message += f"|{"-"*(longest_string-1)}|\n"
        for item in recommendations:
            message += f"| {item:<{longest_string-2}}|\n"
            message += f"|{"-"*(longest_string-1)}|\n"
        print(message)

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
        fridge_quantity = self.__fridge.get_total_quantity(name, False)
        
        item_records = self.__history.search_records(name)
        average_days_between_trips = sum(record.date_range for record in item_records)/len(item_records)

        # Recommend if the average consumption is greater than the current stock
        return (average_consumption * average_days_between_trips) > fridge_quantity
            