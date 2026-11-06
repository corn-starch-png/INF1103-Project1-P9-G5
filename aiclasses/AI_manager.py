from dotenv import load_dotenv
from datetime import date, timedelta
from dotenv import load_dotenv

from DB_manager import send_log

from .AIProvider import AIProvider
from .OpenRouterProvider import OpenRouterProvider
from .PromptBuilder import PromptBuilder
from .AIResponseValidator import AIResponseValidator

#region AI Recommendation Entry Point
def get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock, remarks, days_until_next):
    manager = AIManager(OpenRouterProvider())
    return manager.get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock, remarks, days_until_next)
#endregion

#region AI Manager
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
        
    def get_ai_recommendations(self, household_info: dict, consumption_history: list, fridge_stock: list, purchase_stock: list, remarks: str, days_until_next: int) -> tuple:
        # Check API connection
        send_log("Checking AI API connection...")
        connected, message = self._provider.check_connection()
        if not connected:
            send_log("AI API connection failed.")
            send_log(f"[AI STATUS] {message}")
            return None, message
        send_log("[AI STATUS] AI provider ready.")
        # Prepare AI input
        send_log("[AI STATUS] Preparing AI input...")
        current_date = date.today()
        next_purchase_date = self._get_next_purchase_date(current_date, days_until_next)
        data = self._prepare_data(household_info, consumption_history, fridge_stock, purchase_stock, remarks, current_date, next_purchase_date)

        # Build AI prompt
        send_log("[AI STATUS] Building AI prompt...")
        prompt = self._prompt_builder.build_ai_prompt(data)

        # Generate AI recommendations
        send_log("[AI STATUS] Sending prompt to AI...")
        result, error = self._provider.generate(prompt, self._validator.get_recommendation_schema(), purchase_stock, self._validator)

        if error:
            send_log("[AI] AI request failed.")
            send_log(f"[AI] {error}")
        return result, error
#endregion