from abc import ABC, abstractmethod


class RepositoryFunctions(ABC):
    """Cloud household contract; local cache storage has a separate responsibility."""

    # Require registration because persistence coordination creates offline households on sync.
    @abstractmethod
    def create(self, document):
        """Register a household and return its stored document; never overwrite an existing ID."""
        pass

    # Require explicit household scope for cloud reads.
    @abstractmethod
    def load(self, household_id):
        pass

    # Carry the draft and originally loaded version into the atomic save.
    @abstractmethod
    def save(self, document, expected_version):
        pass

    # Make resource cleanup part of every cloud repository implementation's contract.
    @abstractmethod
    def close(self):
        """Release resources owned by this repository."""
        pass
