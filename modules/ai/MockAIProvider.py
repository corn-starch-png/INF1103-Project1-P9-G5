from .AIProvider import AIProvider

class MockAIProvider(AIProvider):
    def __init__(self, sample_response: str) -> None:
        self._sample_response = sample_response
    def generate(self, prompt: str, schema: dict, grocery_list: list, validator) -> tuple:
        result, error = validator.process_ai_response(self._sample_response)
        if error:
            return None, error
        if not validator.check_ai_output(result["Recommendations_List"], grocery_list):
            return None, "AI recommendations do not match the original grocery list:\nitem names, planned quantities, units or order."
        return result, None
