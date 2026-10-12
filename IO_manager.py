from datetime import date, timedelta, datetime
import os

valid_units = ["kg", "g", "l", "ml", "pcs"]
valid_genders = ["male", "female"]
 
# Ask for one item's name, quantity and unit, validating bad input.
# If the item already exists in existing_items, its unit is reused.
def enter_item(existing_items=None):
    if existing_items is None:
        existing_items = []

    item_name = enter_text("Item name: ")

    # Check if this item was entered before, and lock its unit
    locked_unit = ""
    for existing in existing_items:
        if existing["Item_Name"].lower() == item_name.lower():
            locked_unit = existing["Unit"]
            print(f"{item_name} was entered before in {locked_unit}, so please enter the quantity in {locked_unit}.")
            break

    # Ask for quantity and unit together
    while True:
        if locked_unit != "":
            text = input(f"Quantity in {locked_unit} (e.g. 3): ").strip().lower()
        else:
            text = input(f"Quantity and unit (e.g. 6kg, 500 g, 3 pcs) - units: {', '.join(valid_units)}: ").strip().lower()

        # Split where the number ends and the unit begins
        split_at = 0
        while split_at < len(text) and (text[split_at].isdecimal() or text[split_at] == "."):
            split_at += 1
        number_part = text[:split_at]
        unit = text[split_at:].strip()

        if not number_part.replace(".", "", 1).isdecimal():
            print("Please start with a valid number, e.g. 6kg.")
        elif float(number_part) <= 0:
            print("Quantity must be more than 0.")
        elif unit == "" and locked_unit == "":
            print(f"Please include a unit ({', '.join(valid_units)}), e.g. 6kg.")
        elif unit != "" and unit not in valid_units:
            print(f"'{unit}' is not a valid unit. Please use one of: {', '.join(valid_units)}.")
        elif locked_unit != "" and unit != "" and unit != locked_unit:
            print(f"{item_name} must be entered in {locked_unit}.")
        else:
            quantity = float(number_part)
            if unit == "":
                unit = locked_unit
            break

    return {"Item_Name": item_name, "Quantity": quantity, "Unit": unit}
 
 
# Double quote checks, reasks user to prevent JSON errors
def enter_text(question, allow_blank=False):
    while True:
        text = input(question).strip()
        if '"' in text or "\\" in text:
            print('Please don\'t use double quotes (") or backslashes (\\) in your answer.')
        elif text == "" and not allow_blank:
            print("This can't be empty.")
        else:
            return text


# Ask for a quantity until the user enters a number more than 0.
def enter_quantity(question):
    while True:
        text = input(question).strip()
        if not text.replace(".", "", 1).isdecimal():
            print("Please enter a valid number.")
        elif float(text) <= 0:
            print("Quantity must be more than 0.")
        else:
            return float(text)


# Ask whether the user wants to add another item.
def ask_add_another():
    while True:
        more = input("Do you want to add another item? (yes/no): ").strip().lower()
        if more in ["yes", "y", "no", "n"]:
            return more in ["yes", "y"]
        print("Please answer yes or no.")
 
 
# Ask for a date in YYYY-MM-DD format and check it is a real date.
def enter_date(question):
    while True:
        text = input(question).strip()
        parts = text.split("-")
        valid = (len(parts) == 3 and len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2
                 and parts[0].isdecimal() and parts[1].isdecimal() and parts[2].isdecimal())
        if valid:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            is_leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
            days_in_month = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            valid = 1 <= month <= 12 and 1 <= day <= days_in_month[month - 1]
        if not valid:
            print("Please enter a real date in the format YYYY-MM-DD, e.g. 2026-10-20.")
        elif date(year, month, day) < date.today() - timedelta(days=365):
            print("That date is more than a year ago. Please enter a more recent date.")
        elif date(year, month, day) > date.today() + timedelta(days=3 * 365):
            print("That date is more than 3 years ahead. Please check the year and try again.")
        else:
            if date(year, month, day) < date.today():
                print("That date has already passed! This item is marked as expired.")
            return text
 
 
