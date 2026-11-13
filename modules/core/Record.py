from abc import ABC, abstractmethod
from uuid import uuid4


class Record(ABC):
    """Abstract base class for every entity that can be validated and stored."""

    # Keep storage identity separate from display positions and AI dictionaries.
    @property
    def storage_id(self):
        if not hasattr(self, "_storage_id"):
            self._storage_id = uuid4().hex
        return self._storage_id

    # Restore an embedded record's ID without changing its business fields.
    def restore_storage_id(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Record ID must be a nonempty string.")
        self._storage_id = value

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
