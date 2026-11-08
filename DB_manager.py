from datetime import datetime
import os

class DB_manager():
    @staticmethod
    def load_database(repository):
        errors, data_bundle = repository.load()
        return errors, data_bundle
    
    @staticmethod
    def save_database(repository):
        repository.save()

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