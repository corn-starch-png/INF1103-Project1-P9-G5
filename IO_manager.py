user_check = {}
remaining_items = []
valid_units = ["kg", "g", "l", "ml", "pcs"]

print("Welcome to the Waste Management System!")

if user_check == {}:
    valid_genders = ["male", "female"]
 
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
        print("Please enter male or female")
 
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
            print("Please enter male or female")
 
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

    while True:
        has_items = input("\nDo you have any food items at home you want to add? (yes/no): ").strip().lower()
        if has_items in ["yes", "y", "no", "n"]:
            break
        print("Please answer yes or no.")
 
    if has_items in ["yes", "y"]:
        print("\nEnter the items you currently have at home.")
 
        while True:
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
 
            remaining_items.append({
                "name": item_name,
                "quantity": quantity,
                "unit": unit,
                "used": 0.0
            })
            print(f"Added {quantity} {unit} of {item_name} to your home items.")
 
            while True:
                more = input("Do you want to add another item? (yes/no): ").strip().lower()
                if more in ["yes", "y", "no", "n"]:
                    break
                print("Please answer yes or no.")
            if more in ["no", "n"]:
                break
 
else:
    print(f"Welcome back, {user_check['name']}!")
    previous_inventory = []  
 
    if previous_inventory: 
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




grocery_list = []
 
print("\nEnter the groceries you are planning to buy.")
 
while True:

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


    grocery_list.append({
        "name": item_name,
        "quantity": quantity,
        "unit": unit,
        #"purchase_date": purchase_date,
        #"expiry_date": expiry_date
    })
    print(f"Added {quantity} {unit} of {item_name}.")
 
    while True:
        more = input("Do you want to add another item? (yes/no): ").strip().lower()
        if more in ["yes", "y", "no", "n"]:
            break
        print("Please answer yes or no.")
    if more in ["no", "n"]:
        break
    


print("\nYour grocery list:")
for i in range(len(grocery_list)):
    item = grocery_list[i]
    print(f"{i + 1}. {item['name']} - {item['quantity']} {item['unit']}")

remarks = input("\nAny remarks for this week? e.g. hosting a party, going on holiday (leave blank if none): ").strip()

while True:
    text = input("\nIn how many days do you plan to shop next? (e.g. 7): ").strip()
    if text.isdigit() and int(text) >= 1:
        days_until_next = int(text)
        break
    print("Please enter a whole number of at least 1.")