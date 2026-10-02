import os

files = {
    'consumption_history.csv': 'Date_Range,Item_Name,Quantity,Unit,Remarks',
    'household_info.csv': 'Person_ID,Age,Gender,Dietary_Restriction',
    'stock.csv': 'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date'
}


def check_data(text, filename):
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


def create_database(folder='database'):
    # Implementation for creating the database
    if not os.path.exists(folder):
        print(f"Database not found. Creating database folder: {folder}")
        os.makedirs(folder, exist_ok=True)
    for file in files:
        filename = os.path.join(folder, file)
        if not os.path.exists(filename):
            print(f"File {filename} not found. Creating file: {filename}")
            with open(filename, 'w') as f:
                f.write(files[file] + '\n')  # Write the header to each file


def load_database(folder='database'):
    def check_header(text):
        if text in files.values():
            return True
        return False
    

    # Implementation for loading the database
    database = {}
    errors = []
    for file in files:
        filename = os.path.join(folder, file)
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                header = f.readline().replace(' ', '').replace('\n', '')  # Read the header line
                if not check_header(header):
                    errors.append(f"Header mismatch in {file}: {header}")
                    header = files[file]
                
                file_data = []
                for line in f:
                    line = line.replace(' ', '').replace('\n', '').split(',')
                    is_valid, error_message = check_data(line, file)
                    if not is_valid:
                        errors.append(f"Invalid data {line} in {file}: {error_message}")
                        continue
                    file_data.append(dict(zip(header.split(','), line)))
                database[file[:-4]] = file_data
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
    for file, data in database.items():
        filename = os.path.join(folder, f'{file}.csv')
        if data:
            header = data[0].keys()
            with open(filename, 'w') as f:
                f.write(','.join(header) + '\n')  # Write the header
                for row in data:
                    f.write(','.join(str(row[h]) for h in header) + '\n')  # Write each row

