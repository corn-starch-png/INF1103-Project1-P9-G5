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

from DB_manager import (load_database_refactored, save_database_refactored)
errors, fridge, household_info, history = load_database_refactored("database")


#save_database_refactored(fridge, household_info, history)