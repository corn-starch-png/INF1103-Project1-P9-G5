from datetime import date
from decimal import Decimal
from DB_manager import (MAX_ITEM_NAME_LENGTH, MAX_PERSON_NAME_LENGTH, MAX_DIETARY_LENGTH,
                        MAX_QUANTITY, MAX_REMARKS_LENGTH, normalize_quantity, send_log, shift_calendar_years)
from ioclasses import TextPrompt, QuantityPrompt, DatePrompt, IntRangePrompt, ChoicePrompt
from core.Person import Person
from core.Household import Household
from core.FridgeItem import FridgeItem
from core.ConsumptionRecord import ConsumptionRecord
from core.CartItem import CartItem
from core.Cart import Cart


class IO_manager:
    def __init__(self):
        self.__valid_units = ["kg", "g", "l", "ml", "pcs"]
        self.__valid_genders = ["male", "female"]
        self.__remarks_prompt = TextPrompt(
            "\nAny remarks for this week? e.g. hosting a party, going on holiday (leave blank if none): ",
            allow_blank=True, max_length=MAX_REMARKS_LENGTH)
        self.__days_prompt = IntRangePrompt("\nIn how many days do you plan to shop next? (e.g. 7): ", 1, 365)

    def __ask_yes_no(self, question, error_message="Please answer yes or no."):
        answer = ChoicePrompt(question + "(yes/no): ", ["yes", "y", "no", "n"], error_message).ask()
        return answer in ["yes", "y"]

    # Ask for a date in YYYY-MM-DD format and check it is a real date.
    def __ask_date(self, question, allow_past=False, purchase_date=""):
        today = date.today()
        earliest = shift_calendar_years(today, -1) if allow_past else today
        # maximum expiry date
        latest = shift_calendar_years(today, 3)
        return DatePrompt(question, earliest, latest, purchase_date).ask()

    def __name_unit_pairs(self, items):
        return [(item.name, item.unit) for item in items]

    # Ask for one item's name, quantity and unit, validating bad input.
    # If the item already exists in known_items, its unit is reused.
    def __enter_item(self, known_items):
        item_name = TextPrompt("Item name: ", max_length=MAX_ITEM_NAME_LENGTH).ask()

        # Check if this item was entered before, and lock its unit
        locked_unit = ""
        for name, unit in known_items:
            if name.lower() == item_name.lower():
                locked_unit = unit
                print(f"{item_name} was entered before in {locked_unit}, so please enter the quantity in {locked_unit}.")
                break

        # Ask for quantity and unit together
        while True:
            if locked_unit != "":
                text = input(f"Quantity in {locked_unit} (e.g. 3): ").strip().lower()
            else:
                text = input(f"Quantity and unit (e.g. 6kg, 500 g, 3 pcs) - units: {', '.join(self.__valid_units)}: ").strip().lower()

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
                print(f"Please include a unit ({', '.join(self.__valid_units)}), e.g. 6kg.")
            elif unit != "" and unit not in self.__valid_units:
                print(f"'{unit}' is not a valid unit. Please use one of: {', '.join(self.__valid_units)}.")
            elif locked_unit != "" and unit != "" and unit != locked_unit:
                print(f"{item_name} must be entered in {locked_unit}.")
            else:
                if (unit or locked_unit) == "pcs" and not number_part.isdigit():
                    print("Items in pcs must be a whole number.")
                else:
                    try:
                        quantity = normalize_quantity(number_part)
                    except ValueError:
                        print(f"Quantity must be a valid number no greater than {MAX_QUANTITY:,}.")
                        continue
                    if quantity == 0:
                        print("Quantity is too small after rounding to 4 decimal places.")
                        continue
                    if unit == "":
                        unit = locked_unit
                    break

        return item_name, quantity, unit

    # Ask whether the user wants to add another item or edit/delete an item.
    def __ask_add_another(self):
        return ChoicePrompt("\n1. Add item\n2. Edit/Remove an item\n3. Confirm and submit items\n"
                            "Choose your option (1,2 or 3): ", ["1", "2", "3"],
                            "Please choose a valid option (1,2 or 3)").ask()

    # For new users: Collect the food items they already have at home, with expiry dates.
    def __add_item(self, remaining_items):
        item_name, quantity, unit = self.__enter_item(self.__name_unit_pairs(remaining_items))
        expiry_date = self.__ask_date("Expiry date (YYYY-MM-DD): ")
        item_remarks = TextPrompt("Any remarks about this item? e.g. opened, for a party (leave blank if none): ",
                                  allow_blank=True, max_length=MAX_REMARKS_LENGTH).ask()

        if item_remarks == "":
            item_remarks = "none"

        item = FridgeItem(item_name, quantity, unit, "", expiry_date, item_remarks)

        # Check whether an identical item and expiry date already exist
        for index in range(len(remaining_items)):
            existing = remaining_items[index]
            if (
                existing.name.lower() == item.name.lower()
                and existing.unit == item.unit
                and existing.expiry_date == item.expiry_date
            ):
                # Add quantities using Decimal
                combined_quantity = (Decimal(str(existing.quantity)) + Decimal(str(item.quantity)))
                if combined_quantity > MAX_QUANTITY:
                    print(f"Total quantity cannot exceed {MAX_QUANTITY:,}.")
                    return remaining_items

                # Merge remarks safely
                new_remarks = existing.remarks

                if item.remarks != "none" and item.remarks != new_remarks:
                    if new_remarks == "none":
                        new_remarks = item.remarks
                    else:
                        new_remarks += ", " + item.remarks

                if len(new_remarks) > MAX_REMARKS_LENGTH:
                    print(f"Combined remarks cannot exceed {MAX_REMARKS_LENGTH} characters.")
                    return remaining_items

                # Update the existing item after validation
                existing = FridgeItem(existing.name, normalize_quantity(combined_quantity), existing.unit,
                                      existing.purchase_date, existing.expiry_date, new_remarks)
                remaining_items[index] = existing

                print(f"{existing.name} is already in your home items.\nTotal is now {self.format_item(existing)}.")
                return remaining_items

        # No matching item found then will add a new item
        remaining_items.append(item)

        print(f"Added {self.format_item(item)} to your home items.")
        return remaining_items

    def __add_to_cart(self, cart, other_known_items):
        item_name, quantity, unit = self.__enter_item(self.__name_unit_pairs(cart.get_items()) + other_known_items)

        # If the same item with the same unit was already entered, add to it
        for existing in cart.get_items():
            if existing.name.lower() == item_name.lower() and existing.unit == unit:
                combined_quantity = (Decimal(str(existing.quantity)) + Decimal(str(quantity)))
                if combined_quantity > MAX_QUANTITY:
                    print(f"Total quantity cannot exceed {MAX_QUANTITY:,}.")
                    return
                # To normalize to prevent e.g 0.30000000004 values
                existing.edit_quantity(normalize_quantity(combined_quantity))
                print(f"{existing.name} is already in your list.\nTotal is now {self.format_item(existing)}.")
                return
        item = CartItem(item_name, quantity, unit)
        cart.add_item(item)
        print(f"Added {self.format_item(item)}.")

    def __edit_item(self, item, remove_item):
        while True:
            print(f"Selected {item.name}, Current Quantity: {item.quantity}")

            edited_quantity = input("Enter new amount (enter 0 to delete item): ").strip()
            if edited_quantity.replace(".", "", 1).isdecimal():
                if float(edited_quantity) == 0:
                    remove_item(item)
                else:
                    if item.unit == 'pcs' and not edited_quantity.isdigit():
                        print("quantity must be a whole number for unit pcs")
                        continue
                    try:
                        new_qty = normalize_quantity(edited_quantity)
                    except ValueError:
                        print(f"Quantity cannot exceed {MAX_QUANTITY:,}.")
                        continue

                    if new_qty == 0:
                        if Decimal(edited_quantity) != 0:
                            print("Quantity is too small after rounding to 4 decimal places.")
                            continue
                        remove_item(item)
                    else:
                        item.edit_quantity(new_qty)
                return
            else:
                print("Invalid input. Enter a positive number")

    #can be used to edit grocery list or recommendation list
    def __edit_list(self, item_list, remove_item):
        while True:
            item_index = input("\nEnter item number to edit/delete or enter 'exit' to save: ").strip().lower()
            if item_index == "exit":
                return True
            elif item_index.isdecimal():
                if int(item_index) in range(1, len(item_list) + 1): # check if option is in the list
                    self.__edit_item(item_list[int(item_index) - 1], remove_item)
                    return False
                else:
                    print("Invalid input. Enter item number to edit/delete or enter 'exit' to save")
            else:
                print("Invalid input. Enter item number to edit/delete or enter 'exit' to save")

    # Collect a new user's profile and their family members' details.
    def create_profile(self):
        genders = ", ".join(self.__valid_genders)
        household = Household()

        name = TextPrompt("Please enter your name: ", max_length=MAX_PERSON_NAME_LENGTH).ask()
        age = IntRangePrompt("Please enter your age: ", 10, 120,
                             "Please enter a valid age (whole number between 10 and 120).").ask()
        gender = ChoicePrompt(f"Please enter your gender ({genders}): ", self.__valid_genders,
                              "Please enter male or female.").ask()
        dietary_restrictions = TextPrompt("Please enter your dietary restrictions (leave blank if none): ",
                                          allow_blank=True, max_length=MAX_DIETARY_LENGTH).ask()
        if dietary_restrictions == "":
            dietary_restrictions = "none"
        family = IntRangePrompt("Please enter your family size including yourself: ", 1, 20).ask()

        household.add_member(Person(1, name, age, gender.capitalize(), dietary_restrictions))

        for i in range(family - 1):
            member_name = TextPrompt(f"Please enter the name of family member {i + 1}: ",
                                     max_length=MAX_PERSON_NAME_LENGTH).ask()
            member_age = IntRangePrompt(f"Please enter the age of {member_name}: ", 1, 120,
                                        "Please enter a valid age (whole number between 0 and 120).").ask()
            member_gender = ChoicePrompt(f"Please enter the gender of {member_name} ({genders}): ",
                                         self.__valid_genders, "Please enter male or female.").ask()
            member_diet = TextPrompt(f"Please enter the dietary restrictions of {member_name} (leave blank if none): ",
                                     allow_blank=True, max_length=MAX_DIETARY_LENGTH).ask()
            if member_diet == "":
                member_diet = "none"
            household.add_member(Person(i + 2, member_name, member_age, member_gender.capitalize(), member_diet))

        print(f"User {name} registered successfully!")
        return household

    # Collect home inventory during initial registration
    def enter_home_items(self):
        remaining_items = []
        if not self.__ask_yes_no("\nDo you have any food items at home you want to add? "):
            return remaining_items
        print("\nEnter the items you currently have at home.")
        remaining_items = self.__add_item(remaining_items)
        while True:
            self.display_list("Fridge", remaining_items)
            user_choice = self.__ask_add_another()

            if user_choice == "1":
                remaining_items = self.__add_item(remaining_items)
            elif user_choice == "2":
                if not remaining_items:
                    print("No items to edit or remove.")
                    continue
                while True:
                    self.display_list("Fridge", remaining_items)
                    if self.__edit_list(remaining_items, remaining_items.remove):
                        break
            else:
                return remaining_items

    # For returning users: Ask how much of each item they consumed since last visit.
    # Batches of the same item are combined into one question.
    # Days since last use and remarks are asked once and applied to every item.
    def update_consumption(self, fridge):
        consumed_items = []
        if not fridge.get_items():
            return consumed_items

        # Add up the total of each item across all its batches
        totals = {}
        for item in fridge.get_items():
            key = (item.name.lower(), item.unit)
            if key in totals:
                totals[key]["Quantity"] += Decimal(str(item.quantity))
            else:
                totals[key] = {"Item_Name": item.name, "Quantity": Decimal(str(item.quantity)), "Unit": item.unit}
        print("\nUpdate Consumption.")
        # Asked once for the whole consumption list
        date_range = IntRangePrompt("How many days has it been since you last used the app? ", 1, 365).ask()

        consumed_amounts = []
        for key in totals:
            name = totals[key]["Item_Name"]
            total = totals[key]["Quantity"]
            unit = totals[key]["Unit"]
            consumed = QuantityPrompt(f"How much {name} did you consume? (you have {total} {unit}): ",
                                      max_value=total, allow_zero=True, whole_number=(unit == "pcs"),
                                      normalize=normalize_quantity,
                                      max_message=f"That's more than you have ({total} {unit}). Please try again.").ask()
            consumed_amounts.append((name, consumed, unit))

        # Asked once, then added to every item
        remarks = TextPrompt("Any remarks about your consumption since last time? (leave blank if none): ",
                             allow_blank=True, max_length=MAX_REMARKS_LENGTH).ask()
        if remarks == "" or remarks.lower() == "none":
            remarks = "none"
        for name, consumed, unit in consumed_amounts:
            consumed_items.append(ConsumptionRecord(name, consumed, unit, date_range, remarks))

        return consumed_items

    # Collect the groceries the user plans to buy, until they say they are done.
    def enter_grocery_list(self, fridge, history):
        other_known_items = (self.__name_unit_pairs(fridge.get_items())
                             + [(record["Item_Name"], record["Unit"]) for record in history.to_dicts()])
        cart = Cart()
        print("\nEnter the groceries you are planning to buy.")

        self.__add_to_cart(cart, other_known_items)

        while True:
            self.display_list("Grocery Cart", cart.get_items())
            user_choice = self.__ask_add_another()
            if user_choice == "1": # add items
                self.__add_to_cart(cart, other_known_items)
            elif user_choice == "2": #edit cart
                while True:
                    self.display_list("Grocery Cart", cart.get_items())
                    if self.__edit_list(cart.get_items(), cart.remove_item):
                        break
            else: # exit CRUD of cart
                if len(cart.get_items()) == 0:
                    print(f"grocery list cannot be empty! please enter at least 1 item")
                else:
                    break

        send_log(f"[IO MANAGER] grocery_list = {[item.to_dict() for item in cart.get_items()]}") #log grocery list for verification
        return cart

    # Ask for optional remarks about this week (e.g. events).
    def ask_remarks(self):
        remarks = self.__remarks_prompt.ask()
        if remarks == "" or remarks.lower() == "none":
            remarks = "none"
        return remarks

    # Ask how many days until the user's next planned shop.
    def ask_days_until_next(self):
        return self.__days_prompt.ask()

    # Show the returning user's menu and return their choice ("1" or "2").
    def ask_menu_choice(self):
        return ChoicePrompt("\nWhat would you like to do?\n"
                            "  1. Update consumption and plan groceries\n"
                            "  2. Edit expiry dates or delete items from your fridge\n"
                            "  3. Save database and exit the program\n"
                            "Enter 1, 2 or 3: ", ["1", "2", "3"], "Please enter 1, 2 or 3.").ask()

    # Let the user edit expiry dates or delete items from their fridge until they are done.
    def update_fridge(self, fridge):
        while True:
            items = fridge.get_items()
            self.display_list("Fridge", items)
            if not items:
                return

            print("\nWhat would you like to do with your fridge?")
            print("  1. Edit an expiry date")
            print("  2. Delete an item")
            print("  3. Done")
            action = input("Enter 1, 2 or 3: ").strip()
            if action == "3":
                return
            elif action not in ["1", "2"]:
                print("Please enter 1, 2 or 3.")
                continue

            number = IntRangePrompt(f"Enter the item number (1-{len(items)}): ", 1, len(items),
                                    f"Please enter a number between 1 and {len(items)}.").ask() - 1

            if action == "1":
                selected_item = items[number]
                expiry_date = self.__ask_date(f"New expiry date for {selected_item.name} (YYYY-MM-DD): ",
                                              allow_past=True, purchase_date=selected_item.purchase_date)

                matching_items = []
                total_quantity = Decimal(str(selected_item.quantity))

                for existing in items:
                    if existing is selected_item:
                        continue

                    if (
                        existing.name.lower() == selected_item.name.lower()
                        and existing.unit == selected_item.unit
                        and existing.purchase_date == selected_item.purchase_date
                        and existing.expiry_date == expiry_date
                        and existing.remarks == selected_item.remarks
                    ):
                        matching_items.append(existing)
                        total_quantity += Decimal(str(existing.quantity))

                if total_quantity > MAX_QUANTITY:
                    print(f"Total quantity cannot exceed {MAX_QUANTITY:,}. Expiry date was not changed.")
                    continue

                selected_item.edit_expiry_date(expiry_date)
                selected_item.edit_quantity(normalize_quantity(total_quantity))

                for existing in matching_items:
                    fridge.remove_item(existing)

                if matching_items:
                    print(f"Updated and merged: {self.format_item(selected_item)}")
                else:
                    print(f"Updated: {self.format_item(selected_item)}")
            else:
                removed = items[number]
                fridge.remove_item(removed)
                print(f"{self.format_item(removed)} has been removed from your fridge.")

    #displays recommendations made by business logic
    def output_recommendations(self, calories_message, risk_of_expiry_messages, underbuy_messages, recommendations):
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

    #handles IO for after AI and logic processes
    def shopping_cart_conclusion(self, cart, remarks):
        self.display_list("Recommendations List", cart.get_items())
        if self.__ask_yes_no("\nWould you like to change the quantity of items in your grocery cart? ",
                             "Invalid input. Please enter 'yes' or 'no'."):
            while True:
                self.display_list("Recommendations List", cart.get_items())
                if self.__edit_list(cart.get_items(), cart.remove_item):
                    break
        else:
            print("\nYour grocery cart has been concluded.")
        return [item.to_fridge_item(remarks) for item in cart.get_items()]

    # Formatting-----------
    def format_item(self, item):
        text = f"{item.quantity:g} {item.unit} of {item.name}"
        details = []
        if getattr(item, "expiry_date", "") != "":
            details.append(f"expires {item.expiry_date}")
        if getattr(item, "remarks", "none") != "none":
            details.append(item.remarks)
        if details:
            text += f" ({', '.join(details)})"
        return text

    # Display four dp correctly
    def format_display_quantity(self, value):
        text = format(Decimal(str(value)), "f")
        if "." in text: text = text.rstrip("0").rstrip(".")
        return text

    #display either the fridge, grocery cart or recommendations list in a numbered list format
    #list_name can ONLY be "Fridge" or "Grocery Cart" or "Recommendations List"
    def display_list(self, list_name, item_list):
        if not item_list:
                print(f"\n{list_name}\n  (empty! add some items to see something)")
                return

        name_width = max(len("Item name"), max(len(item.name) for item in item_list)) + 2 #align table according to how big item_name is
        if list_name == "Fridge":
            remarks_width = max(len("Remarks"), max(len(item.remarks) for item in item_list)) + 2 #align table according to how big item_name is

        # Construct and print headers
        header = f"\n{list_name}\n{'No.':<4}| {'Item name':<{name_width}}| {'Current amt':<12}| "
        if list_name == "Grocery Cart": #pre AI grocery list
            pass

        elif list_name == "Recommendations List":
            header += f"{'Recommended amt':<16}| {'CS*':<6}| "

        elif list_name == "Fridge":
            header += f"{'Purchase date':<14}| {'Expiry date':<12}| {'Remarks':<{remarks_width}}| "
        print(header)


        # Construct and print rows
        for i in range(0,len(item_list)):
            item = item_list[i]
            message = f"{i+1:<4}| {item.name:<{name_width}}| "
            cur_amt_formatted = f"{self.format_display_quantity(item.quantity)} {item.unit}"
            if list_name == "Grocery Cart": #pre AI grocery list
                message += f"{cur_amt_formatted:<12}| "

            elif list_name == "Recommendations List":
                recommened_amt_formatted = f"{self.format_display_quantity(item.ai_data.recommended_qty)} {item.unit}"
                if item.ai_data.confidence_score == 0:
                    confidence_score_formatted = f"NA"
                else:
                    confidence_score_formatted = f"{round(item.ai_data.confidence_score, 1)}%"
                message += f"{cur_amt_formatted:<12}| {recommened_amt_formatted:<16}| {confidence_score_formatted:<6}| "

            elif list_name == "Fridge":
                if item.purchase_date == "":
                    purchase_date_formatted = f"NA"
                else:
                    purchase_date_formatted = f"{item.purchase_date}"
                message += f"{cur_amt_formatted:<12}| {purchase_date_formatted:<14}| {item.expiry_date:<12}| {item.remarks:<{remarks_width}}| "
            print(message)

        if list_name == "Recommendations List":
            print(f"* CS --> Confidence score: how accurate the AI estimation is")
            print(f"if CS is NA there is not enough past data to provide score")

    # Print a summary of everyone in the household.
    def show_profile(self, household_info):
        print("\nHousehold summary:")
        for member in household_info.get_members():
            person = member.to_dict()
            print(f"  {person['Person_ID']}. {person['Name']}, {person['Age']}, {person['Gender']}, "
                  f"diet: {person['Dietary_Restriction']}")

    # Print a summary of what was recorded as consumed.
    def show_consumption(self, consumed_items):
        print("\nConsumption recorded:")
        if not consumed_items:
            print("  (none)")
            return
        print(f"  Over the last {consumed_items[0].date_range} day(s), remarks: {consumed_items[0].to_dict()['Remarks']}")
        for i in range(len(consumed_items)):
            record = consumed_items[i]
            print(f"  {i + 1}. {record.quantity:g} {record.unit} of {record.name}")

    # Print the start-up welcome message.
    def show_welcome(self):
        print("Welcome to the Waste Management System!")

    # Print the welcome-back message for a returning user (Person_ID 1 is the user).
    def show_welcome_back(self, household_info):
        print(f"Welcome back, {household_info.get_members()[0].to_dict()['Name']}!")

    # Print exit message
    def show_exit(self):
        print(f"Your data has been recorded into the system")
        print(f"Thank you for using the Waste Management System!")

    def send_message(self, message):
        print(f"{message}")


