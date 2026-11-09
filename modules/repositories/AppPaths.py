from pathlib import Path

# Define shared application storage paths relative to the project root.
class AppPaths:
    # Locate the project root from modules/repositories/AppPaths.py.
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    # Keep generated database files and logs together under app_data.
    APP_DATA_DIR = PROJECT_ROOT / "app_data"
    DATABASE_DIR = APP_DATA_DIR / "database"
    LOGS_DIR = APP_DATA_DIR / "logs"

    # Track locally saved changes that still need uploading to MongoDB.
    OFFLINE_MARKER = DATABASE_DIR / ".offline_changes"