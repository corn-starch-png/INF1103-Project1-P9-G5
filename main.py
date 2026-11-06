#-------START OF DEPENDENCY LINE----------#
try:
    from dotenv import load_dotenv
    from datetime import date, timedelta
    import sys
    from DB_manager import (load_database_refactored, save_database_refactored)
    from IO_manager import IO_manager
    from core.Fridge import Fridge
    from core.Household import Household
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData
    from aiclasses.AI_manager import AIManager
    from aiclasses.OpenRouterProvider import OpenRouterProvider
    from Logic_manager import (under_buy, calories_surplus, risk_of_expiry, calculate_confidence_score, should_evaluate_underbuy)
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")
# Load environment variables once
load_dotenv()
ui = IO_manager()

from DB_manager import (load_database_refactored, save_database_refactored)
errors, fridge, household_info, history = load_database_refactored("database")

#region AI Recommendations
# ui.send_message("Getting AI recommendations... This can take a while.")
# # Convert the grocery cart into the dictionary format expected by AIManager.
# grocery_list = [item.to_dict() for item in cart.get_items()]
# # Convert the refactored database objects into AI-compatible dictionaries.
# household_data = household_info.to_dicts()
# consumption_data = history.to_dicts()

# # Exclude expired fridge items from AI calculations.
# usable_fridge = [item.to_dict() for item in fridge.get_items() if not item.is_expired()]
# expired_count = len(fridge.get_items()) - len(usable_fridge)
# if expired_count > 0:
#     ui.send_message(f"Warning: {expired_count} expired fridge batch(es) excluded from AI recommendations.\nPlease review or remove expired food.")
# # Initialize AI Manager with the OpenRouter provider.
# ai_manager = AIManager(OpenRouterProvider())
# # Generate recommendations.
# ai_recommendations, error = ai_manager.get_ai_recommendations(household_info=household_data, consumption_history=consumption_data, fridge_stock=usable_fridge, purchase_stock=grocery_list, remarks=remarks, days_until_next=days_until_next_visit)
# # Handle unsuccessful AI requests.
# if error or ai_recommendations is None:
#     raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")
# # Extract validated AI results.
# recommendations = ai_recommendations["Recommendations_List"]
# total_planned_calories = ai_recommendations["Total_Planned_Estimated_Calories"]
# total_recommended_calories = ai_recommendations["Total_Estimated_Calories"]
#endregion

#region Attach AI Recommendations
# if len(recommendations) != len(cart.get_items()):
#     raise ValueError("AI recommendation count does not match the grocery cart.")

# for cart_item, recommendation in zip(cart.get_items(), recommendations):
#     ai_data = AIRecData(recommended_qty=recommendation["Recommended_Quantity"], consumption_rate=recommendation["Estimated_Consumption_Rate"], est_expiry_date=recommendation["Estimated_Expiry_Date"])
#     cart_item.set_ai_data(ai_data)
#endregion

#save_database_refactored(fridge, household_info, history)