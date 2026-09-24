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



create_database()  # Create the database if it doesn't exist