# Collect a new user's profile and their family members' details.
# Returns a list in the database's household_info format (the user is Person_ID 1).
def create_profile():
    name = enter_text("Please enter your name: ")
 
    while True:
        age = input("Please enter your age: ").strip()
        if age.isdecimal() and 10 <= int(age) <= 120:
            age = int(age)
            break
        print("Please enter a valid age (whole number between 10 and 120).")
 
    while True:
        gender = input(f"Please enter your gender ({', '.join(valid_genders)}): ").strip().lower()
        if gender in valid_genders:
            break
        print("Please enter male or female.")
 
    dietary_restrictions = enter_text("Please enter your dietary restrictions (leave blank if none): ", True)
    if dietary_restrictions == "":
        dietary_restrictions = "None"
 
    while True:
        family = input("Please enter your family size including yourself: ").strip()
        if family.isdecimal() and 1 <= int(family) <= 20:
            family = int(family)
            break
        print("Please enter a whole number between 1 and 20.")
 
    user_check = {
        "name": name,
        "age": age,
        "gender": gender,
        "dietary_restrictions": dietary_restrictions,
        "family_size": family,
        "family_members": {}
    }
 
    for i in range(family - 1):
        member_name = enter_text(f"Please enter the name of family member {i + 1}: ")
 
        while True:
            member_age = input(f"Please enter the age of {member_name}: ").strip()
            if member_age.isdecimal() and int(member_age) <= 120:
                member_age = int(member_age)
                break
            print("Please enter a valid age (whole number between 0 and 120).")
 
        while True:
            member_gender = input(f"Please enter the gender of {member_name} ({', '.join(valid_genders)}): ").strip().lower()
            if member_gender in valid_genders:
                break
            print("Please enter male or female.")
 
        member_diet = enter_text(f"Please enter the dietary restrictions of {member_name} (leave blank if none): ", True)
        if member_diet == "":
            member_diet = "None"
 
        user_check["family_members"][i + 1] = {
            "name": member_name,
            "age": member_age,
            "gender": member_gender,
            "dietary_restrictions": member_diet
        }
 
    print(f"User {name} registered successfully!")
 
    # Convert into the database's household_info format
    household_info = [{
        "Person_ID": 1,
        "Name": user_check["name"],
        "Age": user_check["age"],
        "Gender": user_check["gender"].capitalize(),
        "Dietary_Restriction": user_check["dietary_restrictions"]
    }]
 
    for number in user_check["family_members"]:
        member = user_check["family_members"][number]
        household_info.append({
            "Person_ID": number + 1,
            "Name": member["name"],
            "Age": member["age"],
            "Gender": member["gender"].capitalize(),
            "Dietary_Restriction": member["dietary_restrictions"]
        })
 
    return household_info
 
 
# For new users: Collect the food items they already have at home, with expiry dates.
# Returns a list in the database's fridge format
def enter_home_items():
    while True:
        has_items = input("\nDo you have any food items at home you want to add? (yes/no): ").strip().lower()
        if has_items in ["yes", "y", "no", "n"]:
            break
        print("Please answer yes or no.")
 
    remaining_items = []
    if has_items in ["no", "n"]:
        return remaining_items
 
    print("\nEnter the items you currently have at home.")
    while True:
        item = enter_item(remaining_items)
        expiry_date = enter_date("Expiry date (YYYY-MM-DD): ")
        item_remarks = enter_text("Any remarks about this item? e.g. opened, for a party (leave blank if none): ", True)
        if item_remarks == "":
            item_remarks = "None"

        item["Purchase_Date"] = ""
        item["Expiry_Date"] = expiry_date
        item["Remarks"] = item_remarks

        # If the same item with the same expiry date was already entered, add to it
        found = False
        for existing in remaining_items:
            if (existing["Item_Name"].lower() == item["Item_Name"].lower() and existing["Unit"] == item["Unit"]
                    and existing["Expiry_Date"] == item["Expiry_Date"]):
                existing["Quantity"] += item["Quantity"]
                # Keep both remarks if they are different
                if item["Remarks"] != "None" and item["Remarks"] != existing["Remarks"]:
                    if existing["Remarks"] == "None":
                        existing["Remarks"] = item["Remarks"]
                    else:
                        existing["Remarks"] = existing["Remarks"] + ", " + item["Remarks"]
                found = True
                print(f"{existing['Item_Name']} is already in your home items. Total is now {format_item(existing)}.")
                break

        if not found:
            remaining_items.append(item)
            print(f"Added {format_item(item)} to your home items.")
        if not ask_add_another():
            break
 
    return remaining_items
 
 
