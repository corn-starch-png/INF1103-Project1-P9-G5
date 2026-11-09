from abc import ABC, abstractmethod

class AIProvider(ABC):
    def check_connection(self) -> tuple:
        return True, "AI provider ready."
    @abstractmethod
    def generate(self, prompt: str, schema: dict, grocery_list: list, validator) -> tuple:
        pass