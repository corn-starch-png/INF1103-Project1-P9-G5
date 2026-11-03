from ioclasses.Prompt import Prompt


# Asks for a whole number between a minimum and maximum
class IntRangePrompt(Prompt):
    def __init__(self, question, min_value, max_value, error_message=None):
        super().__init__(question)
        self.__min = min_value
        self.__max = max_value
        self.__error_message = error_message

    def _validate(self, text):
        if text.isdecimal() and self.__min <= int(text) <= self.__max:
            return ""
        if self.__error_message is not None:
            return self.__error_message
        return f"Please enter a whole number between {self.__min} and {self.__max}."

    def _convert(self, text):
        return int(text)