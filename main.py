from DB_manager import create_database, load_database, save_database

create_database()  # Create the database if it doesn't exist
database = load_database('sample_database')  # Load the database into memory
#print(database)  # Print the loaded database for verification











save_database(database, 'database')  # Save the database to the specified folder