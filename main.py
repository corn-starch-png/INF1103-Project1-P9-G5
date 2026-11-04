#-------START OF DEPENDENCY LINE----------#
try:
    from datetime import date, timedelta
    import sys
    from DB_manager import (database_exists, load_database, save_database, update_household_info, log_exists,
                            add_to_fridge, remove_from_fridge, update_consumption_history, get_all_fridge_quantity,
                            merge_fridge_batches, send_log)
    from IO_manager import IO_manager
    from core.Fridge import Fridge
    from core.Household import Household
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData
    from AI_manager import AIManager
    from core.AI_classes import OpenRouterProvider
    from Logic_manager import (under_buy, calories_surplus, risk_of_expiry, calculate_confidence_score, should_evaluate_underbuy)
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")

ui = IO_manager()

def load_objects(database):
    household_info = Household()
    history = ConsumptionHistory()
    fridge = Fridge()
    for error in household_info.load_dicts(database["household_info"]) + history.load_dicts(database["consumption_history"]) + fridge.load_dicts(database["fridge"]):
        send_log(f"[MAIN] {error}")
    return household_info, history, fridge

def to_rows(records):
    rows = []
    for record in records:
        row = record.to_dict()
        row.pop("Record_Date", None)
        rows.append(row)
    return rows

#here for integration testing
#will remove once the refactored code is fully implemented and tested
USING_REFACTORED_CODE = False
if USING_REFACTORED_CODE:
    from DB_manager import (load_database_refactored, save_database_refactored)
    errors, fridge, household_info, history = load_database_refactored("database")
    database = {"consumption_history": history.to_dicts(), "household_info": household_info.to_dicts(), "fridge": fridge.to_dicts()}
else:
    log_exists()
    database_exists()  # Ensure the database folder and file exist
    db_success, database = load_database('database')  # Load the database into memory
    database["fridge"][:] = merge_fridge_batches(database["fridge"])
    send_log(f"[MAIN] database: {database}")
    if db_success == False:
        ui.send_message(f"Database loading encountered issues, data may be missing")
household_info, history, fridge = load_objects(database)

existing_fridge_items = []
consumed_items = []
#-------END OF DEPENDENCY LINE----------#
#region user IO
ui.show_welcome()
#if new user, direct them to create a new profile then add items they have in thier fridge
if not household_info.get_members():
    household_info = ui.create_profile()
    ui.show_profile(household_info)
    existing_fridge_items = ui.enter_home_items()
    ui.display_list("Fridge", existing_fridge_items)
    database = update_household_info(database, household_info.to_dicts())
    database = add_to_fridge(database, [item.to_dict() for item in existing_fridge_items])
    household_info, history, fridge = load_objects(database)
else:
    ui.show_welcome_back(household_info)
    while True:
        choice = ui.ask_menu_choice()
        #update consumption history then break loop and continue
        if choice == "1":
            consumed_records = ui.update_consumption(fridge)
            consumed_items = to_rows(consumed_records)
            database = remove_from_fridge(database, consumed_items)
            database = update_consumption_history(database, consumed_items)
            household_info, history, fridge = load_objects(database)
            ui.show_consumption(consumed_records)
            break
        #give user option to edit AI estimated expiry dates or delete items(for example if expired)
        elif choice == "2":
            ui.update_fridge(fridge)
            database["fridge"] = fridge.to_dicts()
        #exit program
        else:
            if USING_REFACTORED_CODE:
                save_database_refactored(fridge, household_info, history, 'database')
            else:
                save_database(database, 'database')  # Save the database to the specified folder
            ui.show_exit()
            sys.exit(1)

days_until_next_visit = ui.ask_days_until_next()
cart = ui.enter_grocery_list(fridge, history)
remarks = ui.ask_remarks()
grocery_list = [item.to_dict() for item in cart.get_items()]

send_log(f"[MAIN] \n--- IO results ---")
send_log(f"[MAIN] household_info = {household_info.to_dicts()}")
send_log(f"[MAIN] existing_items = {[item.to_dict() for item in existing_fridge_items]}")
send_log(f"[MAIN] consumed_items = {consumed_items}")
send_log(f"[MAIN] grocery_list = {grocery_list}")
send_log(f"[MAIN] remarks = {remarks}")
send_log(f"[MAIN] days_until_next_visit = {days_until_next_visit}")
#endregion

#region AI Recommendations
ui.send_message("Getting AI recommendations... This can take a while")
# retains expired items for review but excludes them from the AI's usable stock input.
fridge_rows = database['fridge']
usable_fridge = [item for item in fridge_rows if date.fromisoformat(item["Expiry_Date"]) >= date.today()]
if len(usable_fridge) < len(fridge_rows):
    ui.send_message(f"Warning: {len(fridge_rows) - len(usable_fridge)} expired fridge batch(es) excluded from recommendations.\nReview/remove expired food.")
# Initialize AI Manager with OpenRouter provider
ai_manager = AIManager(OpenRouterProvider())
# Generate AI recommendations
ai_recommendations, error = ai_manager.get_ai_recommendations(household_info.to_dicts(), database['consumption_history'], usable_fridge, grocery_list, remarks, days_until_next_visit)
if error or ai_recommendations is None:
    raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")
# Extract recommendation data
recommendations = ai_recommendations.get("Recommendations_List", [])
total_planned_calories = ai_recommendations.get("Total_Planned_Estimated_Calories", 0)
total_recommended_calories = ai_recommendations.get("Total_Estimated_Calories", 0)

send_log(f"[MAIN] Total Planned Estimated Calories: {total_planned_calories}")
send_log(f"[MAIN] Total Recommended Calories: {total_recommended_calories}")
#endregion

#region logic
extra_calories, calories_message = calories_surplus(database, total_planned_calories, days_until_next_visit)
risk_of_expiry_messages = []
underbuy_messages = []

for item in recommendations:
    fridge_amt = get_all_fridge_quantity(database, item["Item_Name"], include_expired=False)
    total_amt = fridge_amt + item["Planned_Quantity"] #total amount of item in grocery list AND currently in fridge

    expire_before_consume, expiry_message = risk_of_expiry(item, total_amt)
    if expiry_message is not None:
        risk_of_expiry_messages.append(expiry_message)

    next_purchase_date = str(date.today() + timedelta(days=days_until_next_visit))
    if should_evaluate_underbuy(extra_calories, expire_before_consume):
        need_to_buy_more, underbuy_message = under_buy(item, next_purchase_date, total_amt)

        if underbuy_message is not None:
            underbuy_messages.append(underbuy_message)

    item["Confidence_Score"] = calculate_confidence_score(item["Item_Name"], database, item["Recommended_Quantity"], fridge_amt, days_until_next_visit, remarks)

for cart_item, item in zip(cart.get_items(), recommendations):
    ai_data = AIRecData(item["Recommended_Quantity"], item.get("Consumption_Rate", 0), item["Estimated_Expiry_Date"])
    ai_data.set_confidence_score(item["Confidence_Score"])
    cart_item.set_ai_data(ai_data)
#endregion

#region user IO confirmation
ui.output_recommendations(calories_message, risk_of_expiry_messages, underbuy_messages, recommendations)

final_checkout = ui.shopping_cart_conclusion(cart, remarks)

database = add_to_fridge(database, [item.to_dict() for item in final_checkout])

if USING_REFACTORED_CODE:
    household_info, history, fridge = load_objects(database)
    save_database_refactored(fridge, household_info, history, 'database')  # Save the database to the specified folder
else:
    save_database(database, 'database')  # Save the database to the specified folder
ui.show_exit()
#endregion