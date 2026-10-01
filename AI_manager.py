import json
import os
import time
import requests
from dotenv import load_dotenv
from openai import (OpenAI, APIConnectionError, AuthenticationError, 
                    BadRequestError, NotFoundError, RateLimitError, APIStatusError)

#region API config
load_dotenv()
def create_ai_client():
    api_key = os.getenv("API_KEY")
    base_url= os.getenv("API_URL")

    if not api_key:
        raise ValueError("API_KEY not found in environment file")
    
    if not base_url:
            raise ValueError("API_URL not found in environment file")

    return OpenAI(
        base_url=base_url,
        api_key=api_key
    )

def get_ai_model():
    ai_model = os.getenv("AI_MODEL")

    if not ai_model:
        raise ValueError("AI_MODEL not found in environment file")

    return ai_model
#endregion

#TODO: proper data fetching from IO Manager
#region data fetching
def get_household_profile(user_id):
    return {
        "user_id": user_id,
        "household_size": 4,
        "adults": 2,
        "children": 2,
        "dietary_preferences": [],
        "notes": "Household usually cooks at home on weekdays."
    }

def get_consumption_log(user_id):
    return [
        #unit - l
        {
            "item": "Milk",
            "week": "Week 1",
            "consumed_quantity": 2,
            "unit": "L",
            "remarks": ""
        },
        {
            "item": "Milk",
            "week": "Week 2",
            "consumed_quantity": 1,
            "unit": "L",
            "remarks": ""
        },
        {
            "item": "Milk",
            "week": "Week 3",
            "consumed_quantity": 2,
            "unit": "L",
            "remarks": ""
        },
        #unit - count
        {
            "item": "Eggs",
            "week": "Week 1",
            "consumed_quantity": 11,
            "unit": "count",
            "remarks": ""
        },
        {
            "item": "Eggs",
            "week": "Week 2",
            "consumed_quantity": 12,
            "unit": "count",
            "remarks": ""
        },
        {
            "item": "Eggs",
            "week": "Week 3",
            "consumed_quantity": 11,
            "unit": "count",
            "remarks": ""
        },
        #unit - kg
        {
            "item": "Chicken",
            "week": "Week 1",
            "consumed_quantity": 1.5,
            "unit": "kg",
            "remarks": ""
        },
        {
            "item": "Chicken",
            "week": "Week 2",
            "consumed_quantity": 1.2,
            "unit": "kg",
            "remarks": ""
        },
        {
            "item": "Chicken",
            "week": "Week 3",
            "consumed_quantity": 1.1,
            "unit": "kg",
            "remarks": ""
        },
        #test fanta
        {
            "item": "Fanta",
            "week": "Week 1",
            "consumed_quantity": 1,
            "unit": "L",
            "remarks": ""
        },
        {
            "item": "Fanta",
            "week": "Week 2",
            "consumed_quantity": 3,
            "unit": "L",
            "remarks": ""
        },
        #test apple
        {
            "item": "Apple",
            "week": "Week 1",
            "consumed_quantity": 12,
            "unit": "count",
            "remarks": ""
        },
        {
            "item": "Apple",
            "week": "Week 2",
            "consumed_quantity": 14,
            "unit": "count",
            "remarks": ""
        }
    ]

def get_grocery_input():
    return [
        {
            "item": "Milk",
            "current_stock": 1,
            "planned_quantity": 3,
            "unit": "L",
            "remarks": ""
        },
        {
            "item": "Eggs",
            "current_stock": 8,
            "planned_quantity": 12,
            "unit": "count",
            "remarks": ""
        },
        {
            "item": "Chicken",
            "current_stock": 0,
            "planned_quantity": 0.5,
            "unit": "kg",
            "remarks": ""
        },
        #Anomaly (party - more people)
        {
            "item": "Fanta",
            "current_stock": 0,
            "planned_quantity": 30,
            "unit": "L",
            "remarks": "House party with 100 guests on monday"
        },
        #Anomaly (vacation - less people)
        {
            "item": "Apple",
            "current_stock": 0,
            "planned_quantity": 13,
            "unit": "count",
            "remarks": "Parents left for holiday on wednesday "
        }
        
    ]
#endregion

#region data preparation
def prepare_data(household_profile, consumption_log, grocery_input):
    return {
        "household_profile": household_profile,
        "consumption_log": consumption_log,
        "purchase_stock": grocery_input
    }
#endregion

#region data response schema
def get_recommendation_schema():
    return {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string"
                        },
                        "planned_quantity": {
                            "type": "number",
                            "minimum": 0
                        },
                        "unit": {
                            "type": "string"
                        },
                        "recommended_quantity": {
                            "type": "number",
                            "minimum": 0
                        },
                        "reason": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "item",
                        "planned_quantity",
                        "unit",
                        "recommended_quantity",
                        "reason"
                    ],
                    "additionalProperties": False
                }
            }
        },
        "required": [
            "recommendations"
        ],
        "additionalProperties": False
    }
#endregion

