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

errors, fridge, household_info, history = load_database_refactored("database")
#-------END OF DEPENDENCY LINE----------#
#region user IO
ui.show_welcome()
#if new user, direct them to create a new profile then add items they have in thier fridge
if not household_info.get_members():
    household_info = ui.create_profile()
    ui.show_profile(household_info)
    #TODO cleanup 
    fridge = ui.create_fridge()
    ui.display_list("Fridge", fridge.get_items())
else:
    ui.show_welcome_back(household_info)
    while True:
        choice = ui.ask_menu_choice()
        #update consumption history then break loop and continue
        if choice == "1":
            #TODO move for loop inside update_consumption out here
            consumed_records = ui.update_consumption(fridge) # list of consumption records

            ui.show_consumption(consumed_records)
            break
        #give user option to edit AI estimated expiry dates or delete items(for example if expired)
        elif choice == "2":
            ui.update_fridge(fridge)
        #exit program
        else:
            save_database_refactored(fridge, household_info, history, 'database')
            ui.show_exit()
            sys.exit(0)

days_until_next_visit = ui.ask_days_until_next()
cart = ui.enter_grocery_list(fridge, history)
remarks = ui.ask_remarks()

#region AI Recommendations
ui.send_message("Getting AI recommendations... This can take a while.")
# Initialize AI Manager with the OpenRouter provider.
ai_manager = AIManager(OpenRouterProvider())
# Generate recommendations.
ai_recommendations, error = ai_manager.get_ai_recommendations(household_info=household_info, consumption_history=history, fridge_stock=fridge, purchase_stock=cart, remarks=remarks, days_until_next=days_until_next_visit,notify=ui.send_message)
# Handle unsuccessful AI requests.
if error or ai_recommendations is None:
    raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")
# Extract validated AI results.
recommendations = ai_recommendations["Recommendations_List"]
total_planned_calories = ai_recommendations["Total_Planned_Estimated_Calories"]
total_recommended_calories = ai_recommendations["Total_Estimated_Calories"]
#endregion

#region Attach AI Recommendations
if len(recommendations) != len(cart.get_items()):
    raise ValueError("AI recommendation count does not match the grocery cart.")

for cart_item, recommendation in zip(cart.get_items(), recommendations):
    ai_data = AIRecData(recommended_qty=recommendation["Recommended_Quantity"], consumption_rate=recommendation["Estimated_Consumption_Rate"], est_expiry_date=recommendation["Estimated_Expiry_Date"])
    cart_item.set_ai_data(ai_data)
#endregion

#save_database_refactored(fridge, household_info, history)