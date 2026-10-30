from abc import ABC, abstractmethod

#region Abstract AI Provider
class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, schema: dict, grocery_list: list, validator) -> tuple:
        pass
#endregion