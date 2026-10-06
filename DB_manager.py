import os
import json

DB_FILENAME = 'db.json'
FILE_STRUCTURE = {
    'consumption_history': 'Date_Range,Item_Name,Quantity,Unit,Remarks',
    'household_info': 'Person_ID,Age,Gender,Dietary_Restriction',
    'fridge': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date',
    'fridge_history': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date'
}
KCAL_TABLE={1: {'Male': 880, 'Female': 810}, 2: {'Male': 1080, 'Female': 1000}, 3: {'Male': 1160, 'Female': 1070}, 4: {'Male': 1310, 'Female': 1190}, 5: {'Male': 1440, 'Female': 1320}, 6: {'Male': 1550, 'Female': 1420}, 7: {'Male': 1600, 'Female': 1500}, 8: {'Male': 1740, 'Female': 1620}, 9: {'Male': 1940, 'Female': 1760}, 10: {'Male': 2110, 'Female': 1910}, 11: {'Male': 2280, 'Female': 2070}, 12: {'Male': 2530, 'Female': 2230}, 13: {'Male': 2740, 'Female': 2310}, 14: {'Male': 2920, 'Female': 2360}, 15: {'Male': 3030, 'Female': 2390}, 16: {'Male': 3120, 'Female': 2400}, 17: {'Male': 3180, 'Female': 2400}, 18: {'Male': 3230, 'Female': 2410}, 19: {'Male': 2700, 'Female': 2070}, 30: {'Male': 2590, 'Female': 2035}, 60: {'Male': 2235, 'Female': 1865}}


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
    def check_unit(value):
        valid_units = ['kg', 'g', 'L', 'ml', 'pcs', 'carton']
        return value in valid_units
    def check_date(value):
        # Check if the date is in the format YYYY-MM-DD
        try:
            year, month, day = map(int, value.split('-'))
            return 1 <= month <= 12 and 1 <= day <= 31
        except ValueError:
            return False
    def check_gender(value):
        valid_genders = ['Male', 'Female', 'Other']
        return value in valid_genders
    #TODO refactor function for new data structure, check if the data is valid for the given table
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

    elif table == 'household_info' and data_length == 4:
        # Check if Person_ID and Age is an integer
        if not check_integer(record["Person_ID"]):
            return False, "Person_ID must be an integer"
        if not check_integer(record["Age"]):
            return False, "Age must be an integer"
        # check if Gender is valid
        if not check_gender(record["Gender"]):
            return False, "Invalid Gender, must be either: ['Male', 'Female', 'Other']"
        return True, None
        
    elif (table == 'fridge' or table == 'fridge_history') and data_length == 5:
        # Check if Quantity can be converted to float
        if not check_float(record["Quantity"]):
            return False, "Quantity must be a number"
        #check if Unit is valid
        if not check_unit(record["Unit"]):
            return False, "Invalid Unit."
        #check if Purchase_Date and Expiry_Date are valid dates
        if not check_date(record["Purchase_Date"]):
            return False, "Invalid Purchase_Date format, must be YYYY-MM-DD"
        if not check_date(record["Expiry_Date"]):
            return False, "Invalid Expiry_Date format, must be YYYY-MM-DD"
        return True, None
        
    else:
        return False, "Data length is incorrect"


def check_database(database):
    errors = []
    for table in FILE_STRUCTURE:
        if table not in database:
            errors.append(f"Missing table '{table}' in the database.")
            database[table] = []  # Initialize missing tables with an empty list
            continue
        for entry in database[table]:
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


def create_empty_database():
    # Create an empty database structure
    return {file: [] for file in FILE_STRUCTURE}


def database_exists(folder='database'):
    # Implementation for creating the database
    if not os.path.exists(folder):
        print(f"Database not found. Creating database folder: {folder}")
        os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, DB_FILENAME)
    if not os.path.exists(filename):
        print(f"File {filename} not found. Creating file: {filename}")
        with open(filename, 'w') as f:
            json.dump(create_empty_database(), f)  # Create an empty JSON file with the required structure


def load_database(folder='database'):
    
    # Implementation for loading the database
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
        print("Database loaded successfully.")
    else:
        print("****************** Errors encountered during loading ******************")
        for error in errors:
            print(error)  # Print any errors encountered during loading
        print("***********************************************************************")
    return database


def save_database(database, folder='database'):
    # Implementation for saving the database
    filename = os.path.join(folder, DB_FILENAME)
    with open(filename, 'w') as f:
        json.dump(database, f)
    print(f"Database saved successfully to {filename}.")






#--------------------------------------for testing----------------------------------------------
#temporary code to load the kcal.csv file into a dictionary for testing purposes
def load_kcal_database():
    cal_db={}
    with open('sample_database/kcal.csv', 'r') as f:
        header = f.readline()  # Skip the header line
        column_names = header.replace('\n', '').split(',')  # Split the header into individual column names
        for line in f:
            cal_values = line.strip().split(',')  # Split each line into individual values
            cal_values[1] = int(cal_values[1]) 
            cal_values[2] = int(cal_values[2]) 
            cal_db[int(cal_values[0])] = {column_names[i]: cal_values[i] for i in range(1, len(column_names))}  # Create a dictionary for each food item with its corresponding values
    print(cal_db)  # Print the entire kcal database dictionary for verification
    return cal_db

'''
database_exists()  # Ensure the database folder and file exist
database = load_database("sample_database")  # Load the database into memory
save_database(database, 'database')  # Save the database to the specified folder
'''
load_kcal_database()  # Load the kcal database for testing purposes

