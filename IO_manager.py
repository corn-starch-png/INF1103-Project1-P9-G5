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
 
    return {"name": item_name, "quantity": quantity, "unit": unit}
 
 
# Ask whether the user wants to add another item.
def ask_add_another():
    while True:
        more = input("Do you want to add another item? (yes/no): ").strip().lower()
        if more in ["yes", "y", "no", "n"]:
            return more in ["yes", "y"]
        print("Please answer yes or no.")
 
# Collect a new user's profile and their family members' details.
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
        dietary_restrictions = "none"
 
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
            member_diet = "none"
 
        user_check["family_members"][i + 1] = {
            "name": member_name,
            "age": member_age,
            "gender": member_gender,
            "dietary_restrictions": member_diet
        }
 
    print(f"User {name} registered successfully!")
    return user_check
 
 
# For new users: Check the food items they already have at home.
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
        item["used"] = 0.0
        remaining_items.append(item)
        print(f"Added {item['quantity']} {item['unit']} of {item['name']} to your home items.")
        if not ask_add_another():
            break
 
    return remaining_items
 
 
# For returning users: Ask how much of each previous item is left.
def update_consumption(previous_inventory):
    remaining_items = []
    if not previous_inventory:
        return remaining_items
 
    print("\nUpdate Consumption.")
    for item in previous_inventory:
        while True:
            text = input(f"How much {item['name']} is left? (you had {item['quantity']} {item['unit']}): ").strip()
            if not text.replace(".", "", 1).isdigit():
                print("Please enter a valid number.")
            elif float(text) > item["quantity"]:
                print(f"That's more than you had ({item['quantity']}). Please try again.")
            else:
                left = float(text)
                break
 
        remaining_items.append({
            "name": item["name"],
            "quantity": left,
            "unit": item["unit"],
            "used": item["quantity"] - left
        })
 
    return remaining_items
 
 
# Collect the groceries the user plans to buy, until they say they are done.
def enter_grocery_list():
    grocery_list = []
    print("\nEnter the groceries you are planning to buy.")
 
    while True:
        item = enter_item()
        grocery_list.append(item)
        print(f"Added {item['quantity']} {item['unit']} of {item['name']}.")
        if not ask_add_another():
            break
 
    print("\nYour grocery list:")
    for i in range(len(grocery_list)):
        item = grocery_list[i]
        print(f"{i + 1}. {item['name']} - {item['quantity']} {item['unit']}")
 
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
 

# Print the start-up welcome message.
def show_welcome():
    print("Welcome to the Waste Management System!")
 
 
# Print the welcome-back message for a returning user.
def show_welcome_back(user_check):
    print(f"Welcome back, {user_check['name']}!")
 
 
# =====================================================================
# Testing
# =====================================================================
 
if __name__ == "__main__":
    user_check = {}          # change to {"name": "Test"} to test a returning user
    previous_inventory = []  # e.g. [{"name": "rice", "quantity": 5.0, "unit": "kg"}]
 
    show_welcome()
 
    if user_check == {}:
        user_check = create_profile()
        remaining_items = enter_home_items()
    else:
        show_welcome_back(user_check)
        remaining_items = update_consumption(previous_inventory)
 
    grocery_list = enter_grocery_list()
 
    remarks = ask_remarks()
    days_until_next = ask_days_until_next()
 
 
    print("\n--- Test results ---")
    print("user_check =", user_check)
    print("remaining_items =", remaining_items)
    print("grocery_list =", grocery_list)
    print("remarks =", remarks)
    print("days_until_next =", days_until_next)
 