# For returning users: Ask how much of each item they consumed since last visit.
# Batches of the same item are combined into one question.
# Days since last use and remarks are asked once and applied to every item.
# Returns a list in the database's format to remove
def update_consumption(previous_inventory):
    consumed_items = []
    if not previous_inventory:
        return consumed_items
 
    # Add up the total of each item across all its batches
    totals = {}
    for item in previous_inventory:
        key = (item["Item_Name"].lower(), item["Unit"])
        if key in totals:
            totals[key]["Quantity"] += item["Quantity"]
        else:
            totals[key] = {"Item_Name": item["Item_Name"], "Quantity": item["Quantity"], "Unit": item["Unit"]}
 
    print("\nUpdate Consumption.")
 
    # Asked once for the whole consumption list
    while True:
        text = input("How many days has it been since you last used the app? ").strip()
        if text.isdecimal() and 1 <= int(text) <= 365:
            date_range = int(text)
            break
        print("Please enter a whole number between 1 and 365.")
 
    for key in totals:
        name = totals[key]["Item_Name"]
        total = round(totals[key]["Quantity"], 2)
        unit = totals[key]["Unit"]
        while True:
            text = input(f"How much {name} did you consume? (you have {total} {unit}): ").strip()
            if not text.replace(".", "", 1).isdecimal():
                print("Please enter a valid number.")
            elif float(text) > total:
                print(f"That's more than you have ({total} {unit}). Please try again.")
            else:
                consumed = float(text)
                break
 
        consumed_items.append({
            "Date_Range": date_range,
            "Item_Name": name,
            "Quantity": consumed,
            "Unit": unit
        })
 
    # Asked once, then added to every item
    remarks = enter_text("Any remarks about your consumption since last time? (leave blank if none): ", True)
    if remarks == "":
        remarks = "None"
    for record in consumed_items:
        record["Remarks"] = remarks
 
    return consumed_items
 
 
# Collect the groceries the user plans to buy, until they say they are done.
# Returns a list of {"Item_Name", "Quantity", "Unit"}.
def enter_grocery_list(database):
    fridge_items = database["fridge"]
    consumed_items = database["consumption_history"]
    if fridge_items is None:
        fridge_items = []
    grocery_list = []
    print("\nEnter the groceries you are planning to buy.")
 
    while True:
        item = enter_item(grocery_list + fridge_items + consumed_items)
 
        # If the same item with the same unit was already entered, add to it
        found = False
        for existing in grocery_list:
            if existing["Item_Name"].lower() == item["Item_Name"].lower() and existing["Unit"] == item["Unit"]:
                existing["Quantity"] += item["Quantity"]
                found = True
                print(f"{existing['Item_Name']} is already in your list. Total is now {format_item(existing)}.")
                break
 
        if not found:
            grocery_list.append(item)
            print(f"Added {format_item(item)}.")
 
        if not ask_add_another():
            break
 
    show_items("Your grocery list", grocery_list)
    send_log(f"[IO MANAGER] grocery_list = {grocery_list}") #log grocery list for verification
    return grocery_list
 
 
# Ask for optional remarks about this week (e.g. events).
def ask_remarks():
    remarks = enter_text("\nAny remarks for this week? e.g. hosting a party, going on holiday (leave blank if none): ", True)
    if remarks == "":
        remarks = "None"
    return remarks
 
 
# Ask how many days until the user's next planned shop.
def ask_days_until_next():
    while True:
        text = input("\nIn how many days do you plan to shop next? (e.g. 7): ").strip()
        if text.isdecimal() and 1 <= int(text) <= 365:
            return int(text)
        print("Please enter a whole number between 1 and 365.")


# Show the returning user's menu and return their choice ("1" or "2").
def ask_menu_choice():
    while True:
        print("\nWhat would you like to do?")
        print("  1. Update consumption and plan groceries")
        print("  2. Edit expiry dates or delete items from your fridge")
        choice = input("Enter 1 or 2: ").strip()
        if choice in ["1", "2"]:
            return choice
        print("Please enter 1 or 2.")


# Let the user edit expiry dates or delete items from their fridge until they are done.
# Returns the updated fridge list.
def edit_fridge(fridge):
    while True:
        show_items("Items in your fridge", fridge)
        if not fridge:
            return fridge

        print("\nWhat would you like to do with your fridge?")
        print("  1. Edit an expiry date")
        print("  2. Delete an item")
        print("  3. Done")
        action = input("Enter 1, 2 or 3: ").strip()
        if action == "3":
            return fridge
        elif action not in ["1", "2"]:
            print("Please enter 1, 2 or 3.")
            continue

        while True:
            text = input(f"Enter the item number (1-{len(fridge)}): ").strip()
            if text.isdecimal() and 1 <= int(text) <= len(fridge):
                number = int(text) - 1
                break
            print(f"Please enter a number between 1 and {len(fridge)}.")

        if action == "1":
            fridge[number]["Expiry_Date"] = enter_date(f"New expiry date for {fridge[number]['Item_Name']} (YYYY-MM-DD): ")
            print(f"Updated: {format_item(fridge[number])}")
        else:
            removed = fridge.pop(number)
            print(f"{format_item(removed)} has been removed from your fridge.")


