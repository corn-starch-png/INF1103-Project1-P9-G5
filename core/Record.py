from abc import ABC, abstractmethod


class Record(ABC):
    """Abstract base class for every entity that can be validated and stored."""

    @abstractmethod
    def validate(self) -> bool:
        """Return True if the record's data is valid."""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Return the record as a dictionary (for saving to the database)."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict):
        """Build a record from a dictionary (for loading from the database)."""
        pass
