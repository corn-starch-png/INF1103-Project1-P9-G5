#-------START OF DEPENDENCY LINE----------#
try:
    from dotenv import load_dotenv
    from datetime import date, timedelta, datetime
    import sys
    import os
    import shutil
    from modules.repositories.DB_manager import DB_manager
    from modules.io.IO_manager import IO_manager
    from modules.logic.Logic_manager import Logic_manager
    from modules.core.Cart import Cart
    from modules.core.Fridge import Fridge
    from modules.core.Household import Household
    from modules.core.ConsumptionHistory import ConsumptionHistory
    from modules.core.AIRecData import AIRecData
    from modules.logic.AnalysisContext import AnalysisContext
    from modules.repositories.JsonRepository import JsonRepository
    from modules.ai.AI_manager import AIManager
    from modules.ai.OpenRouterProvider import OpenRouterProvider
    from CartRecommender import CartRecommender
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")

# Load environment variables once
load_dotenv()
ui = IO_manager()
logicmgr = Logic_manager()

# ---------- database selection: shared MongoDB first, local JSON as fallback ----------
def choose_repository():
    if os.getenv("USE_MONGO", "1") == "1":
        try:
            from modules.repositories.MongoDBRepository import MongoDBRepository
            repo = MongoDBRepository()
            errors, bundle = DB_manager().load_database(repo)
            print("Connected to the shared MongoDB database.")
            return repo, errors, bundle
        except Exception as e:
            print(f"MongoDB unavailable ({e}). Using local JSON instead.")
    repo = JsonRepository(folder="database")
    errors, bundle = DB_manager().load_database(repo)
    return repo, errors, bundle

REPOSITORY, errors, data_bundle = choose_repository()
fridge = data_bundle["fridge"]
household_info = data_bundle["household"]
history = data_bundle["consumption_history"]

# ---------- local JSON copy (fallback + backup) ----------
OFFLINE_MARKER = os.path.join("database", ".offline_changes")