#displays item, current quantity and recommened quantity for conclusion IO 
def display_cart(item_list):
    #assuming input is always the recommendations list
    if not item_list:
        print("  (your shopping cart is empty)")
        return
    name_width = max(len("Item name"), max(len(item["Item_Name"]) for item in item_list)) + 2 #align table according to how big item_name is

    # Print header
    print(f"\nGrocery Cart")
    print(
        f"{'No.':<4}| "
        f"{'Item name':<{name_width}}| "
        f"{'Current amt':<12}| "
        f"{'Recommended amt':<16}| "
        f"{'HS*':<6}| "
    )

    # Print rows
    for i in range(0,len(item_list)):
        cur_amt_formatted = f"{item_list[i]['Planned_Quantity']} {item_list[i]['Unit']}"
        recommened_amt_formatted = f"{item_list[i]['Recommended_Quantity']} {item_list[i]['Unit']}"
        historical_score_formatted = f"{round(item_list[i]['Historical_Score'], 1)}%"
        print(
            f"{i+1:<4}| "
            f"{item_list[i]['Item_Name']:<{name_width}}| "
            f"{cur_amt_formatted:<12}| "
            f"{recommened_amt_formatted:<16}| "
            f"{historical_score_formatted:<6}| "
        )
    print(f"* HS --> Historical score: calculation of historical data quantity and consistency")


#displays recommendations made by business logic
def output_recommendations(calories_message, risk_of_expiry_messages, underbuy_messages, recommendations):
    print(f"\n--------------------------------recommendations---------------------------------")
    print(f"\n{calories_message}")
    print(f"\n--------------------------------------------------------------------------------")
    if len(risk_of_expiry_messages) != 0:
        print(f"\nBased on estimated consumption rate and estimated expiry date, you will not able" 
              f"\n to finish the following items before your next grocery trip:")
        for i in range(len(risk_of_expiry_messages)):
            print(f"  {i+1}. {risk_of_expiry_messages[i]}") 
        print(f"\n--------------------------------------------------------------------------------")
    if len(underbuy_messages) != 0:
        print(f"You are forcasted to finish the following items before your next indicated grocery trip:")
        for i in range(len(underbuy_messages)):
            print(f"  {i+1}. {underbuy_messages[i]}") 
        print(f"\n--------------------------------------------------------------------------------")


#converts recommendation list into format that can be saved in DB
def convert_cart_to_db_list(recommendations_list, remarks):
    final_list=[]
    for i in range(len(recommendations_list)):
        db_item = {}
        db_item["Item_Name"] = recommendations_list[i]["Item_Name"]
        db_item["Quantity"] = recommendations_list[i]["Planned_Quantity"]
        db_item["Unit"] = recommendations_list[i]["Unit"]
        db_item["Purchase_Date"] = date.today().isoformat()
        db_item["Expiry_Date"] = recommendations_list[i]["Estimated_Expiry_Date"]
        db_item["Remarks"] = remarks
        final_list.append(db_item)
    return final_list


#handles IO for after AI and logic processes
def shopping_cart_conclusion(item_list, remarks):
    display_cart(item_list)
    while True:
        decision = input("\nWould you like to change the quantity of items in your shopping cart? (yes/no): ").strip().lower()
        if decision in ["no", "n"]:
            print("\nYour shopping cart has been concluded.")
            return convert_cart_to_db_list(item_list, remarks)
        
        elif decision in ["yes", "y"]:
            while True:
                item_index = input("\nEnter item to edit/delete(1,2...) or enter 'exit' to save: ").strip().lower()
                if item_index == "exit":
                    return convert_cart_to_db_list(item_list, remarks)
                elif item_index.isdecimal():
                    if int(item_index) in range(1, len(item_list) + 1): # check if option is in the list
                        item_index = int(item_index) - 1
                        while True:
                            print(f"Selected {item_list[item_index]['Item_Name']}, Current Quantity: {item_list[item_index]['Planned_Quantity']}")
                            edited_quantity = input("Enter new amount (enter 0 to delete item):").strip()
                            if edited_quantity.replace(".", "", 1).isdecimal():
                                if float(edited_quantity) == 0:
                                    del item_list[item_index]
                                else:
                                    item_list[item_index]["Planned_Quantity"] = float(edited_quantity)
                                break
                            else:
                                print("Invalid input. Enter a positive number")
                        display_cart(item_list)
                    else:
                        print("Invalid input. Enter item to edit/delete(1,2...) or enter 'exit' to save")
                else:
                    print("Invalid input. Enter item to edit/delete(1,2...) or enter 'exit' to save")
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")



