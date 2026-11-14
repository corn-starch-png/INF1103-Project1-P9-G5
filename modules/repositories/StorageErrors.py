# Distinguish stale edits, absent households, and connectivity failures.
class SaveConflict(RuntimeError):
    pass

class LocalConflict(SaveConflict):
    pass

class HouseholdNotFound(RuntimeError):
    pass

class CloudUnavailable(RuntimeError):
    pass

# Report server permission/configuration failures without pretending the save succeeded.
class CloudOperationError(RuntimeError):
    pass