#region ai prompt
def build_ai_prompt(data):
    return f"""
You are a household food waste recommendation assistant.

Analyse the provided household information and generate
a recommended purchase quantity for every item in the
planned grocery list.

Use ONLY the information provided below.
Do not assume missing household information, consumption data,
stock levels, or future events that are not explicitly provided.

HOUSEHOLD PROFILE:
{data["household_profile"]}

CONSUMPTION HISTORY:
{data["consumption_log"]}

PLANNED PURCHASES AND CURRENT STOCK:
{data["purchase_stock"]}

ASSESSMENT CRITERIA:
For each item, consider:
1. Historical consumption
2. Current stock
3. Planned purchase quantity
4. Household size and characteristics, where relevant
5. Consistency or variation in past consumption
6. Amount and quality of available historical data
7. Remarks provided for the item

REMARKS:
- Before calculating the recommended_quantity, check the item's remarks.
- If a remark describes a temporary or unusual change in the household's needs, prioritise that information when making the recommendation.
- Use the remark together with other relevant information, including current stock, planned quantity, and consumption history.
- If no remark is provided, base the recommendation on the other available information.

RECOMMENDED QUANTITY:
The recommended_quantity represents the amount the household should purchase.
The recommended quantity should:
- consider current stock before recommending additional purchases
- reflect historical consumption where sufficient data is available
- account for relevant remarks and temporary changes in needs
- avoid unnecessary excess that may contribute to food waste
- never be negative

QUANTITY RULES:
The only valid units are "count", "kg", and "L".

If the unit is "count":
- recommended_quantity must be a whole number
- do not recommend fractional quantities

If the unit is "kg" or "L":
- decimal quantities are allowed when appropriate
- avoid unnecessary precision

The recommended_quantity must use the same unit as the planned purchase.

OUTPUT RULES:
- Keep item, planned_quantity, and unit exactly as provided.
- Do not modify or recalculate planned_quantity.
- Only calculate recommended_quantity and reason.
- Generate exactly one recommendation for every item in the planned grocery list.
- Do not add items that are not present in the planned grocery list.

"""
#endregion

#region Check AI API Connection
def check_api_conn():
    api_key = os.getenv("API_KEY")
    conn_url= os.getenv("API_CONN_URL")

    if not api_key:
        raise ValueError("API_KEY not found in environment file")
    if not conn_url:
            raise ValueError("API_CONN_URL not found in environment file")
    
    headers = {"Authorization": f"Bearer {api_key}" }

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
#endregion

#region Calling AI API
def call_ai_api(prompt):
    try:
        client = create_ai_client()
        ai_model = get_ai_model()

        update_ai_status("Request sent. Waiting for AI response...")
        start_time = time.time()

        response = client.chat.completions.create(
            model=ai_model,
            messages=[{"role": "user","content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "food_waste_recommendations",
                    "strict": True,
                    "schema": get_recommendation_schema()
                }
            }
        )
        
        elapsed_time = time.time() - start_time
        print(response.to_json)
        update_ai_status(f"AI response received in {elapsed_time:.1f} seconds.")

        return get_ai_response_content(response), None
    except Exception as error:
        return None, handle_ai_exception(error)
#endregion

#region get Response Content
def get_ai_response_content(response):
    if not response.choices:
        raise ValueError("AI returned no response choices.")
    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI returned an empty response.")
    return content
#endregion

#region API Response Error Handling
def handle_ai_exception(error):
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
#endregion

#region AI STATUS UPDATE
def update_ai_status(message):
    print(f"[AI STATUS] {message}")
#endregion

#region Process AI output
def process_ai_response(ai_response):
    try:
        data = json.loads(ai_response)

    except json.JSONDecodeError:
        print("Error: AI returned invalid JSON Response.")
        print(ai_response)
        return []

    if isinstance(data, dict):
        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list):
            return [], ("AI response does not contain a valid\n'recommendations' list.")
    # Fallback: AI returned the list directly
    elif isinstance(data, list):
        recommendations = data
        data = {"recommendations": recommendations}
    else:
        return [], (f"Unsupported AI response structure:\n {type(data).__name__}")
    
    return data, None
#endregion

#region [DEV ONLY] main ai process calling
def ai_main():

    update_ai_status("Checking AI API connection...")
    connected, errMsg = check_api_conn()

    if not connected: 
        update_ai_status("AI API connection failed.")
        print(errMsg) 
        return
    update_ai_status("AI API connection successful.")
    print("\n")
    
    user_id = 1

    update_ai_status("Fetching household data...")
    household_profile = get_household_profile(user_id)
    consumption_log = get_consumption_log(user_id)
    purchase_stock = get_grocery_input()

    update_ai_status("Preparing AI input...")
    data = prepare_data(household_profile, consumption_log, purchase_stock)
    
    update_ai_status("Building AI prompt...")
    prompt = build_ai_prompt(data)

    update_ai_status("Sending prompt to AI...")
    ai_response, error = call_ai_api(prompt)

    #region [DEV] DEBUG PREVIEW AI RESPONSE
    print("\n[DEV] RAW AI RESPONSE:")
    print(ai_response)
    print("\n")
    #endregion

    if error: 
        update_ai_status("AI request failed.")
        print(error) 
        return
    
    update_ai_status("Validating AI output...")
    recommendations, error = process_ai_response(ai_response)
    if error:
        update_ai_status("AI output validation failed.")
        print(error)
        return
    print(recommendations)
    
    update_ai_status("Completed.")
#endregion

if __name__ == "__main__":
    ai_main()