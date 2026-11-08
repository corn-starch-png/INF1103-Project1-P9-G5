from ioclasses.Prompt import Prompt


# Asks until the user types one of the allowed options
class ChoicePrompt(Prompt):
    def __init__(self, question, options, error_message=None):
        super().__init__(question)
        self.__options = options
        self.__error_message = error_message

    def _validate(self, text):
        for option in self.__options:
            if text.lower() == option.lower():
                return ""
        if self.__error_message is not None:
            return self.__error_message
        return f"Please enter one of: {', '.join(self.__options)}."

    def _convert(self, text):
        return text.lower()