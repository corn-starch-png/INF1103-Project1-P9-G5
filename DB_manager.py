import os



def create_database():
    # Implementation for creating the database
    folder, files = 'database', ['consumption_history.csv', 'household_info.csv', 'stock.csv']
    header = ['Date_Range,Item_Name,Quantity,Unit,Remarks',
              'Person_ID,Age,Gender,Dietary_Restriction',
              'Item_Name,Quantity,Unit,Purchase_Date,Expiry_Date']

    if not os.path.exists(folder):
        os.makedirs('database', exist_ok=True)
    for file in files:
        filename = os.path.join(folder, file)
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(header[files.index(file)] + '\n')  # Write the header to each file


def load_database(folder='database'):
    # Implementation for loading the database
    files = ['consumption_history.csv', 'household_info.csv', 'stock.csv']
    database = {}
    for file in files:
        filename = os.path.join(folder, file)
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                header = f.readline().replace(' ', '').replace('\n', '').split(',')  # Read the header line
                file_data = []
                for line in f:
                    line = line.replace(' ', '').replace('\n', '').split(',')
                    file_data.append(dict(zip(header, line)))
                database[file[:-4]] = file_data
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


create_database()  # Create the database if it doesn't exist
database = load_database('sample_database')  # Load the database into memory
save_database(database, 'database')  # Save the database to the specified folder