# Formatting 

def format_item(item):
    text = f"{item['Quantity']:g} {item['Unit']} of {item['Item_Name']}"
    details = []
    if item.get("Expiry_Date", "") != "":
        details.append(f"expires {item['Expiry_Date']}")
    if item.get("Remarks", "None") != "None":
        details.append(item["Remarks"])
    if details:
        text += f" ({', '.join(details)})"
    return text
 
 
# Print a numbered list of items under a title.
def show_items(title, items):
    print(f"\n{title}:")
    if not items:
        print("  (none)")
        return
    for i in range(len(items)):
        print(f"  {i + 1}. {format_item(items[i])}")
 
 
# Print a summary of everyone in the household.
def show_profile(household_info):
    print("\nHousehold summary:")
    for person in household_info:
        print(f"  {person['Person_ID']}. {person['Name']}, {person['Age']}, {person['Gender']}, "
              f"diet: {person['Dietary_Restriction']}")
 
 
# Print a summary of what was recorded as consumed.
def show_consumption(consumed_items):
    print("\nConsumption recorded:")
    if not consumed_items:
        print("  (none)")
        return
    print(f"  Over the last {consumed_items[0]['Date_Range']} day(s), remarks: {consumed_items[0]['Remarks']}")
    for i in range(len(consumed_items)):
        record = consumed_items[i]
        print(f"  {i + 1}. {record['Quantity']:g}{record['Unit']} of {record['Item_Name']}")
 
 
# Print the start-up welcome message.
def show_welcome():
    print("Welcome to the Waste Management System!")
 
 
# Print the welcome-back message for a returning user (Person_ID 1 is the user).
def show_welcome_back(household_info):
    print(f"Welcome back, {household_info[0]['Name']}!")


def send_message(message):
    print(f"{message}")

current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
def send_log(message):
    filename=f"{current_datetime}.log"
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write(message)
    else:
        with open(filename, 'a') as f:
            f.write(f"\n{message}")

 
# =====================================================================
# Testing
# =====================================================================
 
if __name__ == "__main__":
    household_info = []      # change to [{"Person_ID": 1, "Name": "Test", "Age": 20, "Gender": "Male", "Dietary_Restriction": "None"}] to test a returning user
    previous_inventory = []  # e.g. [{"Item_Name": "Milk", "Quantity": 2, "Unit": "l", "Purchase_Date": "2026-09-21", "Expiry_Date": "2026-10-05", "Remarks": "None"}]
    remaining_items = []
    consumed_items = []
 
    show_welcome()
 
    if household_info == []:
        household_info = create_profile()
        show_profile(household_info)
        remaining_items = enter_home_items()
        show_items("Items at home", remaining_items)
    else:
        show_welcome_back(household_info)
        while True:
            choice = ask_menu_choice()
            if choice == "1":
                consumed_items = update_consumption(previous_inventory)
                show_consumption(consumed_items)
                break
            else:
                previous_inventory = edit_fridge(previous_inventory)
 
    grocery_list = enter_grocery_list(previous_inventory + remaining_items)
 
    remarks = ask_remarks()
    days_until_next = ask_days_until_next()
    recommendations = []
    for item in grocery_list:
        recommendations.append({"Item_Name": item["Item_Name"], "Planned_Quantity": item["Quantity"],
                                "Recommended_Quantity": item["Quantity"], "Unit": item["Unit"],
                                "Estimated_Expiry_Date": ""})
    final_checkout = shopping_cart_conclusion(recommendations, remarks)
 
    print("\n--- Test results ---")
    print("household_info =", household_info)
    print("previous_inventory =", previous_inventory)
    print("remaining_items =", remaining_items)
    print("consumed_items =", consumed_items)
    print("grocery_list =", grocery_list)
    print("remarks =", remarks)
    print("days_until_next =", days_until_next)
    print("final_checkout =", final_checkout)