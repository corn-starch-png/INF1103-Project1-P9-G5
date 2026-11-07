
import os

from pymongo import MongoClient

from dbclasses.RepositoryFunctions import RepositoryFunctions
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory


class MongoDBRepository(RepositoryFunctions):

    def __init__(self, database_name=None):
        # Get MongoDB Atlas connection details
        uri = os.getenv("MONGODB_URI")
        database_name = database_name or os.getenv("MONGODB_DATABASE")

        if not uri:
            raise ValueError("MONGODB_URI is missing")

        if not database_name:
            raise ValueError("MONGODB_DATABASE is missing")

        # Connect to MongoDB Atlas
        self.__client = MongoClient(
            uri,
            serverSelectionTimeoutMS=10000
        )

        # Verify the connection
        self.__client.admin.command("ping")

        self.__database = self.__client[database_name]

        # Map MongoDB collections to existing classes
        self.__stores = {
            "fridge": Fridge(),
            "household": Household(),
            "consumption_history": ConsumptionHistory(),
        }

    def load(self) -> list:
        """Load data from MongoDB Atlas into existing objects."""
        errors = []

        for collection_name, store in self.__stores.items():
            try:
                collection = self.__database[collection_name]

                rows = list(
                    collection.find({}, {"_id": 0})
                )

                errors.extend(store.load_dicts(rows))

            except Exception as e:
                errors.append(
                    f"Could not load {collection_name}: {e}"
                )

        return errors, self.__stores

    def save(self) -> None:
        """Save existing objects into MongoDB Atlas."""

        for collection_name, store in self.__stores.items():
            collection = self.__database[collection_name]

            rows = store.to_dicts()

            # WARNING: This replaces all documents in the collection.
            collection.delete_many({})

            if rows:
                collection.insert_many(rows)

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.__client.close()
