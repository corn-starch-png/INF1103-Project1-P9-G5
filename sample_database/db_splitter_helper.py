import os
import json
"""
Use this script to split the database into three separate files, one for each repository. 
This is a one-time operation, so it is not part of the main program.
"""

folder = "sample_database" #CHANGE TO YOUR DATABASE FOLDER (DEFAULT: database)
try:
    with open(os.path.join(folder, "db.json"), encoding="utf-8") as f:
        data = json.load(f)
        with open(os.path.join(folder, "fridge.json"), "w", encoding="utf-8") as f1:
            json.dump(data["fridge"], f1, indent=4, ensure_ascii=False)
        with open(os.path.join(folder, "household.json"), "w", encoding="utf-8") as f2:
            json.dump(data["household_info"], f2, indent=4, ensure_ascii=False)
        with open(os.path.join(folder, "consumption_history.json"), "w", encoding="utf-8") as f3:
            json.dump(data["consumption_history"], f3, indent=4, ensure_ascii=False)
except (json.JSONDecodeError, OSError) as e:
    print(f"Could not read db.json: {e}")
    exit(1)