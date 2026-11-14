# Scope cloud operations to one household and reject stale updates.
import os
from copy import deepcopy
from dotenv import load_dotenv
from dns.exception import DNSException
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import ConfigurationError, ConnectionFailure, DuplicateKeyError, OperationFailure
from .RepositoryFunctions import RepositoryFunctions
from .HouseholdDocument import HouseholdDocument as Doc
from .StorageErrors import CloudUnavailable, HouseholdNotFound, SaveConflict, CloudOperationError

class MongoDBRepository(RepositoryFunctions):
    # Inject a collection for tests; validate configuration for real connections.
    def __init__(self, database_name=None, collection=None):
        self.client = None
        if collection is not None:
            self.collection = collection
            return
        load_dotenv()
        uri = os.getenv("MONGODB_URI")
        name = database_name or os.getenv("MONGODB_DATABASE")
        if not uri or not name:
            raise CloudUnavailable("MONGODB_URI and MONGODB_DATABASE must be configured.")
        try:
            # SRV discovery can fail during construction, before ping is reached.
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000,
                                      connectTimeoutMS=5000, socketTimeoutMS=10000, tz_aware=True)
            self.client.admin.command("ping")
        except ConfigurationError as error:
            self.close()
            # PyMongo wraps DNS lookup failures; preserve offline recovery without hiding invalid settings.
            if isinstance(error.__cause__, DNSException):
                raise CloudUnavailable("MongoDB address lookup failed. Check your internet connection and DNS settings.") from error
            raise CloudOperationError("MongoDB configuration is invalid. Check the connection settings; local data was retained.") from error
        except ConnectionFailure as error:
            self.close()
            raise CloudUnavailable("MongoDB cannot be reached.") from error
        # Authentication and authorization failures are recoverable application errors.
        except OperationFailure as error:
            self.close()
            raise CloudOperationError("MongoDB rejected access. Check database credentials and permissions; local data was retained.") from error
        self.database = self.client[name]
        self.collection = self.database["households"]

    # A confirmed missing ID must not fall back to a cached household.
    def load(self, household_id):
        household_id = Doc.normalize_id(household_id)
        try:
            document = self.collection.find_one({"_id": household_id})
        except ConnectionFailure as error:
            raise CloudUnavailable("MongoDB cannot be reached.") from error
        # Surface server errors through the session recovery menu, preserving the draft.
        except OperationFailure as error:
            raise CloudOperationError("MongoDB rejected the read. Check database permissions; local data was retained.") from error
        if document is None:
            raise HouseholdNotFound("Household ID was not found in MongoDB.")
        return Doc.from_cloud(document)

    # Retry an identical insertion safely after an uncertain network response.
    def create(self, document):
        Doc.size(document)
        try:
            self.collection.insert_one(Doc.to_cloud(document))
        except DuplicateKeyError:
            existing = self.load(document["_id"])
            if existing == document:
                return existing
            # An uncertain prior insertion may already have received another user's edits.
            if existing["created_at"] == document["created_at"]:
                raise SaveConflict("Previously created household has changed; review the draft before reloading.")
            raise
        except ConnectionFailure as error:
            raise CloudUnavailable("Creation could not be confirmed; retain the draft for retry.") from error
        # Failed registration remains locally recoverable.
        except OperationFailure as error:
            raise CloudOperationError("MongoDB rejected creation. Check database write permissions; the local draft was retained.") from error
        return deepcopy(document)

    # Save all arrays atomically using the originally loaded version, with no upsert.
    def save(self, document, expected_version):
        if document["version"] != expected_version:
            raise ValueError("Draft must retain its original cloud version.")
        Doc.size(document)
        try:
            updated = self.collection.find_one_and_update(
                {"_id": document["_id"], "version": expected_version},
                {"$set": Doc.editable(document), "$inc": {"version": 1},
                 "$currentDate": {"updated_at": True}},
                upsert=False, return_document=ReturnDocument.AFTER)
        except ConnectionFailure as error:
            raise CloudUnavailable("Save outcome is unknown; the local draft is preserved.") from error
        # Do not confuse authorization or server rejection with a successful offline save.
        except OperationFailure as error:
            raise CloudOperationError("MongoDB rejected the save. Check database write permissions; the local draft was retained.") from error
        if updated is None:
            raise SaveConflict("The cloud data has changed since you loaded it. Your changes have not been synced.\nReview the differences, then choose whether to keep your local data or use the cloud data.")
        return Doc.from_cloud(updated)

    # Release sockets explicitly for command line migration and long-running callers.
    def close(self):
        if self.client is not None:
            self.client.close()
