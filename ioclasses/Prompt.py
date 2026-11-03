from abc import ABC, abstractmethod



class Prompt(ABC):
    def __init__(self, question):
        self._question = question

    def ask(self):
        while True:
            text = input(self._question).strip()
            error = self._validate(text)
            if error == "":
                return self._convert(text)
            print(error)

    @abstractmethod
    def _validate(self, text):
        pass

    # Turn valid text into the value to return.
    @abstractmethod
    def _convert(self, text):
        pass