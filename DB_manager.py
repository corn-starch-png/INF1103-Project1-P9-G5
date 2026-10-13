import os
import json
import math
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

KCAL_TABLE={1: {'Male': 880, 'Female': 810}, 2: {'Male': 1080, 'Female': 1000}, 3: {'Male': 1160, 'Female': 1070}, 4: {'Male': 1310, 'Female': 1190}, 5: {'Male': 1440, 'Female': 1320}, 6: {'Male': 1550, 'Female': 1420}, 7: {'Male': 1600, 'Female': 1500}, 8: {'Male': 1740, 'Female': 1620}, 9: {'Male': 1940, 'Female': 1760}, 10: {'Male': 2110, 'Female': 1910}, 11: {'Male': 2280, 'Female': 2070}, 12: {'Male': 2530, 'Female': 2230}, 13: {'Male': 2740, 'Female': 2310}, 14: {'Male': 2920, 'Female': 2360}, 15: {'Male': 3030, 'Female': 2390}, 16: {'Male': 3120, 'Female': 2400}, 17: {'Male': 3180, 'Female': 2400}, 18: {'Male': 3230, 'Female': 2410}, 19: {'Male': 2700, 'Female': 2070}, 30: {'Male': 2590, 'Female': 2035}, 60: {'Male': 2235, 'Female': 1865}}
BONUS_KEYWORDS_FULL_PTS = [
    "holiday",
    "event",
    "guests",
    "visitors",
    "party",
    "cooking",
    "travel",
    "going away",
    "stock up",
    "diet",
    "meal prep",
    "sale"
]
BONUS_KEYWORDS_HALF_PTS = [
    "less than usual",
    "more than usual",
    "eating out",
    "reduce",
    "increase",
    "sharing",
    "special occasion"
]

DB_FILENAME = 'db.json'
FILE_STRUCTURE = {
    'consumption_history': 'Date_Range,Item_Name,Quantity,Unit,Remarks',
    'household_info': 'Person_ID,Name,Age,Gender,Dietary_Restriction',
    'fridge': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date,Remarks'
}

MAX_ITEM_NAME_LENGTH = 50
MAX_PERSON_NAME_LENGTH = 50
MAX_REMARKS_LENGTH = 500
MAX_DIETARY_LENGTH = 200
MAX_QUANTITY = 1_000_000
QUANTITY_STEP = Decimal("0.0001")

