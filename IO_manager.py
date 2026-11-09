from logger import app_logger
from ioclasses import (TextPrompt, QuantityPrompt, DatePrompt, IntRangePrompt, ChoicePrompt,
                       QuantityUnitPrompt, EditQuantityPrompt)
from core.ItemRecord import ItemRecord
from core.ListFunctions import ListFunctions
from core.ItemFunctions import ItemFunctions
from core.Person import Person
from core.Household import Household
from core.Fridge import Fridge
from core.FridgeItem import FridgeItem
from core.ConsumptionHistory import ConsumptionHistory
from core.ConsumptionRecord import ConsumptionRecord
from core.CartItem import CartItem
from core.Cart import Cart
from core.UnitValidator import UnitValidator


class IO_manager:

    def __ask_yes_no(self, question, error_message="Please answer yes or no."):
        answer = ChoicePrompt(question + "(yes/no): ", ["yes", "y", "no", "n"], error_message).ask()
        return answer in ["yes", "y"]

    # Ask for one item's name, quantity and unit, validating bad input.
    # If the item was entered before, its unit is reused.
    # used by __add_fridge_item() and __add_cart_item()
    def __enter_item(self, unit_validator, other_items=None):
        item_name = TextPrompt("Item name: ", max_length=ItemRecord.MAX_NAME_LENGTH).ask()

        # Check if this item was entered before, and lock its unit
        locked_unit = unit_validator.find_unit(item_name, other_items)
        if locked_unit != "":
            print(f"{item_name} was entered before in {locked_unit}, so please enter the quantity in {locked_unit}.")

        # Ask for quantity and unit together
        quantity, unit = QuantityUnitPrompt(item_name, ItemRecord.VALID_UNITS, locked_unit, ItemRecord.MAX_QUANTITY).ask()
        return item_name, quantity, unit

    # Ask whether the user wants to add another item or edit/delete an item.
    def __ask_add_another(self):
        return ChoicePrompt("\n1. Add item\n2. Edit/Remove an item\n3. Confirm and submit items\n"
                            "Choose your option (1,2 or 3): ", ["1", "2", "3"],
                            "Please choose a valid option (1,2 or 3)").ask()

    # For new users: Collect the food items they already have at home, with expiry dates.
    # used by initialize_fridge()
    def __add_fridge_item(self, home_items: Fridge):
        item_name, quantity, unit = self.__enter_item(UnitValidator(home_items))
        expiry_date = DatePrompt("Expiry date (YYYY-MM-DD): ").ask()
        item_remarks = TextPrompt("Any remarks about this item? e.g. opened, for a party (leave blank if none): ",
                                  allow_blank=True, max_length=ItemRecord.MAX_REMARKS_LENGTH).ask()

        if item_remarks == "":
            item_remarks = "none"

        item = FridgeItem(item_name, quantity, unit, "", expiry_date, item_remarks)

        # Check whether an identical item and expiry date already exist
        try:
            merged = home_items.add_item(item)
        except ValueError as error:
            print(error)
            return
        if merged:
            print(f"{item.name} is already in your home items.\nTotal is now {self.__format_item(item)}.")
        else:
            print(f"Added {self.__format_item(item)} to your home items.")

    #used by enter_grocery_list()
    def __add_cart_item(self, cart, unit_validator):
        item_name, quantity, unit = self.__enter_item(unit_validator, cart.get_items())

        # If the same item with the same unit was already entered, add to it
        try:
            cart_item = CartItem(item_name, quantity, unit)
            merged = cart.add_item(cart_item)
        except ValueError as error:
            print(error)
            return
        if merged:
            print(f"{cart_item.name} is already in your list.\nTotal is now {self.__format_item(cart_item)}.")
        else:
            print(f"Added {self.__format_item(cart_item)}.")

    def __edit_item(self, item: ItemFunctions):
        new_qty = EditQuantityPrompt(f"Selected {item.name}, Current Quantity: {item.quantity}\n"
                                     "Enter new amount (enter 0 to delete item): ",
                                     item.unit == 'pcs', ItemRecord.MAX_QUANTITY).ask()
        if new_qty == 0:
            return True
        else:
            item.set_quantity(new_qty)
            return False

    #can be used edit Fridge or Cart
    def __edit_list(self, item_list: ListFunctions):
        while True:
            item_index = input("\nEnter item number to edit/delete or enter 'exit' to save: ").strip().lower()
            if item_index == "exit":
                return True
            elif item_index.isdecimal():
                if int(item_index) in range(1, len(item_list.get_items()) + 1): # check if option is in the list
                    item = item_list.get_item_at(int(item_index) - 1)
                    delete_item = self.__edit_item(item)
                    if delete_item == True:
                        item_list.remove_item(item)
                    return False
                else:
                    print("Invalid input. Enter item number to edit/delete or enter 'exit' to save")
            else:
                print("Invalid input. Enter item number to edit/delete or enter 'exit' to save")

    #used by initialize_household()
    def __get_person_info(self) -> tuple:
        genders = ", ".join(Person.VALID_GENDERS)
        name = TextPrompt("Please enter name: ", max_length=Person.MAX_NAME_LENGTH).ask()
        age = IntRangePrompt("Please enter age: ", Person.MIN_AGE, Person.MAX_AGE, f"Please enter a valid age (whole number between {Person.MIN_AGE} and {Person.MAX_AGE}).").ask()
        gender = ChoicePrompt(f"Please enter gender ({genders}): ", Person.VALID_GENDERS,
                                f"Please enter from the list of options: ({genders})").ask()
        dietary_restrictions = TextPrompt("Please enter dietary restrictions (leave blank if none): ",
                                            allow_blank=True, max_length=Person.MAX_DIETARY_LENGTH).ask()
        if dietary_restrictions == "":
            dietary_restrictions = "none"

        return name, age, gender, dietary_restrictions

    # Collect a new user's profile and their family members' details.
    def initialize_household(self, household: Household):
        name, age, gender, dietary_restrictions = self.__get_person_info()
        household.add_member(Person(1, name, age, gender.capitalize(), dietary_restrictions))

        family = IntRangePrompt("Please enter your family size including yourself: ", Household.MIN_PAX, Household.MAX_PAX).ask()
        for i in range(family - 1):
            print(f"Please enter the details for the next family member")
            others_name, others_age, others_gender, others_dietary_restrictions = self.__get_person_info()
            household.add_member(Person(i + 2, others_name, others_age, others_gender.capitalize(), others_dietary_restrictions))

        print(f"User {name} registered successfully!")

    # Collect home inventory during initial registration
    def initialize_fridge(self, fridge: Fridge) -> None:
        if not self.__ask_yes_no("\nDo you have any food items at home you want to add? "):
            return
        print("\nEnter the items you currently have at home.")
        self.__add_fridge_item(fridge)
        while True:
            self.display_fridge(fridge)
            user_choice = self.__ask_add_another()

            if user_choice == "1":
                self.__add_fridge_item(fridge)
            elif user_choice == "2":
                if not fridge.get_items():
                    print("No items to edit or remove.")
                    continue
                while True:
                    self.display_fridge(fridge)
                    if self.__edit_list(fridge):
                        break
            else:
                return 

    def get_consumption_remarks(self) -> str:
        remarks = TextPrompt("Any remarks about your consumption since last time? (leave blank if none): ",
                                allow_blank=True, max_length=ItemRecord.MAX_REMARKS_LENGTH).ask()
        if remarks == "" or remarks.lower() == "none":
            remarks = "none"
        return remarks

    def ask_last_use_days(self):
        return IntRangePrompt("How many days has it been since you last used the app? ", 1, 365).ask()
    
    # For returning users: Ask how much of each item they consumed since last visit.
    # Batches of the same item are combined into one question.
    # Asked once, then added to every item
    def get_consumption(self, fridge: Fridge, history: ConsumptionHistory, last_used_days: int, consumption_remarks: str) -> None:
        total_items = fridge.get_fridge_totals()
        total_records = []
        for combined_item in total_items:
            consumed_amount = QuantityPrompt(f"How much {combined_item['item_name']} did you consume? (you have {combined_item['quantity']} {combined_item['units']}): ",
                                    max_value=combined_item['quantity'], allow_zero=True, whole_number=(combined_item['units'] == "pcs"),
                                    normalize=True,
                                    max_message=f"That's more than you have ({combined_item['quantity']} {combined_item['units']}). Please try again.").ask()
            if consumed_amount == 0:
                continue
            record = fridge.consume(combined_item['item_name'], consumed_amount, combined_item['units'], last_used_days, consumption_remarks)
            history.add_record(record)
            total_records.append(record)

        self.show_consumption(total_records, last_used_days, consumption_remarks)


    # Collect the groceries the user plans to buy, until they say they are done.
    def enter_grocery_list(self, cart: Cart, fridge: Fridge, history: ConsumptionHistory) -> None:
        unit_validator = UnitValidator(fridge, history)
        print("\nEnter the groceries you are planning to buy.")
        self.__add_cart_item(cart, unit_validator)
        while True:
            self.display_cart(cart)
            user_choice = self.__ask_add_another()
            if user_choice == "1": # add items
                self.__add_cart_item(cart, unit_validator)
            elif user_choice == "2": #edit cart
                while True:
                    self.display_cart(cart)
                    if self.__edit_list(cart):
                        break
            else: # exit CRUD of cart
                if len(cart.get_items()) == 0:
                    print(f"grocery list cannot be empty! please enter at least 1 item")
                else:
                    break

        app_logger.send_log(f"[IO MANAGER] grocery_list = {[item.to_dict() for item in cart.get_items()]}") #log grocery list for verification

    # Ask for optional remarks about this week (e.g. events).
    def get_cart_remarks(self):
        remarks = TextPrompt(
            "\nAny remarks for this week? e.g. hosting a party, going on holiday (leave blank if none): ",
            allow_blank=True, max_length=ItemRecord.MAX_REMARKS_LENGTH).ask()
        if remarks == "" or remarks.lower() == "none":
            remarks = "none"
        return remarks

    # Ask how many days until the user's next planned shop.
    def ask_days_until_next(self):
        return IntRangePrompt("\nIn how many days do you plan to shop next? (e.g. 7): ", 1, 365).ask()

    # Show the returning user's menu and return their choice ("1" or "2").
    def ask_main_menu_choice(self):
        return ChoicePrompt("\nWhat would you like to do?\n"
                            "  1. Update consumption and plan groceries\n"
                            "  2. Edit expiry dates or delete items from your fridge\n"
                            "  3. Save database and exit the program\n"
                            "Enter 1, 2 or 3: ", ["1", "2", "3"], "Please enter 1, 2 or 3.").ask()

    # Let the user edit expiry dates or delete items from their fridge until they are done.
    def update_fridge(self, fridge: Fridge):
        while True:
            items = fridge.get_items()
            self.display_fridge(fridge)
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
                selected_item = fridge.get_item_at(number)
                expiry_date = DatePrompt(f"New expiry date for {selected_item.name} (YYYY-MM-DD): ",
                                              allow_past=True, purchase_date=selected_item.purchase_date).ask()
                try:
                    merged = fridge.change_expiry(selected_item, expiry_date)
                except ValueError as error:
                    print(error)
                    continue
                if merged:
                    print(f"Updated and merged: {self.__format_item(selected_item)}")
                else:
                    print(f"Updated: {self.__format_item(selected_item)}")
            else:
                removed = fridge.get_item_at(number)
                fridge.remove_item(removed)
                print(f"{self.__format_item(removed)} has been removed from your fridge.")

    #displays recommendations made by business logic
    def output_recommendations(self, calories_message, risk_of_expiry_messages, underbuy_messages):
        print(f"\n--------------------------------Recommendations---------------------------------")
        print(f"\n{calories_message[0]}")
        print(f"\n--------------------------------------------------------------------------------")
        if len(risk_of_expiry_messages) != 0:
            print(f"\nBased on your consumption history, the following items "
                  f"\nare likely to expire before your next trip:")
            for i in range(len(risk_of_expiry_messages)):
                print(f"  {i+1}. {risk_of_expiry_messages[i]}")
            print(f"\n--------------------------------------------------------------------------------")
        if len(underbuy_messages) != 0:
            print(f"Based on your consumption history, you may run out of the following items and want to buy more:")
            for i in range(len(underbuy_messages)):
                print(f"  {i+1}. {underbuy_messages[i]}")
            print(f"\n--------------------------------------------------------------------------------")

    #handles IO for after AI and logic processes
    def shopping_cart_conclusion(self, cart: Cart) -> None:
        self.display_cart(cart)
        if self.__ask_yes_no("\nWould you like to change the quantity of items in your grocery cart? ",
                             "Invalid input. Please enter 'yes' or 'no'."):
            while True:
                self.display_cart(cart)
                if self.__edit_list(cart):
                    break
        else:
            print("\nYour grocery cart has been concluded.")

    # Formatting-----------
    def __format_item(self, item):
        text = f"{item.quantity:g} {item.unit} of {item.name}"
        details = []
        if getattr(item, "expiry_date", "") != "":
            details.append(f"expires {item.expiry_date}")
        if getattr(item, "remarks", "none") != "none":
            details.append(item.remarks)
        if details:
            text += f" ({', '.join(details)})"
        return text

    def display_fridge(self, fridge: Fridge):
        item_list = fridge.get_items()
        if not item_list:
            print(f"\nFridge\n  (empty! add some items to see something)")
            return
        name_width = max(len("Item name"), max(len(item.name) for item in item_list)) + 2 #align table according to how big item_name is
        remarks_width = max(len("Remarks"), max(len(item.remarks) for item in item_list)) + 2 #align table according to how big item_name is
        
        header = f"\nFridge\n{'No.':<4}| {'Item name':<{name_width}}| {'Current amt':<12}| {'Purchase date':<14}| {'Expiry date':<12}| {'Remarks':<{remarks_width}}| "
        print(header)
        #format and print items
        for i in range(0,len(item_list)):
            item = item_list[i]
            message = f"{i+1:<4}| {item.name:<{name_width}}| "
            cur_amt_formatted = f"{item.quantity:g} {item.unit}"
            if item.purchase_date == "":
                purchase_date_formatted = f"NA"
            else:
                purchase_date_formatted = f"{item.purchase_date}"

            message += f"{cur_amt_formatted:<12}| {purchase_date_formatted:<14}| {item.expiry_date:<12}| {item.remarks:<{remarks_width}}| "
            print(message)

    def display_cart(self, cart: Cart):
        if cart.get_ai_enhanced() == True:
            title = "Recommendation List"
        else:
            title = "Cart"
        item_list = cart.get_items()
        if not item_list:
            print(f"\n{title}\n  (empty! add some items to see something)")
            return
        #print header
        name_width = max(len("Item name"), max(len(item.name) for item in item_list)) + 2 #align table according to how big item_name is
        header = f"\n{title}\n{'No.':<4}| {'Item name':<{name_width}}| {'Current amt':<12}| "
        if cart.get_ai_enhanced() == True:
            header += f"{'Recommended amt':<16}| {'CS*':<6}| "
        print(header)
        #print items
        for i in range(0,len(item_list)):
            item = item_list[i]
            cur_amt_formatted = f"{item.quantity:g} {item.unit}"
            message = f"{i+1:<4}| {item.name:<{name_width}}| {cur_amt_formatted:<12}| "

            if cart.get_ai_enhanced() == True:
                recommened_amt_formatted = f"{item.ai_data.recommended_qty:g} {item.unit}"
                if item.ai_data.confidence_score == 0:
                    confidence_score_formatted = f"NA"
                else:
                    confidence_score_formatted = f"{round(item.ai_data.confidence_score, 1)}%"
                message += f"{recommened_amt_formatted:<16}| {confidence_score_formatted:<6}| "

            print(message)
        if cart.get_ai_enhanced() == True:
            print(f"* CS --> Confidence score: how accurate the AI estimation is")
            print(f"if CS is NA there is not enough past data to provide score")

    # Print a summary of everyone in the household.
    def show_profile(self, household_info):
        print("\nHousehold summary:")
        for member in household_info.get_members():
            print(f"  {member.get_id()}. {member.get_name()}, {member.get_age()}, {member.get_gender()}, "
                  f"diet: {member.get_dietary_restriction()}")

    # Print a summary of what was recorded as consumed.
    def show_consumption(self, consumed_items: list[ConsumptionRecord], days: int, remarks: str):
        print("\nConsumption recorded:")
        if not consumed_items:
            print("  (none)")
            return
        print(f"  Over the last {days} day(s), remarks: {remarks}")
        for i in range(len(consumed_items)):
            record = consumed_items[i]
            print(f"  {i + 1}. {record.quantity:g} {record.unit} of {record.name}")

    # Print the start-up welcome message.
    def show_welcome(self):
        print("Welcome to the Waste Management System!")

    # Print the welcome-back message for a returning user (Person_ID 1 is the user).
    def show_welcome_back(self, household_info):
        user = household_info.get_members()[0]
        print(f"Welcome back, {user.get_name()}!")

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
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData

    ui = IO_manager()
    household_info = Household()      # add Person(1, "Test", 20, "Male", "none") to test a returning user
    fridge = Fridge()                 # e.g. fridge.add_item(FridgeItem("Milk", 2, "l", "2026-09-21", "2026-12-05", "none"))
    history = ConsumptionHistory()
    remaining_items = []
    consumed_items = []

    ui.show_welcome()
    # ALL BELOW MAY BE BROKEN DUE TO REFACTOR, USE MAIN TO TEST
    if not household_info.get_members():
        household_info = ui.initialize_household()
        ui.show_profile(household_info)
        remaining_items = ui.initialize_fridge()
        ui.display_fridge(remaining_items)
    else:
        ui.show_welcome_back(household_info)
        while True:
            choice = ui.ask_main_menu_choice()
            if choice == "1":
                consumed_items = ui.get_consumption(fridge) # this is broken, refer to main
                ui.show_consumption(consumed_items)
                break
            else:
                ui.update_fridge(fridge)

    cart = ui.enter_grocery_list(fridge, history)

    remarks = ui.get_cart_remarks()
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