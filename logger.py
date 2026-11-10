# logger_setup.py
from datetime import datetime
import os
from modules.repositories.AppPaths import AppPaths

class Logger:
    def __init__(self, logs_dir=AppPaths.LOGS_DIR):
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Created ONCE when this module is first imported during program startup
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = os.path.join(self.logs_dir, f"{current_datetime}.log")

    def send_log(self, message: str):
        file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        mode = 'a' if file_exists else 'w'
        
        with open(self.filename, mode, encoding='utf-8') as f:
            if file_exists:
                f.write(f"\n{message}")
            else:
                f.write(message)

# Initialize a single global logger instance for the entire application
app_logger = Logger()