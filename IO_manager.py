valid_units = ["kg", "g", "l", "ml", "pcs"]
valid_genders = ["male", "female"]
 
# Ask for one item's name, quantity and unit, validating bad input.
def enter_item():
    while True:
        item_name = input("Item name: ").strip()
        if item_name != "":
            break
        print("Item name can't be empty.")
 
    while True:
        text = input("Quantity: ").strip()
        if not text.replace(".", "", 1).isdigit():
            print("Please enter a valid number.")
        elif float(text) <= 0:
            print("Quantity must be more than 0.")
        else:
            quantity = float(text)
            break
 
    while True:
        unit = input(f"Unit ({', '.join(valid_units)}): ").strip().lower()
        if unit in valid_units:
            break
        print("Please enter a valid unit.")
 
    return {"Item_Name": item_name, "Quantity": quantity, "Unit": unit}
 
 
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
                 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit())
        if valid:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            is_leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
            days_in_month = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            valid = 1 <= month <= 12 and 1 <= day <= days_in_month[month - 1]
        if valid:
            return text
        print("Please enter a real date in the format YYYY-MM-DD, e.g. 2026-10-20.")
 
 
# Collect a new user's profile and their family members' details.
# Returns a list in the database's household_info format (the user is Person_ID 1).
def create_profile():
    while True:
        name = input("Please enter your name: ").strip()
        if name != "":
            break
        print("Name can't be empty.")
 
    while True:
        age = input("Please enter your age: ").strip()
        if age.isdigit() and int(age) <= 120:
            age = int(age)
            break
        print("Please enter a valid age (whole number between 0 and 120).")
 
    while True:
        gender = input(f"Please enter your gender ({', '.join(valid_genders)}): ").strip().lower()
        if gender in valid_genders:
            break
        print("Please enter male or female.")
 
    dietary_restrictions = input("Please enter your dietary restrictions (leave blank if none): ").strip()
    if dietary_restrictions == "":
        dietary_restrictions = "None"
 
    while True:
        family = input("Please enter your family size including yourself: ").strip()
        if family.isdigit() and 1 <= int(family) <= 20:
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
        while True:
            member_name = input(f"Please enter the name of family member {i + 1}: ").strip()
            if member_name != "":
                break
            print("Name can't be empty.")
 
        while True:
            member_age = input(f"Please enter the age of {member_name}: ").strip()
            if member_age.isdigit() and int(member_age) <= 120:
                member_age = int(member_age)
                break
            print("Please enter a valid age (whole number between 0 and 120).")
 
        while True:
            member_gender = input(f"Please enter the gender of {member_name} ({', '.join(valid_genders)}): ").strip().lower()
            if member_gender in valid_genders:
                break
            print("Please enter male or female.")
 
        member_diet = input(f"Please enter the dietary restrictions of {member_name} (leave blank if none): ").strip()
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
        item = enter_item()
        expiry_date = enter_date("Expiry date (YYYY-MM-DD): ")
        item_remarks = input("Any remarks about this item? e.g. opened, for a party (leave blank if none): ").strip()
        if item_remarks == "":
            item_remarks = "None"
 
        item["Purchase_Date"] = ""
        item["Expiry_Date"] = expiry_date
        item["Remarks"] = item_remarks
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
        if text.isdigit() and 1 <= int(text) <= 365:
            date_range = int(text)
            break
        print("Please enter a whole number between 1 and 365.")
 
    for key in totals:
        name = totals[key]["Item_Name"]
        total = round(totals[key]["Quantity"], 2)
        unit = totals[key]["Unit"]
        while True:
            text = input(f"How much {name} did you consume? (you have {total} {unit}): ").strip()
            if not text.replace(".", "", 1).isdigit():
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
    remarks = input("Any remarks about your consumption since last time? (leave blank if none): ").strip()
    if remarks == "":
        remarks = "None"
    for record in consumed_items:
        record["Remarks"] = remarks
 
    return consumed_items
 
 
# Collect the groceries the user plans to buy, until they say they are done.
# Returns a list of {"Item_Name", "Quantity", "Unit"}.
def enter_grocery_list():
    grocery_list = []
    print("\nEnter the groceries you are planning to buy.")
 
    while True:
        item = enter_item()
 
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
    print("grocery_list =", grocery_list)  # Print the grocery list for verification
    return grocery_list
 
 
# Ask for optional remarks about this week (e.g. events).
def ask_remarks():
    return input("\nAny remarks for this week? e.g. hosting a party, going on holiday (leave blank if none): ").strip()
 
 
# Ask how many days until the user's next planned shop.
def ask_days_until_next():
    while True:
        text = input("\nIn how many days do you plan to shop next? (e.g. 7): ").strip()
        if text.isdigit() and 1 <= int(text) <= 365:
            return int(text)
        print("Please enter a whole number between 1 and 365.")


def shopping_cart_conclusion(grocery_list):
    while True:
        decision = input("\nDo you want to conclude your shopping cart? (yes/no): ").strip().lower()
        if decision == "yes":
            print("\nYour shopping cart has been concluded.")
            return grocery_list
        elif decision == "no":
            print("\nProceed with editing your shopping cart.")
            for i in range(len(grocery_list)):
                print(f"  {i + 1}. {format_item(grocery_list[i])}")
                action = input(f"Do you want to remove this item from your shopping cart? (yes/no): ").strip().lower()
                if action == "yes":
                    grocery_list.pop(i)
                    print(f"{format_item(grocery_list[i])} has been removed from your shopping cart.")
                    continue
                elif action == "no":
                    grocery_list[i]["Quantity"] = float(input(f"Enter the new quantity for {format_item(grocery_list[i])}: "))
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
            addtion = input("\nDo you want to add any new items to your shopping cart? (yes/no): ").strip().lower()
            if addtion == "yes":
                while True:
                    item = enter_item()
                    grocery_list.append(item)
                    print(f"Added {format_item(item)} to your shopping cart.")
                    if not ask_add_another():
                        break
            elif addtion == "no":  
                print("\nYour shopping cart has been concluded.")
                return grocery_list
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")
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
        print(f"  {i + 1}. {record['Quantity']:g} {record['Unit']} of {record['Item_Name']}")
 
 
# Print the start-up welcome message.
def show_welcome():
    print("Welcome to the Waste Management System!")
 
 
# Print the welcome-back message for a returning user (Person_ID 1 is the user).
def show_welcome_back(household_info):
    print(f"Welcome back, {household_info[0]['Name']}!")


def send_message(message):
    print(f"{message}")

def send_log(message):
    print(f"[LOG] {message}")

 
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
        consumed_items = update_consumption(previous_inventory)
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
 