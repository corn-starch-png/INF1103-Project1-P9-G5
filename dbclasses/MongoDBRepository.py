import os
from urllib.parse import quote_plus

from pymongo import MongoClient

from dbclasses.RepositoryFunctions import RepositoryFunctions
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory


class MongoDBRepository(RepositoryFunctions):

    def __init__(
        self,
        fridge: Fridge,
        household: Household,
        history: ConsumptionHistory,
        database_name: str = "food_waste"
    ):
        # Get MongoDB credentials from environment variables
        username = os.getenv("MONGO_ROOT_USERNAME")
        password = os.getenv("MONGO_ROOT_PASSWORD")

        if not username or not password:
            raise ValueError("MongoDB credentials are missing")

        # Construct MongoDB connection URI
        uri = (
            f"mongodb://{quote_plus(username)}:"
            f"{quote_plus(password)}"
            "@mongo:27017/?authSource=admin"
        )

        # Connect to MongoDB
        self.__client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000
        )

        self.__database = self.__client[database_name]

        # Same injected objects as JsonRepository
        self.__stores = {
            "fridge": fridge,
            "household": household,
            "consumption_history": history,
        }

    def load(self) -> list:
        """Load data from MongoDB into the existing objects."""
        errors = []

        for collection_name, store in self.__stores.items():
            try:
                collection = self.__database[collection_name]

                rows = list(collection.find({}, {"_id": 0}))

                errors.extend(store.load_dicts(rows))

            except Exception as e:
                errors.append(
                    f"Could not load {collection_name}: {e}"
                )

        return errors

    def save(self) -> None:
        """Save the existing objects into MongoDB."""

        for collection_name, store in self.__stores.items():
            collection = self.__database[collection_name]

            rows = store.to_dicts()

            # Replace existing records with current data
            collection.delete_many({})

            if rows:
                collection.insert_many(rows)

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.__client.close()