# =====================================================================
# Testing
# =====================================================================

if __name__ == "__main__":
    from core.Fridge import Fridge
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData

    ui = IO_manager()
    household_info = Household()      # add Person(1, "Test", 20, "Male", "none") to test a returning user
    fridge = Fridge()                 # e.g. fridge.add_item(FridgeItem("Milk", 2, "l", "2026-09-21", "2026-12-05", "none"))
    history = ConsumptionHistory()
    remaining_items = []
    consumed_items = []

    ui.show_welcome()

    if not household_info.get_members():
        household_info = ui.create_profile()
        ui.show_profile(household_info)
        remaining_items = ui.enter_home_items()
        ui.display_list("Fridge", remaining_items)
    else:
        ui.show_welcome_back(household_info)
        while True:
            choice = ui.ask_menu_choice()
            if choice == "1":
                consumed_items = ui.update_consumption(fridge)
                ui.show_consumption(consumed_items)
                break
            else:
                ui.update_fridge(fridge)

    cart = ui.enter_grocery_list(fridge, history)

    remarks = ui.ask_remarks()
    days_until_next = ui.ask_days_until_next()
    for item in cart.get_items():
        item.set_ai_data(AIRecData(item.quantity, 0, ""))
    final_checkout = ui.shopping_cart_conclusion(cart, remarks)

    print("\n--- Test results ---")
    print("household_info =", household_info.to_dicts())
    print("fridge =", fridge.to_dicts())
    print("remaining_items =", [item.to_dict() for item in remaining_items])
    print("consumed_items =", [record.to_dict() for record in consumed_items])
    print("grocery_list =", [item.to_dict() for item in cart.get_items()])
    print("remarks =", remarks)
    print("days_until_next =", days_until_next)
    print("final_checkout =", [item.to_dict() for item in final_checkout])