#-------START OF DEPENDENCY LINE----------#
try:
    from dotenv import load_dotenv
    from datetime import date, timedelta
    import sys
    from DB_manager import DB_manager
    from IO_manager import IO_manager
    from Logic_manager import Logic_manager
    from core.Fridge import Fridge
    from core.Household import Household
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData
    from logicclasses.AnalysisContext import AnalysisContext
    from dbclasses.JsonRepository import JsonRepository
    from dbclasses.MongoDBRepository import MongoDBRepository
    from aiclasses.AI_manager import AIManager
    from aiclasses.OpenRouterProvider import OpenRouterProvider
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")
# Load environment variables once
load_dotenv()
REPOSITORY = JsonRepository(folder="database")
ui = IO_manager()
logicmgr = Logic_manager()


errors, data_bundle = DB_manager().load_database(REPOSITORY)
fridge = data_bundle["fridge"]
household_info = data_bundle["household"]
history = data_bundle["consumption_history"]
#-------END OF DEPENDENCY LINE----------#
#region user IO
ui.show_welcome()
#if new user, direct them to create a new profile then add items they have in thier fridge
if not household_info.get_members():
    #TODO this will not change the actual household being used, but will instead point household_info to another household
    household_info = ui.create_profile()
    ui.show_profile(household_info)
    #TODO same logic as above
    fridge = ui.create_fridge()
    ui.display_list("Fridge", fridge.get_items())
else:
    ui.show_welcome_back(household_info)
    while True:
        choice = ui.ask_menu_choice()
        #update consumption history then break loop and continue
        if choice == "1":
            last_used_days = ui.ask_last_use_days()
            consumption_remarks = ui.get_consumption_remarks()

            total_items = fridge.get_fridge_totals()
            total_records = []
            for combined_item in total_items:
                consumed_amount = ui.get_consumption(combined_item['item_name'], combined_item['quantity'], combined_item['units']) # list of consumption records
                record = fridge.consume(combined_item['item_name'], consumed_amount, combined_item['units'], last_used_days, consumption_remarks)
                history.add_record(record)
                total_records.append(record)

            ui.show_consumption(total_records)
            break
        #give user option to edit AI estimated expiry dates or delete items(for example if expired)
        elif choice == "2":
            ui.update_fridge(fridge)
        #exit program
        else:
            DB_manager().save_database(REPOSITORY)
            ui.show_exit()
            sys.exit(0)

days_until_next_visit = ui.ask_days_until_next()
#TODO display recommended cart
#TODO let user choose start new cart or use recommened cart
cart = ui.enter_grocery_list(fridge, history)
remarks = ui.ask_remarks()
cart.set_remarks(remarks)

#region AI Recommendations
ui.send_message("Getting AI recommendations... This can take a while.")
# Initialize AI Manager with the OpenRouter provider.
ai_manager = AIManager(OpenRouterProvider())
# Generate recommendations.
ai_recommendations, error = ai_manager.get_ai_recommendations(
    household_info=household_info, 
    consumption_history=history, 
    fridge_stock=fridge, 
    purchase_stock=cart, 
    remarks=cart.get_remarks(), 
    days_until_next=days_until_next_visit,
    notify=ui.send_message
    )
# Handle unsuccessful AI requests.
if error or ai_recommendations is None:
    raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")
# Extract validated AI results.
recommendations = ai_recommendations["Recommendations_List"]
total_planned_calories = ai_recommendations["Total_Planned_Estimated_Calories"]
total_recommended_calories = ai_recommendations["Total_Estimated_Calories"]
#endregion

#create context object for logic calculations
context = AnalysisContext(cart= cart,
                          household= household_info,
                          fridge= fridge,
                          history= history,
                          total_est_calories= total_planned_calories,
                          next_purchase_date= days_until_next_visit
                          )

cart = logicmgr.add_confidence_score(ctx=context)

findings = logicmgr.process_recommendations(ctx= context)

calorie_msg = logicmgr.get_recommedations("CaloriesSurplus")
roe_msgs = logicmgr.get_recommedations("RiskOfExpiry")
underbuy_msgs = logicmgr.get_recommedations("UnderBuy")


#region user IO confirmation
ui.output_recommendations(calorie_msg, roe_msgs, underbuy_msgs)

ui.shopping_cart_conclusion(cart) #output is list of fridge_items
cart.checkout(fridge)

DB_manager().save_database(REPOSITORY)  # Save the database to the specified folder
ui.show_exit()
