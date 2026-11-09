from .Prompt import Prompt

# Asks for text. Rejects double quotes and backslashes 
# Blank answers are only allowed if allow_blank is True

class TextPrompt(Prompt):
    def __init__(self, question, allow_blank=False, max_length=None):
        super().__init__(question)
        self.__allow_blank = allow_blank
        self.__max_length = max_length

    def _validate(self, text):
        if '"' in text or "\\" in text:
            return "Please do not use double quotes or backslashes."
        if text == "" and not self.__allow_blank:
            return "This can't be empty."
        if self.__max_length is not None and len(text) > self.__max_length:
            return f"Please enter no more than {self.__max_length} characters."
        return ""

    def _convert(self, text):
        return text