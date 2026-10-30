from abc import ABC, abstractmethod

#region Abstract AI Provider
class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, schema: dict, grocery_list: list, validator) -> tuple:
        pass
#endregion

#region OpenRouter Provider
class OpenRouterProvider(AIProvider):
    def __init__(self) -> None:
        self._client = None
        self._primary_model = None
        self._backup_model = None
        self._max_retries = None

    def generate(self, prompt: str, schema: dict, grocery_list: list, validator) -> tuple:
        from AI_manager import call_ai_api
        return call_ai_api(prompt, grocery_list)

    def check_api_conn(self) -> tuple:
        from AI_manager import check_api_conn
        return check_api_conn()

    def _create_ai_client(self):
        from AI_manager import create_ai_client
        return create_ai_client()

    def _get_ai_model(self, model_type: str) -> str:
        from AI_manager import get_ai_model
        return get_ai_model(model_type)

    def _get_ai_response_content(self, response: object) -> str:
        from AI_manager import get_ai_response_content
        return get_ai_response_content(response)

    def _handle_ai_exception(self, error: Exception) -> str:
        from AI_manager import handle_ai_exception
        return handle_ai_exception(error)

    def _should_retry_ai_error(self, error: Exception) -> bool:
        from AI_manager import should_retry_ai_error
        return should_retry_ai_error(error)

    def _update_ai_status(self, message: str) -> None:
        from AI_manager import update_ai_status
        update_ai_status(message)
#endregion