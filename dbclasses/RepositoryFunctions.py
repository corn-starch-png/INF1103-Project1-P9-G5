from abc import ABC, abstractmethod


class RepositoryFunctions(ABC):
    """Interface: operations every single repository must support."""

    @abstractmethod
    def load(self) -> list:
        pass

    @abstractmethod
    def save(self) -> None:
        pass
