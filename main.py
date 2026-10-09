from datetime import date, timedelta
import json
from DB_manager import database_exists, load_database, save_database, KCAL_TABLE
from IO_manager import show_welcome, create_profile, show_profile, enter_home_items, show_items, show_welcome_back, update_consumption, show_consumption, enter_grocery_list, ask_remarks, ask_days_until_next
from AI_manager import get_ai_recommendations
database_exists()  # Ensure the database folder and file exist
database = load_database('sample_database')  # Load the database into memory
#print(database)  # Print the loaded database for verification

household_info = database.get('household_info', [])
consumption_history = database.get('consumption_history', [])
fridge = database.get('fridge', [])


remaining_items = []
consumed_items = []
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
#endregion










#save_database(database, 'database')  # Save the database to the specified folder