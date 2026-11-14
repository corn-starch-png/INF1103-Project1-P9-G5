from typing import Callable
from dotenv import load_dotenv
from datetime import date, timedelta
from dotenv import load_dotenv
from logger import app_logger
from .AIProvider import AIProvider
from .OpenRouterProvider import OpenRouterProvider
from .PromptBuilder import PromptBuilder
from .AIResponseValidator import AIResponseValidator
from modules.core.Household import Household
from modules.core.ConsumptionHistory import ConsumptionHistory
from modules.core.Fridge import Fridge
from modules.core.Cart import Cart
from modules.core.AIRecData import AIRecData

# region AI Manager
class AIManager:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider
        self._prompt_builder = PromptBuilder()
        self._validator = AIResponseValidator()
    def _prepare_data(self, household_info: dict, consumption_history: list, fridge_stock: list, grocery_list_input: list, remarks: str, current_date: date, next_purchase_date: date) -> dict:
        return {"household_info": household_info, "consumption_history": consumption_history, 
                "fridge_stock": fridge_stock, "planned_grocery_list": grocery_list_input, 
                "remarks": remarks, "current_date": current_date, "next_purchase_date": next_purchase_date}
    def _get_next_purchase_date(self, current_date: date, days_until_next: int) -> date:
        try:
            next_purchase_date = current_date + timedelta(days=days_until_next)
            return next_purchase_date
        except ValueError:
            raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")

    def _attach_ai_recommendations(self, cart: Cart, recommendations: list[dict]) -> None:
        cart_items = cart.get_items()
        if len(recommendations) != len(cart_items):
            raise ValueError("AI recommendation count does not match the grocery cart.")
        for cart_item, recommendation in zip(cart_items, recommendations):
            if (cart_item.name != recommendation["Item_Name"] or cart_item.quantity != recommendation["Planned_Quantity"] or cart_item.unit != recommendation["Unit"] ): 
                raise ValueError( f"AI recommendation does not match cart item: {cart_item.name}" )
            # FLAG setting item data to an item derived from get_items() function
            cart_item.set_ai_data(recommended_qty=recommendation["Recommended_Quantity"], consumption_rate=recommendation["Estimated_Consumption_Rate"], est_expiry_date=recommendation["Estimated_Expiry_Date"])
    
    def get_ai_recommendations(self, household_info: Household, consumption_history: ConsumptionHistory, fridge_stock: Fridge, purchase_stock: Cart, remarks: str, days_until_next: int, notify: Callable[[str], None] | None = None) -> tuple:    
        app_logger.send_log("Checking AI API connection...")
        connected, message = self._provider.check_connection()
        if not connected:
            app_logger.send_log("AI API connection failed.")
            app_logger.send_log(f"[AI STATUS] {message}")
            return None, message
        app_logger.send_log("[AI STATUS] AI provider ready.")
        # Prepare AI input
        app_logger.send_log("[AI STATUS] Preparing AI input...")
        current_date = date.today()
        next_purchase_date = self._get_next_purchase_date(current_date, days_until_next)
        # Exclude expired fridge items from AI calculations.
        usable_fridge = [item.to_dict() for item in fridge_stock.get_items() if not item.is_expired()]
        expired_count = len(fridge_stock.get_items()) - len(usable_fridge)
        if expired_count > 0:
            warning = (f"Warning: {expired_count} expired fridge batch(es) excluded from AI recommendations.\nPlease review or remove expired food.")
            app_logger.send_log(f"[AI STATUS] {warning}")
            if notify:
                notify(warning)
        # Convert objects into dictionaries for the AI prompt.
        data = self._prepare_data(household_info=household_info.to_dicts(),
            consumption_history=consumption_history.to_dicts(), fridge_stock=usable_fridge,
            grocery_list_input=[item.to_dict() for item in purchase_stock.get_items()],
            remarks=remarks, current_date=current_date, next_purchase_date=next_purchase_date)
        # Build AI prompt
        app_logger.send_log("[AI STATUS] Building AI prompt...")
        prompt = self._prompt_builder.build_ai_prompt(data)
        # Generate AI recommendations
        app_logger.send_log("[AI STATUS] Sending prompt to AI...")
        result, error = self._provider.generate(prompt, self._validator.get_recommendation_schema(), data["planned_grocery_list"], self._validator)
        if error or result is None:
            app_logger.send_log("[AI] AI request failed.")
            app_logger.send_log(f"[AI] {error}")
            return None, error or "No AI response returned."
        # Attach validated AI recommendations to CartItem objects.
        self._attach_ai_recommendations(purchase_stock, result["Recommendations_List"])

        return result, error