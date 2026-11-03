from abc import ABC, abstractmethod
 
 
class CanBeStored(ABC):
    """
    Interface: an object that can export its contents as a list of dictionaries
    and rebuild itself from one. A Repository only needs this interface, so it
    never has to know how a Fridge, Household or ConsumptionHistory stores its items.
    """
 
    @abstractmethod
    def to_dicts(self) -> list:
        """Return every stored item as a dictionary (ready to be written as JSON)."""
        pass
 
    @abstractmethod
    def load_dicts(self, rows: list) -> list:
        """
        Build items from the dictionaries in rows and add them to this object.
        Invalid rows are skipped. Returns a list of error messages, one per
        skipped row (an empty list means every row loaded).
        """
        pass