def mirror_to_json(backup=False):
    """When running on the cloud, keep the local JSON files in sync."""
    if isinstance(REPOSITORY, JsonRepository):
        return                                   # already running on local JSON
    try:
        if backup:                               # keep the old local files before overwriting them
            dest = os.path.join("database", "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(dest, exist_ok=True)
            for name in ("fridge.json", "household.json", "consumption_history.json"):
                src = os.path.join("database", name)
                if os.path.exists(src):
                    shutil.copy2(src, dest)

        json_repo = JsonRepository(folder="database")
        _, json_stores = json_repo.load()        # gives us JsonRepository's own stores
        json_stores.update({
            "fridge": fridge,
            "household": household_info,
            "consumption_history": history,
        })
        json_repo.save()
    except Exception as e:
        print(f"Warning: could not update the local JSON backup: {e}")

def save_everything():
    try:
        DB_manager().save_database(REPOSITORY)
    except Exception as e:
        print(f"Warning: could not save to the database: {e}")
    mirror_to_json()                             # always keep the local copy current
    if isinstance(REPOSITORY, JsonRepository):   # saved offline: remember it
        os.makedirs("database", exist_ok=True)
        open(OFFLINE_MARKER, "w").close()

# ---------- startup: handle changes made while offline ----------
if not isinstance(REPOSITORY, JsonRepository) and os.path.exists(OFFLINE_MARKER):
    answer = input("You made changes while offline. Upload them to the shared database? "
                   "This REPLACES the cloud data (y/n): ").strip().lower()
    if answer == "y":
        _, local_stores = JsonRepository(folder="database").load()
        data_bundle.update(local_stores)         # swap the cloud-loaded objects for the local ones
        fridge = data_bundle["fridge"]
        household_info = data_bundle["household"]
        history = data_bundle["consumption_history"]
        DB_manager().save_database(REPOSITORY)
        print("Offline changes uploaded to the shared database.")
    else:
        print("Offline changes discarded. Using the shared database data.")
    os.remove(OFFLINE_MARKER)

mirror_to_json(backup=True)     # back up the old local files, then refresh them from the cloud

#-------END OF DEPENDENCY LINE----------#

# old code
# Load environment variables once
# load_dotenv()
# REPOSITORY = JsonRepository(folder="database")
# ui = IO_manager()
# logicmgr = Logic_manager()

# errors, data_bundle = DB_manager().load_database(REPOSITORY)
# fridge = data_bundle["fridge"]
# household_info = data_bundle["household"]
# history = data_bundle["consumption_history"]
#-------END OF DEPENDENCY LINE----------#


#region user IO
ui.show_welcome()
#if new user, direct them to create a new profile then add items they have in thier fridge
if not household_info.get_members():
    ui.initialize_household(household_info)
    ui.show_profile(household_info)
    ui.initialize_fridge(fridge)
    ui.display_fridge(fridge)
else:
    ui.show_welcome_back(household_info)
    while True:
        choice = ui.ask_main_menu_choice()
        #update consumption history then break loop and continue
        if choice == "1":
            last_used_days = ui.ask_last_use_days()
            consumption_remarks = ui.get_consumption_remarks()
            ui.get_consumption(fridge, history, last_used_days, consumption_remarks)
            break
        #give user option to edit AI estimated expiry dates or delete items(for example if expired)
        elif choice == "2":
            ui.update_fridge(fridge)
        #exit program
        else:
            # DB_manager().save_database(REPOSITORY)
            save_everything()
            ui.show_exit()
            sys.exit(0)

days_until_next_visit = ui.ask_days_until_next()
cart = Cart()
recommended_cart = CartRecommender(fridge, history).generate_recommendation()
if recommended_cart.get_items():
    if ui.ask_use_recommended_cart(recommended_cart):
        cart = recommended_cart
else:
    ui.show_no_recommendations()
ui.enter_grocery_list(cart, fridge, history)
remarks = ui.get_cart_remarks()
cart.set_remarks(remarks)

#region AI Recommendations
ui.send_message("Getting AI recommendations... This can take a while.")
# Initialize AI Manager with the OpenRouter provider.
ai_manager = AIManager(OpenRouterProvider())
# Generate recommendations.
ai_recommendations, error = ai_manager.get_ai_recommendations(
    household_info=household_info, 
    consumption_history=history, 
    fridge_stock=fridge, 
    purchase_stock=cart, 
    remarks=cart.get_remarks(), 
    days_until_next=days_until_next_visit,
    notify=ui.send_message
    )
# Handle unsuccessful AI requests.
if error or ai_recommendations is None:
    raise SystemExit(f"AI recommendation failed: {error or 'No response returned.'}")
# Extract validated AI results.
cart.set_ai_enhanced(True)
recommendations = ai_recommendations["Recommendations_List"]
total_planned_calories = ai_recommendations["Total_Planned_Estimated_Calories"]
total_recommended_calories = ai_recommendations["Total_Estimated_Calories"]
#endregion

#create context object for logic calculations
context = AnalysisContext(cart= cart,
                          household= household_info,
                          fridge= fridge,
                          history= history,
                          total_est_calories= total_planned_calories,
                          next_purchase_date= days_until_next_visit
                          )

logicmgr.add_confidence_score(ctx=context)

findings = logicmgr.process_recommendations(ctx= context)

calorie_msg = logicmgr.get_recommedations("CaloriesSurplus", False) #calorie msg is special where we will return a message regardless of the finding state
if not calorie_msg:
    calorie_msg = logicmgr.get_recommedations("CaloriesSurplus", True)
roe_msgs = logicmgr.get_recommedations("RiskOfExpiry", True)
underbuy_msgs = logicmgr.get_recommedations("UnderBuy", True)


#region user IO confirmation
ui.output_recommendations(calorie_msg, roe_msgs, underbuy_msgs)

ui.shopping_cart_conclusion(cart) #output is list of fridge_items
#TODO check if cart can checkout empty
cart.checkout(fridge)

save_everything()
# DB_manager().save_database(REPOSITORY)  # Save the database to the specified folder
ui.show_exit()