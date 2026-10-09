#-------START OF DEPENDENCY LINE----------#
from datetime import date, timedelta
import json
from DB_manager import database_exists, load_database, save_database, KCAL_TABLE
from IO_manager import show_welcome, create_profile, show_profile, enter_home_items, show_items, show_welcome_back, update_consumption, show_consumption, enter_grocery_list, ask_remarks, ask_days_until_next
from AI_manager import get_ai_recommendations
from Logic_manager import under_buy, calories_surplus, risk_of_expiry, calculate_confidence_score
database_exists()  # Ensure the database folder and file exist
database = load_database('sample_database')  # Load the database into memory
#print(database)  # Print the loaded database for verification

household_info = database.get('household_info', [])
consumption_history = database.get('consumption_history', [])
fridge = database.get('fridge', [])


remaining_items = []
consumed_items = []

#-------END OF DEPENDENCY LINE----------#
show_welcome()
if household_info == []:
    household_info = create_profile()
    show_profile(household_info)
    remaining_items = enter_home_items()
    show_items("Items at home", remaining_items)
    #TODO save remaining_items to fridge and household_info to database
else:
    show_welcome_back(household_info)
    consumed_items = update_consumption(consumption_history)
    show_consumption(consumed_items)

grocery_list = enter_grocery_list()

remarks = ask_remarks()
days_until_next = ask_days_until_next()

print("\n--- Test results ---")
print("household_info =", household_info)
print("remaining_items =", remaining_items)
print("consumed_items =", consumed_items)
print("grocery_list =", grocery_list)
print("remarks =", remarks)
print("days_until_next =", days_until_next)

#region AI Recommendations
ai_recommendations, error = get_ai_recommendations(household_info, consumption_history, fridge, grocery_list,remarks,days_until_next)
if error:
    print(f"Error: {error}")
    #return
recommendations = ai_recommendations.get("recommendations", [])
total_estimated_calories = ai_recommendations.get("total_estimated_calories", 0)
print(f"AI Recommendations: {json.dumps(recommendations, indent=2)}")
print(f"Total Estimated Calories: {total_estimated_calories}")
#endregion """


#logic for database 

calorie_extra = calories_surplus(database, total_estimated_calories)
for item in recommendations:
    est_consum_rate = item["consumption_rate"]
    planned_amt = item["planned_quantity"]
    item_name = item["item"]
    expiry_date = item["estimated_expiration_date"]
    unit = item["unit"]
    next_purchase_date = "2026-10-10"
    
    roe = risk_of_expiry(est_consum_rate, planned_amt, expiry_date, item_name, unit)
    if roe is False and calorie_extra is False:
        under_string = under_buy(item_name=item_name, planned_quantity= planned_amt,
                      item_expiry_date= expiry_date, 
                      estimated_consumption_rate= est_consum_rate,
                      next_purchase_date=next_purchase_date)
        print(f"Underbuy {under_string}")


    confidence_score = calculate_confidence_score(item_name=item_name)
    print(item_name, confidence_score)




#save_database(database, 'database')  # Save the database to the specified folder