#mitigate rounding error in db
def normalize_quantity(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or not 0 <= amount <= MAX_QUANTITY:
            raise ValueError("Quantity must be between 0 and 1,000,000.")
        return float(amount.quantize(QUANTITY_STEP,rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as error:
        raise ValueError("Invalid quantity.") from error

#LOGGING FUNCTIONS--------------
#current_datetime used to generate log filename
#only used by send_log function 
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
def send_log(message):
    os.makedirs("logs", exist_ok=True)
    filename = f"logs/{current_datetime}.log"
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write(message)
    else:
        with open(filename, 'a') as f:
            f.write(f"\n{message}")


#creates log folder for log files
def log_exists(folder='logs'):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
  

#VALIDATION FUCNTIONS---------------
#checks if individual entries in the database have the correct data types and values
#in-put: <dictionary> entry, <string> consumption_history/household_info/fridge
#output: <boolean> True if the entry is valid, <string> error message if the entry is invalid else None

# Validate individual database records
def check_data(record: dict, table: str) -> tuple[bool, str | None]:
    # Check table and record structure
    if table not in FILE_STRUCTURE:
        return False, f"Unknown table: {table}"
    if not isinstance(record, dict):
        return False, "Record must be a dictionary"
    expected_keys = set(FILE_STRUCTURE[table].split(","))
    if set(record.keys()) != expected_keys:
        return False, "Record contains missing or unexpected fields"
    
    # Validate stored quantity precision
    def check_quantity(value):
        if type(value) not in (int, float):
            return False
        try:
            return Decimal(str(value)) == Decimal(str(normalize_quantity(value)))
        except ValueError:
            return False

    # Check string values and text length validation to the database
    def check_string(value, max_length, allow_blank=False):
        return (isinstance(value, str) and len(value) <= max_length and (allow_blank or bool(value.strip())))

    # Check units
    def check_unit(value):
        return isinstance(value, str) and value in ("kg", "g", "l", "ml", "pcs")

    # Check real calendar dates, including leap years
    def check_date(value, allow_blank=False):
        if not isinstance(value, str):
            return False
        if allow_blank and value == "":
            return True
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False

    # consumption history validation
    if table == "consumption_history":
        days = record["Date_Range"]
        if type(days) is not int or not 1 <= days <= 365:
            return False, "Date_Range must be an integer between 1 and 365"
        if not check_string(record["Item_Name"], MAX_ITEM_NAME_LENGTH):
            return False, "Item_Name must be a non-empty string"
        if not check_quantity(record["Quantity"]):
            return False, "Quantity must be a non-negative number"
        if not check_string(record["Remarks"], MAX_REMARKS_LENGTH, allow_blank=True):
            return False, "Remarks must be a string (max 500 characters)"

    # household info validation
    elif table == "household_info":
        if type(record["Person_ID"]) is not int or record["Person_ID"] < 1:
            return False, "Person_ID must be a positive integer"
        if not check_string(record["Name"], MAX_PERSON_NAME_LENGTH):
            return False, "Name must be a non-empty string (max 50 characters)"
        if type(record["Age"]) is not int or not 1 <= record["Age"] <= 120:
            return False, "Age must be an integer between 1 and 120"
        if record["Gender"] not in ("Male", "Female"):
            return False, "Gender must be Male or Female"
        if not check_string(record["Dietary_Restriction"], MAX_DIETARY_LENGTH, allow_blank=True):
            return False, "Dietary_Restriction must be a string (max 200 characters)"

    # fridge stock validation
    elif table == "fridge":
        if not check_string(record["Item_Name"], MAX_ITEM_NAME_LENGTH):
            return False, "Item_Name must be a non-empty string (max 50 characters)"
        if not check_quantity(record["Quantity"]) or record["Quantity"] == 0:
            return False, "Fridge Quantity must be greater than 0"
        if not check_date(record["Purchase_Date"], allow_blank=True):
            return False, "Invalid Purchase_Date, expected YYYY-MM-DD or blank"
        if not check_date(record["Expiry_Date"]):
            return False, "Invalid Expiry_Date, expected YYYY-MM-DD"
        if record["Purchase_Date"] != "":
            if date.fromisoformat(record["Purchase_Date"]) > date.fromisoformat(record["Expiry_Date"]):
                return False, "Purchase_Date cannot be after Expiry_Date"
        if not check_string(record["Remarks"], MAX_REMARKS_LENGTH, allow_blank=True):
            return False, "Remarks must be a string (max 500 characters)"
    # unit and qty validation
    if table in ("consumption_history", "fridge"):
        if not check_unit(record["Unit"]):
            return False, "Unit must be kg, g, l, ml or pcs"
        quantity = record["Quantity"]
        if record["Unit"] == "pcs":
            if not float(quantity).is_integer():
                return False, "Quantity in pcs must be a whole number"
    return True, None

#checks if the database dictionary has all the required tables and entries, and if the entries have the correct data types
#in-put: <dictionary> database
#output: <dictionary> database with problematic entries removed, <list> errors encountered during checking
def check_database(database):
    errors = []
    for table in FILE_STRUCTURE:
        if table not in database:
            errors.append(f"Missing table '{table}' in the database.")
            database[table] = []  # Initialize missing tables with an empty list
            continue
        # Iterate over a copy to prevent skipping entries when removing invalid records
        for entry in database[table][:]:
            if not isinstance(entry, dict):
                errors.append(f"Invalid entry in table '{table}': {entry}. Expected a dictionary.")
                database[table].remove(entry)  # Remove invalid entries
                continue

            #check if all expected keys are present in the entry
            expected_keys = FILE_STRUCTURE[table].split(',')
            missing_key=False
            for key in expected_keys:
                if key not in entry:
                    errors.append(f"Missing key '{key}' in entry {entry} of table '{table}'.")
                    missing_key = True
            if missing_key:
                database[table].remove(entry)  # Remove invalid entries
                continue

            # Validate the data types of each entry in the table
            check_result, error_message = check_data(entry, table)
            if not check_result:
                errors.append(f"Invalid data in table '{table}': {entry}. Error: {error_message}")
                database[table].remove(entry)  # Remove invalid entries
    return database, errors


#DB CREATION/SAVING FUCNTIONS---------------
#creates an empty database structure with the required tables and returns it
#in-put: None
#output: <dictionary> empty database structure
def create_empty_database():
    # Create an empty database structure
    return {file: [] for file in FILE_STRUCTURE}


#checks if the database folder and file exist, if not creates them
#in-put: <string> folder to check for json db
#output: None, Creates the database folder and file if they do not exist
def database_exists(folder='database'):
    # Implementation for creating the database
    if not os.path.exists(folder):
        send_log(f"[DATABASE] Database not found. Creating database folder: {folder}")
        os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, DB_FILENAME)
    if not os.path.exists(filename):
        send_log(f"[DATABASE] File {filename} not found. Creating file: {filename}")
        with open(filename, 'w') as f:
            json.dump(create_empty_database(), f)  # Create an empty JSON file with the required structure


#Loads the database from a JSON file in the specified folder and checks for errors
#in-put: <string> folder to load json db from
#output: <dictionary> database outputs out any errors encountered during loading
def load_database(folder='database'):
    errors = []
    filename = os.path.join(folder, DB_FILENAME)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                database = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"Error loading {filename}: {e}. Initializing with an empty database.")
                database = create_empty_database()  # Initialize with an empty database if there's an error
    else:
        errors.append(f"File {filename} not found. Initializing with an empty database.")
        database = create_empty_database()  # Initialize with an empty database if the file doesn't exist

    database, validation_errors = check_database(database)
    errors.extend(validation_errors)  # Add any validation errors to the errors list
    # Check existing records for conflicting units
    try:
        for table in ("fridge", "consumption_history"):
            for entry in database[table]:
                ensure_item_unit(database, entry["Item_Name"],entry["Unit"] )
    except ValueError as error:
        raise SystemExit(f"Database unit conflict: {error}") from error

    if not errors:
        send_log(f"[DATABASE] Database loaded successfully.")
        return True, database
    else:
        send_log(f"[DATABASE] ****************** Errors encountered during loading ******************")
        for error in errors:
            send_log(f"[DATABASE] {error}")  # log any errors encountered during loading
        send_log(f"[DATABASE] ***********************************************************************")
        return False, database
    
#saves the database dictionary to a JSON file in the specified folder
#in-put: <dictionary> database, <string> folder to save json db to
#output: None
def save_database(database, folder='database'):
    # Implementation for saving the database
    filename = os.path.join(folder, DB_FILENAME)
    with open(filename, 'w') as f:
        f.write(json.dumps(database, indent=2))
    send_log(f"[DATABASE] Database saved successfully to {filename}.")

# Ensure the same item uses one unit across the database
def ensure_item_unit(database, item_name, unit):
    name = item_name.strip().casefold()
    unit = unit.strip().lower()
    for table in ("fridge", "consumption_history"):
        for entry in database.get(table, []):
            existing_name = entry["Item_Name"].strip().casefold()
            existing_unit = entry["Unit"].strip().lower()
            if existing_name == name and existing_unit != unit:
                raise ValueError(f"{item_name} uses both {existing_unit} and {unit}.\nCorrect the existing data before proceeding.")

def shift_calendar_years(value, years):
    target_year = value.year + years
    try:
        return value.replace(year=target_year)
    except ValueError:
        return value.replace(year=target_year, month=2, day=28)
#DB CRUD FUCNTIONS---------------
#returns the total quantity of the item in the fridge and consumption_history tables
#in-put: <dictionary> database, <string> item_name
#output: <integer> total quantity of the item in the fridge and consumption_history tables
def get_all_fridge_quantity(database, item_name, include_expired=True):
    total_quantity = 0
    for entry in database.get("fridge", []):
        # Match item names (case insensitive)
        if entry["Item_Name"].strip().casefold() != item_name.strip().casefold():
            continue
        # Exclude expired items if requested
        if not include_expired:
            expiry_date = date.fromisoformat(entry["Expiry_Date"])
            if expiry_date < date.today():
                continue
        total_quantity += entry["Quantity"]
    return total_quantity

#adds dictionary item to the household_info table in the database dictionary
#in-put: [{"Person_ID": <integer>, "Name": "<string>", "Age": <integer>, "Gender": "<string>", "Dietary_Restriction": "<string>"},...]
#output: <dictionary> database 
def update_household_info(database, update_list):
    for item in update_list:
        check_result, error_message = check_data(item, 'household_info')
        if not check_result:
            send_log(f"[DATABASE] Invalid data being added to  household_info: {item}. Error: {error_message}")
            continue  # Skip invalid entries
        database.get('household_info', []).append(item)  # Append each item in the update list to the household_info table
    return database


#adds dictionary item to the consumption_history table in the database dictionary
#in-put: [{"Item_Name": "<string>", "Quantity": <float>, "Unit": "<string>", "Date_Range": <integer>, "Remarks": "<string>"},...]
#output: <dictionary> database 
def update_consumption_history(database, update_list):
    for item in update_list:
        check_result, error_message = check_data(item, 'consumption_history')
        if not check_result:
            send_log(f"[DATABASE] Invalid data being added to consumption_history: {item}. Error: {error_message}")
            continue  # Skip invalid entries
        ensure_item_unit(database, item["Item_Name"], item["Unit"])
        database.get('consumption_history', []).append(item)  # Append each item in the update list to the consumption_history table
    return database


#adds dictionary item to the fridge table in the database dictionary
#in-put: [{"Item_Name": "<string>", "Quantity": <integer>, "Unit": "<string>", "Purchase_Date": "<YYYY-MM-DD>", "Expiry_Date": "<YYYY-MM-DD>", "Remarks": "<string>"},...]
#output: <dictionary> database 
def add_to_fridge(database, update_list):
    for item in update_list:
        check_result, error_message = check_data(item, 'fridge')
        if not check_result:
            send_log(f"[DATABASE] Invalid data being added in fridge: {item}. Error: {error_message}")
            continue  # Skip invalid entries
        ensure_item_unit(database, item["Item_Name"], item["Unit"])
        database.get('fridge', []).append(item)  # Append each item in the update list to the fridge table
    return database


#removes the quantity from the fridge table FIFO order based on the item name and quantity specified in the update_list
#in-put: [{"Item_Name": "<string>", "Quantity": <integer>,...},...]
#output: <dictionary> database  
def remove_from_fridge(database, update_list):
    fridge = database.get("fridge", [])
    planned_removals = {}

    # Validate all removals before modifying inventory list
    for item in update_list:
        name = item["Item_Name"].strip().casefold()
        unit = item["Unit"].strip().lower()
        amount = item["Quantity"]

        if type(amount) not in (int, float):
            raise ValueError(f"Invalid consumption quantity for {item['Item_Name']}.")
        
        amount_decimal = Decimal(str(amount))
        if ( not amount_decimal.is_finite() or amount_decimal != Decimal(str(normalize_quantity(amount)))):
            raise ValueError(f"Invalid consumption precision for {item['Item_Name']}.")

        if unit == "pcs" and amount_decimal != amount_decimal.to_integral_value():
            raise ValueError(f"{item['Item_Name']}: pcs must be whole numbers.")

        key = (name, unit)
        planned_removals[key] = (planned_removals.get(key, Decimal("0")) + amount_decimal)

    # reject consumption exceeding available stock
    for (name, unit), amount in planned_removals.items():
        available = sum(
            (
                Decimal(str(entry["Quantity"]))
                for entry in fridge
                if entry["Item_Name"].strip().casefold() == name
                and entry["Unit"].strip().lower() == unit
            ),
            Decimal("0")
        )
        if amount > available:
            raise ValueError(f"Cannot consume {amount} {unit} of {name};\nonly {available} available.")
    # Perform precise subtraction
    for (name, unit), amount_to_remove in planned_removals.items():
        if amount_to_remove == 0:
            continue
        for entry in fridge[:]:
            if (entry["Item_Name"].strip().casefold() == name and entry["Unit"].strip().lower() == unit):
                available = Decimal(str(entry["Quantity"]))
                consumed = min(available, amount_to_remove)
                remaining = available - consumed
                amount_to_remove -= consumed

                if remaining == 0:
                    fridge.remove(entry)
                else:
                    entry["Quantity"] = normalize_quantity(remaining)
                if amount_to_remove == 0:
                    break
    return database