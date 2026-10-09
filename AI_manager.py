from datetime import date, timedelta
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

#region Date Conversion
def date_convert(current_date, days_until_next):
    try:
        next_purchase_date = current_date + timedelta(days=days_until_next)
        return next_purchase_date
    except ValueError:
        raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
#endregion

#region expiration date conversion
def get_expiration_date(current_date, default_expiration_days):
    try:
        expiration_date = current_date + timedelta(days=default_expiration_days)
        return expiration_date
    except ValueError:
        raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
    
def get_default_expiration_date(current_date, default_expiration_days):
    try:
        default_expiration_date = current_date + timedelta(days=default_expiration_days)
        return default_expiration_date
    except ValueError:
        raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
#endregion

#For main.py to prepare data for AI processing
#region data preparation
def prepare_data(household_info, consumption_history, fridge_stock, grocery_list_input,remarks, current_date=None, next_purchase_date=None):
    return {
        "household_info": household_info,
        "consumption_history": consumption_history,
        "fridge_stock": fridge_stock,
        "planned_grocery_list": grocery_list_input,
        "remarks": remarks,
        "current_date": current_date,
        "next_purchase_date": next_purchase_date
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
                        "Item_Name": {
                            "type": "string"
                        },
                        "Planned_Quantity": {
                            "type": "number",
                            "minimum": 0
                        },
                        "Unit": {
                            "type": "string"
                        },
                        "Recommended_Quantity": {
                            "type": "number",
                            "minimum": 0
                        },
                        "Consumption_Rate": {
                            "type": "number",
                            "minimum": 0
                        },
                        "Estimated_Calories": {
                            "type": "number",
                            "minimum": 0
                        },
                        "Estimated_Expiration_Days": {
                            "type": ["integer", "null"],
                            "minimum": 0
                        },
                    },
                    "required": [
                        "Item_Name",
                        "Planned_Quantity",
                        "Unit",
                        "Recommended_Quantity",
                        "Consumption_Rate",
                        "Estimated_Calories",
                        "Estimated_Expiration_Days",
                    ],
                    "additionalProperties": False
                }
            },
            "Total_Estimated_Calories": {
                "type": "number",
                "minimum": 0
            }
        },
        "required": [
            "Recommendations_List",
            "Total_Estimated_Calories"
        ],
        "additionalProperties": False
    }
#endregion

