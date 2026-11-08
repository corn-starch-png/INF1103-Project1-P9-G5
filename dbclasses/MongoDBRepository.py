import os

from dotenv import load_dotenv
from pymongo import MongoClient

from dbclasses.RepositoryFunctions import RepositoryFunctions
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory

load_dotenv()


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
            serverSelectionTimeoutMS=5000
        )

        # Verify the connection (raises if Atlas is unreachable)
        self.__client.admin.command("ping")

        self.__database = self.__client[database_name]

        # Map MongoDB collections to existing classes
        self.__stores = {
            "fridge": Fridge(),
            "household": Household(),
            "consumption_history": ConsumptionHistory(),
        }

    def load(self):
        """Load data from MongoDB Atlas into existing objects.
        Returns (errors, stores). Connection errors are NOT caught here,
        so main.py can fall back to local JSON."""
        errors = []

        for collection_name, store in self.__stores.items():
            rows = list(
                self.__database[collection_name].find({}, {"_id": 0})
            )
            errors.extend(store.load_dicts(rows))

        return errors, self.__stores

    def save(self) -> None:
        """Save existing objects into MongoDB Atlas."""

        for collection_name, store in self.__stores.items():
            collection = self.__database[collection_name]

            rows = store.to_dicts()

            # WARNING: This replaces all documents in the collection,
            # so avoid editing at the same time as a teammate.
            collection.delete_many({})

            if rows:
                # Insert copies so PyMongo doesn't add "_id" to your own dicts
                collection.insert_many([dict(r) for r in rows])

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.__client.close()
