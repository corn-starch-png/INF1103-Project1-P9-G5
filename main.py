#-------START OF DEPENDENCY LINE----------#
try:
    from dotenv import load_dotenv
    from datetime import date, timedelta
    import sys
    from DB_manager import (load_database_refactored, save_database_refactored)
    from IO_manager import IO_manager
    from core.Fridge import Fridge
    from core.Household import Household
    from core.ConsumptionHistory import ConsumptionHistory
    from core.AIRecData import AIRecData
    from aiclasses.AI_manager import AIManager
    from aiclasses.OpenRouterProvider import OpenRouterProvider
    from Logic_manager import (under_buy, calories_surplus, risk_of_expiry, calculate_confidence_score, should_evaluate_underbuy)
except ImportError as e :
    raise SystemExit(f"requried libraries do not exist! Ensure requried manager files are in the same directory \n{e}")
# Load environment variables once
load_dotenv()
ui = IO_manager()

from DB_manager import (load_database_refactored, save_database_refactored)
errors, fridge, household_info, history = load_database_refactored("database")


#save_database_refactored(fridge, household_info, history)