#region ai prompt
def build_ai_prompt(data):
    return f"""
You are the food waste recommendation assistant for a household.
Your task is to analyse the provided household information and determine the recommended quantity to buy for every item in the planned grocery list.
Your goal is to meet the household's expected needs until the next planned purchase while avoiding unnecessary purchases that may contribute to food waste.
Use only the information provided for household and purchase recommendations. Do not invent or assume household data, consumption, stock, future purchases, household changes, preferences, or nutritional requirements that are not provided.
Typical nutritional knowledge may be used ONLY when estimating calories, as described below.

HOUSEHOLD PROFILE:
{data["household_info"]}

CONSUMPTION HISTORY:
{data["consumption_history"]}

CURRENT FRIDGE STOCK:
{data["fridge_stock"]}

PLANNED PURCHASES:
{data["planned_grocery_list"]}

REMARKS:
{data["remarks"]}

CURRENT DATE:
{data["current_date"]}

PLANNED NEXT PURCHASE DATE:
{data["next_purchase_date"]}

ASSESSMENT CRITERIA:
For every item consider:
1. Historical consumption
2. Weekly consumption rate
3. Current fridge stock
4. Planned purchase quantity
5. Number of days until the next planned purchase
6. Household size and household characteristics, where applicable
7. Consistency or variation in previous consumption
8. Quantity and quality of historical data available
9. Remarks provided for the item

REMARKS HANDLING:
- Before calculating the recommended_quantity, you should check the item's remarks.
- If a remark describes a temporary or unusual change in the household's needs, When making the recommendation, give that information the top priority.
- The note is to be considered along with other information that includes current stock levels, planned quantity, family situation, and previous usage records.
- If there are no notes made, derive the conclusion based on other pieces of information available.
- Do not invent any situations or changes in the family which are not stated here.

RECOMMENDED QUANTITY:
The amount that the household should buy is the recommended_quantity.

The recommended quantity shall:
- Consider current fridge stock before recommending additional purchases.
- Reflect historical consumption where sufficient data is available.
- Account for relevant remarks and temporary changes in needs.
- Avoid unnecessary excess that may contribute to food waste.
- Never be negative.

NEW ITEMS AND MISSING CONSUMPTION HISTORY:
- Check whether each planned grocery item has any relevant
  historical consumption records.
- No consumption history does not mean zero consumption.
- Do not interpret missing consumption records as evidence
  that the household does not need the item.
- If an item has no historical consumption records,
  use its planned_quantity as the default recommended_quantity.
- Only adjust this default if current stock information,
  explicit remarks or other provided evidence supports
  a different quantity.
- Do not invent a consumption rate for an item with
  no historical consumption records.
- Do not recommend zero solely because an item is new.
- If historical records explicitly show zero consumption,
  distinguish this from missing consumption history.
- For newly planned perishable items, do not invent a
  smaller consumption-based quantity solely from shelf life.

QUANTITY RULES:
The only valid units are:
- "kg","l","g,"ml","pcs",

If the unit is "pcs":
- Recommended_quantity must be a whole number
- Do not recommend fractional quantities

If the unit is "kg", "g", "l" or "ml":
- Decimal quantities are allowed when appropriate
- Avoid unnecessary precision

The unit that is recommended quantity should be the same as the one used for the planned purchase.

ESTIMATED CALORIES:
For every item, estimate the total calories represented by the recommended_quantity.
Using typical nutritional values to determine the recommended quantity.

The calorie value is an estimate only and must not be presented as exact nutritional information.

If exact nutrition information is not provided:
- Use a reasonable typical calorie value for the food item
- Base the estimate on the recommended_quantity and its unit
- Use common nutritional assumptions appropriate to the item
- Avoid unnecessary precision
- Do not claim that the estimate represents a specific brand or product
- Do not invent exact nutrition-label values

For every recommendation provide:
- estimated_calories

The estimated_calories represents the estimated total calories for
that item's recommended_quantity.

Also calculate:
- total_estimated_calories

total_estimated_calories must be the sum of estimated_calories for all recommendation items.

CALORIE UNIT:
- All estimated calorie values must be expressed in kilocalories (kcal).
- estimated_calories and total_estimated_calories must be numeric kcal values.
- Do not return calories in cal, kJ, or any other unit.

PURCHASE PERIOD:
- Use CURRENT DATE and PLANNED NEXT PURCHASE DATE to determine
  how many days the recommended purchase needs to cover.
- Consider whether existing fridge stock is likely to last until
  the next planned purchase date.
- Do not assume another grocery purchase will occur before the
  planned next purchase date.

ESTIMATED EXPIRATION DAYS:
For each item from the planned grocery list, estimate the number of days
until the newly purchased food is expected to expire.
estimated_expiration_days refers to the number of days a newly purchased food item will remain edible from the day of purchase.
The value returned is a non-negative integer and not a date.

When estimating the number of days until expiration:
1. Think about the type of food.
2. Think about the typical shelf life of the food.
3. Think about any specific storage instructions, packaging,
freshness information, or other relevant notes.
4. Use general food storage and shelf-life knowledge
when estimating the number of days until expiration.
5. Do not make up specific information about a food’s
manufacturer-specified expiration information, pack aging, storage instructions, or other specific details.

6. Do not assume that existing items in the fridge have the
same shelf life as newly purchased items.
7. Remember to treat the estimated_expiration_days as an
estimate and not an official manufacturer expiration or use-by date.
If recommended_quantity is 0, return estimated_expiration_days as null.
Return estimated_expiration_days as null if the data required to estimate expiry datys is not available or cannot be estimated a reasonable days.
Otherwise, if you believe you have enough information to estimate expiration, return the number of days as an integer. There should be no units or other text. You should never use more decimal places than are necessary to represent an integer.

When determining the suggested quantity:
Consider whether it is reasonable to assume that the amount of food recommended will be consumed before it goes bad.
When making a recommendation, consider past consumption, current inventory, the time of purchase, and any pertinent notes, but do not recommend more than you feel can be safely consumed before it expires.

WEEKLY CONSUMPTION RATE:
For all items that are supposed to be purchased, compute the consumption rate.

Consumption rate is the estimated amount that is consumed within a period of 7 days.

A Consumption History entry comprises of:
- Date Range: number of days in the record
- Quantity: amount of consumption in the Date_Range
- Unit: unit of measurement

When normalising consumption for a historical record:
weekly_rate = (Quantity / Date_Range) * 7

Where there are several historical records for a product:
- Calculate the weekly_rate for each relevant record
- Look out for remarks of any unusual or special consumption
- Do not use an unusual event as the normal consumption pattern of the household, unless the unusual circumstances apply to the upcoming purchase cycle
- Find the appropriate consumption_rate from the normalised historical data provided

The resulting consumption rate:
- Must reflect the consumption rate per 7 days
- Should have the same unit of base as the item
- Cannot be less than zero
- Can be in decimals
- Should not be unnecessarily precise

OUTPUT RULES:
- Retain the item, the planned quantity and the unit exactly as they are given in the planned purchases.
- Do not modify or recalculate planned_quantity
- Calculate recommended_quantity, consumption_rate, estimated_calories and estimated_expiration_date for each item.
For each item on the planned grocery list, make exactly one recommendation.
- Make sure not to include any items that are not on the grocery list.
- Do not take any items off the grocery list that was planned.
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
        item_name = item.get("Item_Name", "Unknown")
        recommended_quantity = item.get("Recommended_Quantity")
        if type(recommended_quantity) not in (int, float):
            return None, (f"Recommended_Quantity for {item_name} must be numeric.")
        if recommended_quantity < 0:
            return None, (f"Recommended_Quantity for {item_name} cannot be negative.")
        # Validate estimated expiration days
        estimated_expiration_days = item.get("Estimated_Expiration_Days")
        if estimated_expiration_days is not None:
            if type(estimated_expiration_days) is not int:
                return None, (f"Estimated_Expiration_Days for {item_name} must be an integer.")
            if estimated_expiration_days < 0:
                return None, (f"Estimated_Expiration_Days for {item_name} cannot be negative.")
        if recommended_quantity == 0:
            if estimated_expiration_days is not None:
                return None, (f"Estimated_Expiration_Days for {item_name} must be null when Recommended_Quantity is 0.")
        # Validate estimated calories
        estimated_calories = item.get("Estimated_Calories")
        if type(estimated_calories) not in (int, float):
            return None, (f"Estimated_Calories for {item_name} must be numeric.")
        if estimated_calories < 0:
            return None, (f"Estimated_Calories for {item_name} cannot be negative.")
    # Validate total estimated calories
    total_calories = data.get("total_estimated_calories")
    if type(total_calories) not in (int, float):
        return None, ("total_estimated_calories must be numeric.")
    if total_calories < 0:
        return None, ("total_estimated_calories cannot be negative.")
    # Validate total against item calorie sum
    calculated_total = sum(item["Estimated_Calories"] for item in recommendations)
    if abs(calculated_total - total_calories) > 0.01:
        return None, ("total_estimated_calories does not match the sum of Estimated_Calories.")
    # Add Estimated_Expiry_Date after successful validation
    for item in recommendations:
        estimated_expiration_days = item.get("Estimated_Expiration_Days")
        if estimated_expiration_days is not None:
            item["Estimated_Expiry_Date"] = get_expiration_date(date.today(), estimated_expiration_days).isoformat()
        else:
            item["Estimated_Expiry_Date"] = get_default_expiration_date(date.today(), 365).isoformat()
    return data, None
#endregion

#region Functions to be implemented for main.py to call AI_manager.py
# To use functions to get specific data from the AI output, you can implement the following functions in main.py:
# ai_recommendations, error = get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock,remarks,days_until_next)
# recommendations = ai_recommendations.get("recommendations", [])
# total_estimated_calories = ai_recommendations.get("total_estimated_calories", 0)
def get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock,remarks,days_until_next):
    update_ai_status("Checking AI API connection...")
    connected, errMsg = check_api_conn()

    # Check if the connection to the AI API is successful
    if not connected: 
        update_ai_status("AI API connection failed.")
        print(errMsg) 
        return None, errMsg
    update_ai_status("AI API connection successful.")
    
    update_ai_status("Preparing AI input...")
    # Prepare data for AI processing
    current_date = date.today()
    next_purchase_date = date_convert(current_date,days_until_next)
    data = prepare_data(household_info, consumption_history, fridge_stock, purchase_stock,remarks,current_date, next_purchase_date)

    update_ai_status("Building AI prompt...")
    #build the prompt for AI processing
    prompt = build_ai_prompt(data)

    update_ai_status("Sending prompt to AI...")
    #Output of the AI response
    ai_response, error = call_ai_api(prompt)

    if error: 
        update_ai_status("AI request failed.")
        print(error) 
        return None, error
    
    update_ai_status("Validating AI output...")
    # Process and validate the AI response
    ai_output, error = process_ai_response(ai_response)
    if error:
        update_ai_status("AI output validation failed.")
        print(error)
        return None, error

    return ai_output, None
#endregion