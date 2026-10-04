from DB_manager import check_database, load_database, save_database

check_database()  # Ensure the database folder and file exist
database = load_database('sample_database')  # Load the database into memory
#print(database)  # Print the loaded database for verification











save_database(database, 'database')  # Save the database to the specified folder