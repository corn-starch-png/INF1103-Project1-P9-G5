#-------START OF DEPENDENCY LINE----------#
try:
    import sys
    from DB_manager import (load_database_refactored, save_database_refactored)
    from IO_manager import IO_manager
    from core.Fridge import Fridge
    from core.Household import Household
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData
    from AI_manager import AIManager
    from core.AI_classes import OpenRouterProvider
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")

ui = IO_manager()

errors, fridge, household_info, history = load_database_refactored("database")
#-------END OF DEPENDENCY LINE----------#
#region user IO
ui.show_welcome()
#if new user, direct them to create a new profile then add items they have in thier fridge
if not household_info.get_members():
    household_info = ui.create_profile()
    ui.show_profile(household_info)
    #TODO cleanup 
    fridge = ui.create_fridge()
    ui.display_list("Fridge", fridge.get_items())
else:
    ui.show_welcome_back(household_info)
    while True:
        choice = ui.ask_menu_choice()
        #update consumption history then break loop and continue
        if choice == "1":
            #TODO move for loop inside update_consumption out here
            consumed_records = ui.update_consumption(fridge) # list of consumption records

            ui.show_consumption(consumed_records)
            break
        #give user option to edit AI estimated expiry dates or delete items(for example if expired)
        elif choice == "2":
            ui.update_fridge(fridge)
        #exit program
        else:
            save_database_refactored(fridge, household_info, history, 'database')
            ui.show_exit()
            sys.exit(0)

days_until_next_visit = ui.ask_days_until_next()
cart = ui.enter_grocery_list(fridge, history)
remarks = ui.ask_remarks()





#save_database_refactored(fridge, household_info, history)