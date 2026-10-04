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

def get_fridge_stock():
    return [
    {
        "Item_Name": "Rice",
        "Quantity": 5,
        "Unit": "kg",
        "Purchase_Date": "2026-09-01",
        "Expiry_Date": "2027-09-01"
    },
    {
        "Item_Name": "Milk",
        "Quantity": 6,
        "Unit": "carton",
        "Purchase_Date": "2026-09-20",
        "Expiry_Date": "2026-10-04"
    },
    {
        "Item_Name": "Milk",
        "Quantity": 2,
        "Unit": "carton",
        "Purchase_Date": "2026-09-20",
        "Expiry_Date": "2026-10-04"
    },
    {
        "Item_Name": "Milk",
        "Quantity": 1,
        "Unit": "carton",
        "Purchase_Date": "2026-09-20",
        "Expiry_Date": "2026-10-04"
    },
    {
        "Item_Name": "Milk",
        "Quantity": 10,
        "Unit": "carton",
        "Purchase_Date": "2026-09-20",
        "Expiry_Date": "2026-10-04"
    },
    {
        "Item_Name": "Chicken",
        "Quantity": 1,
        "Unit": "kg",
        "Purchase_Date": "2026-09-23",
        "Expiry_Date": "2026-09-26"
    },
    {
        "Item_Name": "Chicken",
        "Quantity": 2,
        "Unit": "kg",
        "Purchase_Date": "2026-09-25",
        "Expiry_Date": "2026-09-26"
    },
    {
        "Item_Name": "Chicken",
        "Quantity": 1.5,
        "Unit": "kg",
        "Purchase_Date": "2026-09-27",
        "Expiry_Date": "2026-09-29"
    },
    {
        "Item_Name": "Chicken",
        "Quantity": 1,
        "Unit": "kg",
        "Purchase_Date": "2026-09-28",
        "Expiry_Date": "2026-09-30"
    }
    ]
#endregion

#region data preparation
def prepare_data(household_profile, consumption_log, fridge_stock, grocery_input):
    return {
        "household_profile": household_profile,
        "consumption_log": consumption_log,
        "fridge_stock": fridge_stock,
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
                        "estimated_calories": {
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
                        "estimated_calories",
                        "reason"
                    ],
                    "additionalProperties": False
                }
            },
            "total_estimated_calories": {
                "type": "number",
                "minimum": 0
            }
        },
        "required": [
            "recommendations",
            "total_estimated_calories"
        ],
        "additionalProperties": False
    }
#endregion

