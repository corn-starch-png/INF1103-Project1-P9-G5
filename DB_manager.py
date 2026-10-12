import os
import json
from datetime import datetime


DB_FILENAME = 'db.json'
FILE_STRUCTURE = {
    'consumption_history': 'Date_Range,Item_Name,Quantity,Unit,Remarks',
    'household_info': 'Person_ID,Name,Age,Gender,Dietary_Restriction',
    'fridge': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date,Remarks'
}



#LOGGING FUNCTIONS--------------
#current_datetime used to generate log filename
#only used by send_log function 
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
def send_log(message):
    filename=f"logs/{current_datetime}.log"
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
def check_data(record, table):
    def check_integer(value):
        try:
            int(value)
            return True
        except ValueError:
            return False
    def check_float(value):
        try:
            float(value)
            return True
        except ValueError:
            return False
    def check_string(value):
        return isinstance(value, str)
    def check_unit(value):
        valid_units = ['kg', 'g', 'L', 'ml', 'pcs']
        if not isinstance(value, str):
            return False
        return value.strip().lower() in [unit.lower() for unit in valid_units]
    def check_date(value):
        # Check if the date is in the format YYYY-MM-DD
        try:
            year, month, day = map(int, value.split('-'))
            return 1 <= month <= 12 and 1 <= day <= 31
        except ValueError:
            return False
    def check_gender(value):
        valid_genders = ['Male', 'Female']
        return value in valid_genders
    
    
    data_length = len(record)
    if table == 'consumption_history' and data_length == 5:
        # Check if Date_Range is an integer
        if not check_integer(record["Date_Range"]):
            return False, "Date_Range must be an integer"
        # Check if Quantity can be converted to float
        if not check_float(record["Quantity"]):
            return False, "Quantity must be a number"
        # Check if Unit is valid
        if not check_unit(record["Unit"]):
            return False, "Invalid Unit"
        return True, None

    elif table == 'household_info' and data_length == 5:
        # Check if Person_ID and Age is an integer
        if not check_integer(record["Person_ID"]):
            return False, "Person_ID must be an integer"
        if not check_integer(record["Age"]):
            return False, "Age must be an integer"
        # check if Gender is valid
        if not check_gender(record["Gender"]):
            return False, "Invalid Gender, must be either: ['Male', 'Female']"
        return True, None
        
    elif table == 'fridge' and data_length == 6:
        # Check if Quantity can be converted to float
        if not check_float(record["Quantity"]):
            return False, "Quantity must be a number"
        #check if Unit is valid
        if not check_unit(record["Unit"]):
            return False, "Invalid Unit."
        #check if Purchase_Date and Expiry_Date are valid dates
        if not check_date(record["Purchase_Date"]) and record["Purchase_Date"] != "":
            return False, "Invalid Purchase_Date format, must be YYYY-MM-DD"
        if not check_date(record["Expiry_Date"]):
            return False, "Invalid Expiry_Date format, must be YYYY-MM-DD"
        if not check_string(record["Remarks"]):
            return False, "Invalid Remarks format, must be a string"
        return True, None
        
    else:
        return False, "Data length is incorrect"


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


#DB CRUD FUCNTIONS---------------
#returns the total quantity of the item in the fridge and consumption_history tables
#in-put: <dictionary> database, <string> item_name
#output: <integer> total quantity of the item in the fridge and consumption_history tables
def get_all_fridge_quantity(database, item_name):
    # Implementation for retrieving all quantities of a specific item from the fridge table
    total_quantity = 0
    for entry in database.get('fridge', []):
        if entry.get('Item_Name').lower() == item_name.lower():
            total_quantity += entry.get('Quantity')
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
        database.get('fridge', []).append(item)  # Append each item in the update list to the fridge table
    return database


#removes the quantity from the fridge table FIFO order based on the item name and quantity specified in the update_list
#in-put: [{"Item_Name": "<string>", "Quantity": <integer>,...},...]
#output: <dictionary> database  
def remove_from_fridge(database, update_list):  
    for item in update_list:
        amount_to_remove = item.get('Quantity', 0)
        for entry in database.get('fridge', []).copy():  # Use copy() to avoid modifying the list while iterating
            if entry.get('Item_Name').lower() == item.get('Item_Name').lower():
                if entry.get('Quantity') >= amount_to_remove:
                    entry['Quantity'] -= amount_to_remove
                    amount_to_remove = 0
                    if entry['Quantity'] == 0:
                        database.get('fridge', []).remove(entry)
                else:
                    amount_to_remove -= entry.get('Quantity')
                    database.get('fridge', []).remove(entry)
                if amount_to_remove == 0:
                    break
            

    return database 
