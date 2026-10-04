import os
import json

db_filename = 'db.json'
file_structure = {
    'consumption_history': 'Date_Range,Item_Name,Quantity,Unit,Remarks',
    'household_info': 'Person_ID,Age,Gender,Dietary_Restriction',
    'stock': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date'
}


def check_data(text, filename):
    #TODO refactor function for new data structure, check if the data is valid for the given filename
    data_length = len(text)
    valid_units = ['kg', 'g', 'L', 'ml', 'pcs', 'carton']
    if filename == 'consumption_history.csv' and data_length == 5:
        # Check if Quantity can be converted to float
        try:
            float(text[2])  
        except ValueError:
            return False, "Quantity must be a number"
        # Check if Unit is valid
        if text[3] in valid_units:
            return True, None
        else:
            return False, "Invalid Unit."
        
    elif filename == 'household_info.csv' and data_length == 4:
        # Check if Person_ID and Age is an integer
        try:
            int(text[0])  
            int(text[1])  
        except ValueError:
            return False, "Person_ID and Age must be numbers"
        # check if Gender is valid
        if text[2] in ['Male', 'Female', 'Other']:
            return True, None
        else:
            return False, "Invalid Gender, must be either: ['Male', 'Female', 'Other']"
        
    elif filename == 'stock.csv' and data_length == 5:
        # Check if Quantity can be converted to float
        try:
            float(text[1])  
        except ValueError:
            return False, "Quantity must be a number"
        #check if Unit is valid
        if text[2] in valid_units:
            return True, None
        else:
            return False, "Invalid Unit."
        
    else:
        return False, "Data length is incorrect"


def create_empty_database():
    # Create an empty database structure
    return {file: [] for file in file_structure}


def check_database(folder='database'):
    # Implementation for creating the database
    if not os.path.exists(folder):
        print(f"Database not found. Creating database folder: {folder}")
        os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, db_filename)
    if not os.path.exists(filename):
        print(f"File {filename} not found. Creating file: {filename}")
        with open(filename, 'w') as f:
            json.dump(create_empty_database(), f)  # Create an empty JSON file with the required structure


def load_database(folder='database'):
    

    # Implementation for loading the database
    errors = []
    filename = os.path.join(folder, db_filename)
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

    #TODO: Add validation for the loaded data to ensure it matches the expected structure and types

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
    filename = os.path.join(folder, db_filename)
    with open(filename, 'w') as f:
        json.dump(database, f)
    print(f"Database saved successfully to {filename}.")

#temporary code to load the kcal.csv file into a dictionary for testing purposes
def load_kcal_database():
    cal_db={}
    with open('sample_database/kcal.csv', 'r') as f:
        header = f.readline()  # Skip the header line
        print(header.strip())  # Print the header of the kcal.csv file
        column_names = header.replace('\n', '').split(',')  # Split the header into individual column names
        for line in f:
            print(line.strip())  # Print each line of the kcal.csv file
            cal_values = line.strip().split(',')  # Split each line into individual values
            cal_values[1] = int(cal_values[1]) 
            cal_values[2] = int(cal_values[2]) 
            cal_db[cal_values[0]] = {column_names[i]: cal_values[i] for i in range(1, len(column_names))}  # Create a dictionary for each food item with its corresponding values
    print(cal_db)  # Print the entire kcal database dictionary for verification
    return cal_db
'''
check_database()  # Ensure the database folder and file exist
database = load_database("sample_database")  # Load the database into memory
save_database(database, 'database')  # Save the database to the specified folder
'''