#region ai prompt
def build_ai_prompt(data):
    return f"""
You are the food waste recommendation assistant for a household.

On the provided household information, perform an analysis and assign the amount of each item that is recommended to be bought in the grocery list planned.

You are required to use only the information provided below.

Do not make any assumptions about household data, consumption data, stock data, future data, or nutritional data, if the information is not provided.

HOUSEHOLD PROFILE:
{data["household_profile"]}

CONSUMPTION HISTORY:
{data["consumption_log"]}

CURRENT FRIDGE STOCK:
{data["fridge_stock"]}

PLANNED PURCHASES:
{data["purchase_stock"]}

ASSESSMENT CRITERIA:
For every item consider:
1. Historical consumption
2. Current fridge stock
3. Planned purchase quantity
4. Information about household size and household characteristics, where applicable
5. Whether there has been consistency or variation in previous consumption
6. The quantity and quality of the historical data available
7. Comments given for the item

REMARKS:
- Before calculating the recommended_quantity, you should check the item's remarks.
- If a remark describes a temporary or unusual change in the household's needs,
When making the recommendation, give that information the top priority.
- The note is to be considered along with other information that includes current stock levels, planned quantity, family situation, and previous usage records.
- If there are no notes made, derive the conclusion based on other pieces of information available.
- Do not invent any situations or changes in the family which are not stated here.

RECOMMENDED QUANTITY:
The amount that the household should buy is the recommended_quantity.

The recommended quantity shall:
- consider current fridge stock before recommending additional purchases
- reflect historical consumption where sufficient data is available
- account for relevant remarks and temporary changes in needs
- avoid unnecessary excess that may contribute to food waste
- never be negative

QUANTITY RULES:
The only valid units are:
- "count"
- "kg"
- "L"

If the unit is "count":
- recommended_quantity must be a whole number
- do not recommend fractional quantities

If the unit is "kg" or "L":
- decimal quantities are allowed when appropriate
- avoid unnecessary precision

The unit that is recommended quantity should be the same as the one used for the planned purchase.

ESTIMATED CALORIES:
For every item, estimate the total calories represented by the
Using typical nutritional values to determine the recommended quantity.

The calorie value is an estimate only and must not be presented
as exact nutritional information.

If exact nutrition information is not provided:
- use a reasonable typical calorie value for the food item
- base the estimate on the recommended_quantity and its unit
- use common nutritional assumptions appropriate to the item
- avoid unnecessary precision
- do not claim that the estimate represents a specific brand or product
- do not invent exact nutrition-label values

For every recommendation provide:
- estimated_calories

The estimated_calories represents the estimated total calories for
that item's recommended_quantity.

Also calculate:
- total_estimated_calories

total_estimated_calories must be the sum of estimated_calories
for all recommendation items.

CALORIE UNIT:
- All estimated calorie values must be expressed in kilocalories (kcal).
- estimated_calories and total_estimated_calories must be numeric kcal values.
- Do not return calories in cal, kJ, or any other unit.

REASON:
Provide an explanation in 1-2 sentences for each recommended quantity.

The reason shall:
- reference relevant consumption history, current fridge stock,
planned quantity, household information or remarks
- explain the main factor affecting the recommended quantity
- mention uncertainty where available information is limited
- not contain information that was not provided
- not present estimated calorie information as exact

OUTPUT RULES:
- retain the item, the planned quantity and the unit exactly as they are given in the planned purchases.
- do not modify or recalculate planned_quantity
- only calculate recommended_quantity, estimated_calories and reason for each item
For each item on the planned grocery list, make exactly one recommendation.
- Make sure not to include any items that are not on the grocery list.
- do not take any items off the grocery list that was planned.
The total estimated calories must equal the sum of all the estimated calories values.
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
    client = create_ai_client()
    ai_model = get_ai_model()
    max_retries = int(os.getenv("MAX_RETRIES", 2))

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                update_ai_status("Request sent. Waiting for AI response...")
            else:
                update_ai_status(f"Retrying AI request. \n({attempt}/{max_retries})")
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
            update_ai_status(f"AI response received in {elapsed_time:.1f} seconds.")
            content = get_ai_response_content(response)
            return content, None
        except Exception as error:
            if (should_retry_ai_error(error) and attempt < max_retries):
                retry_delay = 3 * (attempt + 1)
                update_ai_status(f"Temporary AI error.\nRetrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
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

#region AI Error Retry Logic
def should_retry_ai_error(error):
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

#region AI STATUS UPDATE
def update_ai_status(message):
    print(f"[AI STATUS] {message}")
#endregion

#region Process AI output
def process_ai_response(ai_response):
    try:
        data = json.loads(ai_response)
    except (json.JSONDecodeError, TypeError):
        return None, "AI returned invalid JSON response."
    # Top-level response must be a dictionary
    if not isinstance(data, dict):
        return None, (f"Invalid AI response structure. \nExpected dict, received {type(data).__name__}.")
    # Validate recommendations list
    recommendations = data.get("recommendations")
    if not isinstance(recommendations, list):
        return None, ("AI response does not contain a valid 'recommendations' list.")
    # Validate each recommendation object
    for item in recommendations:
        if not isinstance(item, dict):
            return None, (f"Invalid recommendation structure. \nExpected dict, received {type(item).__name__}.")
        estimated_calories = item.get("estimated_calories")
        if not isinstance(estimated_calories, (int, float)):
            return None, (f"estimated_calories for {item.get('item', 'Unknown')} must be numeric.")
        if estimated_calories < 0:
            return None, (f"estimated_calories for {item.get('item', 'Unknown')} cannot be negative.")

    # Validate total estimated calories
    total_calories = data.get("total_estimated_calories")
    if not isinstance(total_calories, (int, float)):
        return None, ("total_estimated_calories must be numeric.")
    if total_calories < 0:
        return None, ("total_estimated_calories cannot be negative.")

    # Validate total against item calorie sum
    calculated_total = sum(item["estimated_calories"] for item in recommendations)
    if abs(calculated_total - total_calories) > 0.01:
        return None, ("total_estimated_calories does not match the sum of estimated_calories.")
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
    fridge_stock = get_fridge_stock()
    purchase_stock = get_grocery_input()

    update_ai_status("Preparing AI input...")
    data = prepare_data(household_profile, consumption_log, fridge_stock, purchase_stock)
    
    update_ai_status("Building AI prompt...")
    prompt = build_ai_prompt(data)

    update_ai_status("Sending prompt to AI...")
    ai_response, error = call_ai_api(prompt)

    if error: 
        update_ai_status("AI request failed.")
        print(error) 
        return
    
    update_ai_status("Validating AI output...")
    ai_output, error = process_ai_response(ai_response)
    if error:
        update_ai_status("AI output validation failed.")
        print(error)
        return
    recommendations = ai_output.get("recommendations", [])
    total_estimated_calories = ai_output.get("total_estimated_calories", 0)
    print(recommendations)
    print(f"Total Estimated Calories: {total_estimated_calories} kcal")

    update_ai_status("Completed.")
#endregion

if __name__ == "__main__":
    ai_main()