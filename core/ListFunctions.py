from abc import ABC, abstractmethod


class ListFunctions(ABC):
    """Interface: operations every item container (cart, recommendation list, fridge) must support."""

    @abstractmethod
    def add_item(self, item) -> None:
        pass

    @abstractmethod
    def remove_item(self, item) -> None:
        pass

    @abstractmethod
    def get_items(self) -> list:
        pass

    @abstractmethod
    def get_item_at(self, index: int):
        pass

