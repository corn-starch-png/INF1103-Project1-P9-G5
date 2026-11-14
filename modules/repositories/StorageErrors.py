"""
Technically each class should have each own folder, but the purpose of the classes here is 
to give more relevant error messages, as there is no logic in each class, we decided to put them all in one file
here so that the modules folder will be less cluttered
"""
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
