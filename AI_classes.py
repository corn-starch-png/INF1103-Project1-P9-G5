from abc import ABC, abstractmethod
from datetime import date, timedelta
import json
import math
import os
import time
import requests
from dotenv import load_dotenv
from openai import (OpenAI, APIConnectionError, AuthenticationError, 
                    BadRequestError, NotFoundError, RateLimitError, APIStatusError)
from DB_manager import MAX_QUANTITY, send_log, shift_calendar_years

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
        try:
            client = self._create_ai_client().with_options(max_retries=0)
            models = [("Primary", self._get_ai_model()), ("Backup", self._get_ai_model("AI_BACKUP_MODEL"))]
            if models[0][1] == models[1][1]:
                return None, "Primary and backup AI models cannot be the same."
            max_retries = int(os.getenv("MAX_RETRIES", 2))
            if max_retries < 0:
                raise ValueError("MAX_RETRIES cannot be negative.")
        except ValueError as error:
            return None, str(error)
        last_error = None
        # Both models will use the same processing workflow
        for model_type, ai_model in models:
            self._update_ai_status(f"Using {model_type.lower()} AI model: {ai_model}...")
            # Independent retries for each model
            for attempt in range(max_retries + 1):
                try:
                    if attempt:
                        self._update_ai_status(f"Retrying {model_type.lower()} AI model. ({attempt}/{max_retries})...")
                    else:
                        self._update_ai_status(f"Sending request to {model_type.lower()} AI model...")
                    start_time = time.time()
                    response = client.chat.completions.create(
                        model=ai_model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "food_waste_recommendations",
                                "strict": True,
                                "schema": self._get_recommendation_schema()
                            }
                        }
                    )
                    # Validate response exists
                    content = self._get_ai_response_content(response)
                    elapsed_time = time.time() - start_time
                    self._update_ai_status(f"AI response received in {elapsed_time:.1f} seconds.")
                    # Validate output inside retry loop
                    self._update_ai_status("Validating AI output...")
                    ai_output, error = self._process_ai_response(content)
                    if error:
                        raise ValueError(error)
                    # Check original grocery list integrity
                    if not self._check_ai_output(ai_output["Recommendations_List"], self._purchase_stock):
                        raise ValueError("AI recommendations do not match the original grocery list:\nitem names, planned quantities, units or order.")
                    # All checks successful
                    self.update_ai_status(f"Model used: {response.model}")
                    self.update_ai_status("AI output validation successful.")
                    return ai_output, None
                # HTTP 404: Skip retries
                except NotFoundError as error:
                    last_error = self._handle_ai_exception(error)
                    self._update_ai_status(f"{model_type} AI request failed (404). Skipping retries.")
                    break
                # Authentication failure: Stop
                except AuthenticationError as error:
                    return None, self._handle_ai_exception(error)
                # Retry temporary errors and invalid output
                except Exception as error:
                    last_error = (str(error) if isinstance(error, ValueError) else self._handle_ai_exception(error))
                    if self._should_retry_ai_error(error) and attempt < max_retries:
                        retry_delay = 3 * (attempt + 1)
                        self._update_ai_status(f"{model_type} AI error: {last_error}\nRetrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    self._update_ai_status(f"{model_type} AI model failed: {last_error}")
                    break
            # Switch only after primary fails
            if model_type == "Primary":
                self._update_ai_status("Primary AI model failed. Switching to backup AI model...")
        self._update_ai_status("Both primary and backup AI models failed.")
        return None, f"Both AI models failed. Last error: {last_error}"

    def check_api_conn(self) -> tuple:
        # Get the api keys and api connection url
        api_key = os.getenv("API_KEY")
        conn_url= os.getenv("API_CONN_URL")
        if not api_key:
            raise ValueError("API_KEY not found in environment file")
        if not conn_url:
                raise ValueError("API_CONN_URL not found in environment file")
        headers = {"Authorization": f"Bearer {api_key}" }
        # Send the a request to api url to check for connection
        try:
            response = requests.get(conn_url, headers=headers,timeout=10)
            if response.status_code == 200:
                return True, "API Connection Establish. API Key Valid."
            if response.status_code == 501:
                return False, "AI API authentication failed. API KEY Not Valid."
            if response.status_code == 500:
                return False, "API Server Error."
            return False, (f"AI API connection failed. HTTP status: {response.status_code}")
        except requests.exceptions.Timeout:
            return False, "AI API connection timed out."
        except requests.exceptions.ConnectionError:
            return False, "Unable to connect to AI API."
        except requests.exceptions.RequestException as error:
            return False, (f"AI API connection error: {error}")
    def _create_ai_client(self):
        api_key = os.getenv("API_KEY")
        base_url= os.getenv("API_URL")
        if not api_key:
            raise ValueError("API_KEY not found in environment file")
        if not base_url:
                raise ValueError("API_URL not found in environment file")
        return OpenAI(base_url=base_url,api_key=api_key)

    def _get_ai_model(self, model_type: str) -> str:
        ai_model = os.getenv(model_type, "").strip()
        if not ai_model:
            raise ValueError(f"{model_type} not found in environment file")
        return ai_model

    def _get_ai_response_content(self, response: object) -> str:
        if not response.choices:
            raise ValueError("AI returned no response choices.")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI returned an empty response.")
        return content

    def _handle_ai_exception(self, error: Exception) -> str:
        if isinstance(error, AuthenticationError):
            return(f"Error: AI API authentication failed.\nCheck API_KEY in the environment file.")
        elif isinstance(error, NotFoundError):
            return ("Error: The configured AI model is unavailable or does not exist.")
        elif isinstance(error, RateLimitError):
            return("AI service is temporarily rate-limited.\nThe selected free model may currently be busy.\nPlease try again later.")
        elif isinstance(error, APIConnectionError):
            return("Error: Could not connect to Configured API URL.\nCheck API_URL and internet connectivity.")
        elif isinstance(error, BadRequestError):
            return("Error: OpenRouter rejected the request.\nCheck the model, prompt or response schema.")
        elif isinstance(error, APIStatusError):
            return (f"Error: AI API has returned HTTP Error Code: {error.status_code}.")
        return(f"Unexpected AI API error: {error}")
    
    def _should_retry_ai_error(self, error: Exception) -> bool:
        if isinstance(error, RateLimitError):
            return True
        if isinstance(error, APIConnectionError):
            return True
        if isinstance(error, APIStatusError):
            return error.status_code >= 500
        # Handles:
        # 1. AI returned no response choices.
        # 2. AI returned an empty response.
        if isinstance(error, ValueError):
            return True
        return False

    def _update_ai_status(self, message: str) -> None:
        send_log(f"[AI STATUS] {message}")
#endregion

#region Mock AI Provider
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
#endregion