from abc import ABC, abstractmethod


class ItemFunctions(ABC):
    """Interface: operations every single grocery/fridge item must support."""

    @abstractmethod
    def set_quantity(self, amount: float) -> None:
        pass
