#-------START OF DEPENDENCY LINE----------#
import sys
try:
    from datetime import date, timedelta
    import json
    from DB_manager import (database_exists, load_database, save_database, update_household_info, 
                            add_to_fridge, remove_from_fridge, update_consumption_history, get_all_fridge_quantity)
    from IO_manager import (show_welcome, create_profile, show_profile, enter_home_items, show_items, show_welcome_back, 
                            update_consumption, show_consumption, enter_grocery_list, ask_remarks, ask_days_until_next, 
                            shopping_cart_conclusion, ask_menu_choice, edit_fridge, send_log, send_message, output_recommendations)
    from AI_manager import get_ai_recommendations
    from Logic_manager import (under_buy, calories_surplus, risk_of_expiry, calculate_confidence_score, should_evaluate_underbuy)
except ImportError:
    print("requried libraries do not exist")
    sys.exit(1)


database_exists()  # Ensure the database folder and file exist
database = load_database('database')  # Load the database into memory
send_log(f"[MAIN] check database is loaded: {database}")
household_info = database['household_info']
history = database['consumption_history']
fridge = database['fridge']


existing_items = []
consumed_items = []

#-------END OF DEPENDENCY LINE----------#
show_welcome()
if household_info == []:
    household_info = create_profile()
    show_profile(household_info)
    existing_items = enter_home_items()
    show_items("Items at home", existing_items)
    database = update_household_info(database, household_info)
    database = add_to_fridge(database, existing_items)
else:
    show_welcome_back(household_info)
    while True:
        choice = ask_menu_choice()
        if choice == "1":
            consumed_items = update_consumption(fridge)
            database = remove_from_fridge(database, consumed_items)
            database = update_consumption_history(database, consumed_items)
            show_consumption(consumed_items)
            break
        else:
            fridge = edit_fridge(fridge)
            database["fridge"] = fridge
            save_database(database, 'database')  # Save the database to the specified folder
            sys.exit(1)


days_until_next_visit = ask_days_until_next()
grocery_list = enter_grocery_list(database)
remarks = ask_remarks()

send_log(f"[MAIN] \n--- IO results ---")
send_log(f"[MAIN] household_info = {household_info}")
send_log(f"[MAIN] existing_items = {existing_items}")
send_log(f"[MAIN] consumed_items = {consumed_items}")
send_log(f"[MAIN] grocery_list = {grocery_list}")
send_log(f"[MAIN] remarks = {remarks}")
send_log(f"[MAIN] days_until_next_visit = {days_until_next_visit}")


#region AI Recommendations
send_message("Getting AI recommendations... This can take a while")
ai_recommendations, error = get_ai_recommendations(household_info, history, fridge, grocery_list,remarks,days_until_next_visit)
if error or ai_recommendations is None:
    raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")

recommendations = ai_recommendations.get("Recommendations_List", [])
total_planned_calories = ai_recommendations.get("Total_Planned_Estimated_Calories", 0)
total_recommended_calories = ai_recommendations.get("Total_Estimated_Calories", 0)

send_log(f"[MAIN] AI Recommendations: {json.dumps(recommendations, indent=2)}")
send_log(f"[MAIN] Total Planned Estimated Calories: {total_planned_calories}")
send_log(f"[MAIN] Total Recommended Calories: {total_recommended_calories}")
#endregion


#logic for database 
extra_calories, calories_message = calories_surplus(database, total_planned_calories, days_until_next_visit)
risk_of_expiry_messages = []
underbuy_messages = []

for item in recommendations:
    item_name = item["Item_Name"]
    est_consume_rate = item["Estimated_Consumption_Rate"]
    planned_amt = item["Planned_Quantity"]
    expiry_date = item["Estimated_Expiry_Date"]
    unit = item["Unit"]
    fridge_amt = get_all_fridge_quantity(database, item_name)
    total_amt = fridge_amt + planned_amt #total amount of item in grocery list AND currently in fridge

    expire_before_consume, expiry_message = risk_of_expiry(item, total_amt) 
    if expiry_message is not None:
        risk_of_expiry_messages.append(expiry_message) 

    next_purchase_date = str(date.today() + timedelta(days=days_until_next_visit))
    if should_evaluate_underbuy(extra_calories, expire_before_consume):
        need_to_buy_more, underbuy_message = under_buy(item, next_purchase_date, total_amt) 
        
        if underbuy_message is not None:
                underbuy_messages.append(underbuy_message) 


    confidence_score = calculate_confidence_score(item_name, database, item["Recommended_Quantity"], fridge_amt, days_until_next_visit, remarks)
    item["Confidence_Score"] = confidence_score

output_recommendations(calories_message, risk_of_expiry_messages, underbuy_messages, recommendations)


final_checkout = shopping_cart_conclusion(recommendations, remarks)
database = add_to_fridge(database, final_checkout)
save_database(database, 'database')  # Save the database to the specified folder
