from datetime import date, timedelta
import json
import math
import os
import time
import requests
from dotenv import load_dotenv
from openai import (OpenAI, APIConnectionError, AuthenticationError, 
                    BadRequestError, NotFoundError, RateLimitError, APIStatusError)
from DB_manager import send_log

#region API config
load_dotenv()
def create_ai_client():
    api_key = os.getenv("API_KEY")
    base_url= os.getenv("API_URL")
    if not api_key:
        raise ValueError("API_KEY not found in environment file")
    if not base_url:
            raise ValueError("API_URL not found in environment file")
    return OpenAI(base_url=base_url,api_key=api_key)

def get_ai_model(model_type="AI_MODEL"):
    ai_model = os.getenv(model_type, "").strip()
    if not ai_model:
        raise ValueError(f"{model_type} not found in environment file")
    return ai_model
#endregion

#region Date Conversion
def get_next_purchase_date(current_date, days_until_next):
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

#region data preparation for ai prompt
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
            "Recommendations_List": {
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
                        "Estimated_Consumption_Rate": {
                            "type": "number",
                            "minimum": 0
                        },
                        "Planned_Estimated_Calories": {
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
                        "Estimated_Consumption_Rate",
                        "Planned_Estimated_Calories",
                        "Estimated_Calories",
                        "Estimated_Expiration_Days",
                    ],
                    "additionalProperties": False
                }
            },
            "Total_Planned_Estimated_Calories": {
                "type": "number",
                "minimum": 0
            }
            ,
            "Total_Estimated_Calories": {
                "type": "number",
                "minimum": 0
            }
        },
        "required": [
            "Recommendations_List",
            "Total_Planned_Estimated_Calories",
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
- Check whether each planned grocery item has any relevant historical consumption records.
- No consumption history does not mean zero consumption.
- Do not interpret missing consumption records as evidence that the household does not need the item.
- If an item has no historical consumption records, use its planned_quantity as the default recommended_quantity.
- Only adjust this default if current stock information, explicit remarks or other provided evidence supports a different quantity.
- Do not invent a consumption rate for an item with no historical consumption records.
- Do not recommend zero solely because an item is new.
- If historical records explicitly show zero consumption, distinguish this from missing consumption history.
- For newly planned perishable items, do not invent a smaller consumption-based quantity solely from shelf life.

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
- For every item of the planned grocery list, there shall be two separate estimated calorie values:

1. Planned_Estimated_Calories
- Represents estimated total calories based on Planned_Quantity.
- Planned_Quantity refers to the user's quantity input.
- Planned_Estimated_Calories shall not use Recommended_Quantity.
- Planned_Estimated_Calories shall be used to evaluate the user's original grocery purchasing plan.

2. Estimated_Calories
- Represents estimated total calories based on Recommended_Quantity.
- Recommended_Quantity refers to the quantity suggested by the AI.
- Estimated_Calories shall not use Planned_Quantity.
- Estimated_Calories shall be used to compare the AI recommendation with the user's original purchasing plan.

CALORIE CALCULATION RULES:
- Use typical nutritional knowledge to estimate the calories for every food.
- Use the same estimated calorie value per unit for both calculations of the same item.
- Each calculation shall be based on its specific quantity and unit.
- If the quantity is 0, its estimated calories shall be 0.
- Do not change Planned_Quantity.
- Do not change Recommended_Quantity to accommodate calorie requirements.
- Do not concoct exact nutritional information for specific brands, products.
- Avoid unnecessary precision.
- All estimated calories must be numeric and expressed in kilocalories (kcal).
- Do not return calorie values in cal, kJ, or any other unit.

TOTAL ESTIMATED CALORIES:
There shall be two separate calorie totals:
1. Total_Planned_Estimated_Calories
- Sum of all Planned_Estimated_Calories.
- Represents the estimated total calories of the user's original planned grocery list.
2. Total_Estimated_Calories
- Sum of all Estimated_Calories.
- Represents the estimated total calories from the AI-recommended grocery quantities.
Both totals must exactly match the sum of their respective item-level estimated calories.
Do not combine planned and recommended calories into a single total. The calorie estimates are for reference only and must not be presented as actual nutritional information.

PURCHASE PERIOD:
- Use CURRENT DATE and PLANNED NEXT PURCHASE DATE to determine how many days the recommended purchase needs to cover.
- Consider whether existing fridge stock is likely to last until the next planned purchase date.
- Do not assume another grocery purchase will occur before the planned next purchase date.

ESTIMATED EXPIRATION DAYS:
- For each item from the planned grocery list, estimate the number of days
- until the newly purchased food is expected to expire.
- estimated_expiration_days refers to the number of days a newly purchased food item will remain edible from the day of purchase.
- The value returned is a non-negative integer and not a date.

When estimating the number of days until expiration:
1. Think about the type of food.
2. Think about the typical shelf life of the food.
3. Think about any specific storage instructions, packaging, freshness information, or other relevant notes.
4. Use general food storage and shelf-life knowledge when estimating the number of days until expiration.
5. Do not make up specific information about a food manufacturer-specified expiration information, pack aging, storage instructions, or other specific details.
6. Do not assume that existing items in the fridge have the same shelf life as newly purchased items.
7. Treat Estimated_Expiration_Days as an estimate, not an official manufacturer expiration or use-by date.
8. If both Planned_Quantity and Recommended_Quantity are 0, return Estimated_Expiration_Days as null.
9. Otherwise, estimate expiration days independently of the purchase quantities, using available shelf-life information.
10. If Planned_Quantity is greater than 0 but Recommended_Quantity is 0, still estimate expiration days to allow the original planned purchase to be assessed for expiry risk.
11. If there is insufficient information to reasonably estimate the expiration days, return null. Do not invent unsupported expiration information.
12. If expiration days can be reasonably estimated, return a non-negative integer representing the number of days until expiration. Do not include units, text, or decimal values.
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
- Retain Item_Name, Planned_Quantity and Unit exactly as provided in the planned purchases.
- Do not modify or recalculate Planned_Quantity.
- Calculate Recommended_Quantity based on the provided household data, consumption history, current fridge stock, remarks, and next purchase date.
- Calculate Estimated_Consumption_Rate for each item.
- Calculate Planned_Estimated_Calories based on Planned_Quantity.
- Calculate Estimated_Calories based on Recommended_Quantity.
- Calculate Estimated_Expiration_Days for each item according to the expiration estimation rules.
- For each item in the planned grocery list, produce exactly one recommendation.
- Do not add items that are not in the planned grocery list.
- Do not omit any items from the planned grocery list.
- Total_Planned_Estimated_Calories must equal the sum of all Planned_Estimated_Calories values.
- Total_Estimated_Calories must equal the sum of all Estimated_Calories values.
- Return all fields using the exact names and data types defined in the JSON response schema.
"""
#endregion

#region Check AI API Connection
def check_api_conn():
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
#endregion


#region Calling AI API
def call_ai_api(prompt, purchase_stock):
    try:
        client = create_ai_client().with_options(max_retries=0)
        models = [("Primary", get_ai_model()), ("Backup", get_ai_model("AI_BACKUP_MODEL"))]
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
        update_ai_status(f"Using {model_type.lower()} AI model: {ai_model}...")
        # Independent retries for each model
        for attempt in range(max_retries + 1):
            try:
                if attempt:
                    update_ai_status(f"Retrying {model_type.lower()} AI model. ({attempt}/{max_retries})...")
                else:
                    update_ai_status(f"Sending request to {model_type.lower()} AI model...")
                start_time = time.time()
                response = client.chat.completions.create(
                    model=ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "food_waste_recommendations",
                            "strict": True,
                            "schema": get_recommendation_schema()
                        }
                    }
                )
                # Validate response exists
                content = get_ai_response_content(response)
                elapsed_time = time.time() - start_time
                update_ai_status(f"AI response received in {elapsed_time:.1f} seconds.")
                # Validate output inside retry loop
                update_ai_status("Validating AI output...")
                ai_output, error = process_ai_response(content)
                if error:
                    raise ValueError(error)
                # Check original grocery list integrity
                if not check_ai_output(ai_output["Recommendations_List"], purchase_stock):
                    raise ValueError("AI recommendations do not match the original grocery list:\nitem names, planned quantities, units or order.")
                # All checks successful
                update_ai_status(f"Model used: {response.model}")
                update_ai_status("AI output validation successful.")
                return ai_output, None
            # HTTP 404: Skip retries
            except NotFoundError as error:
                last_error = handle_ai_exception(error)
                update_ai_status(f"{model_type} AI request failed (404). Skipping retries.")
                break
            # Authentication failure: Stop
            except AuthenticationError as error:
                return None, handle_ai_exception(error)
            # Retry temporary errors and invalid output
            except Exception as error:
                last_error = (str(error) if isinstance(error, ValueError) else handle_ai_exception(error))
                if should_retry_ai_error(error) and attempt < max_retries:
                    retry_delay = 3 * (attempt + 1)
                    update_ai_status(f"{model_type} AI error: {last_error}\nRetrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                update_ai_status(f"{model_type} AI model failed: {last_error}")
                break
        # Switch only after primary fails
        if model_type == "Primary":
            update_ai_status("Primary AI model failed. Switching to backup AI model...")
    update_ai_status("Both primary and backup AI models failed.")
    return None, f"Both AI models failed. Last error: {last_error}"
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
    send_log(f"[AI STATUS] {message}")
#endregion

#region Process and validate AI output
def process_ai_response(ai_response):
    # Reject invalid JSON and non-finite JSON numbers
    try:
        def reject_nonfinite_constant(value):
            raise ValueError(f"Invalid JSON number: {value}")
        data = json.loads(ai_response,parse_constant=reject_nonfinite_constant)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, "AI returned invalid JSON response."
    # Validate top-level JSON structure
    if not isinstance(data, dict):
        return None, "AI response must be a JSON object."
    expected_top = {"Recommendations_List", "Total_Planned_Estimated_Calories", "Total_Estimated_Calories"}
    if set(data) != expected_top:
        return None, "AI response has missing or unexpected top-level fields."

    recommendations = data["Recommendations_List"]
    if not isinstance(recommendations, list):
        return None, "Recommendations_List must be a list."
    # Validate non-negative, finite numeric values
    def valid_number(value):
        return (type(value) in (int, float) and math.isfinite(value) and value >= 0)
    # Validate both calorie totals
    for total_field in ("Total_Planned_Estimated_Calories", "Total_Estimated_Calories"):
        if not valid_number(data[total_field]):
            return None, f"{total_field} must be a non-negative finite number."
    # Required item fields
    required_item_fields = {
        "Item_Name",
        "Planned_Quantity",
        "Unit",
        "Recommended_Quantity",
        "Estimated_Consumption_Rate",
        "Planned_Estimated_Calories",
        "Estimated_Calories",
        "Estimated_Expiration_Days"
    }
    numeric_item_fields = (
        "Planned_Quantity",
        "Recommended_Quantity",
        "Estimated_Consumption_Rate",
        "Planned_Estimated_Calories",
        "Estimated_Calories"
    )
    valid_units = {"kg", "g", "l", "ml", "pcs"}

    # Validate each recommendation
    for index, item in enumerate(recommendations, start=1):
        if not isinstance(item, dict):
            return None, f"Recommendation {index} must be a JSON object."
        if set(item) != required_item_fields:
            return None, f"Recommendation {index} has missing or unexpected fields."
        item_name = item["Item_Name"]
        # Validate item name and unit
        if not isinstance(item_name, str) or not item_name.strip():
            return None, f"Recommendation {index}: Item_Name must be a non-empty string."
        if not isinstance(item["Unit"], str) or item["Unit"] not in valid_units:
            return None, f"{item_name}: Unit must be kg, g, l, ml or pcs."
        # Validate all numeric fields
        for field in numeric_item_fields:
            if not valid_number(item[field]):
                return None, f"{item_name}: {field} must be a non-negative finite number."
        planned_qty = item["Planned_Quantity"]
        recommended_qty = item["Recommended_Quantity"]
        planned_cal = item["Planned_Estimated_Calories"]
        recommended_cal = item["Estimated_Calories"]

        # Validate whole-number quantities for pcs
        if item["Unit"] == "pcs" and (not float(planned_qty).is_integer() or not float(recommended_qty).is_integer()):
            return None, f"{item_name}: Quantities in pcs must be whole numbers."
        # Validate estimated expiration days
        expiration_days = item["Estimated_Expiration_Days"]
        if expiration_days is not None and (type(expiration_days) is not int or expiration_days < 0):
            return None, f"{item_name}: Estimated_Expiration_Days must be a non-negative integer or null."
        if planned_qty == 0 and recommended_qty == 0 and expiration_days is not None:
            return None, f"{item_name}: Expiration days must be null when both quantities are zero."
        # Validate zero-quantity calorie calculations
        if planned_qty == 0 and planned_cal != 0:
            return None, f"{item_name}: Planned calories must be zero when planned quantity is zero."
        if recommended_qty == 0 and recommended_cal != 0:
            return None, f"{item_name}: Estimated calories must be zero when recommended quantity is zero."

        # Validate calorie consistency per unit
        if planned_qty > 0 and recommended_qty > 0:
            planned_per_unit = planned_cal / planned_qty
            recommended_per_unit = recommended_cal / recommended_qty
            if not math.isclose(planned_per_unit, recommended_per_unit, rel_tol=0.05,abs_tol=1.0):
                return None, f"{item_name}: Planned and recommended calories per unit are inconsistent."

    # Validate totals against individual item calorie sums
    totals = (("Total_Planned_Estimated_Calories", "Planned_Estimated_Calories"),
        ("Total_Estimated_Calories", "Estimated_Calories"))

    for total_field, item_field in totals:
        calculated = sum(item[item_field] for item in recommendations)
        if not math.isclose(data[total_field], calculated, rel_tol=0, abs_tol=0.01):
            return None, f"{total_field} does not match the sum of {item_field}."

    # Add estimated expiry date after validation
    for item in recommendations:
        expiration_days = item["Estimated_Expiration_Days"]
        is_default = expiration_days is None
        try:
            expiry_date = get_expiration_date(date.today(), 365 if is_default else expiration_days)
        except (OverflowError, ValueError):
            return None, f"{item['Item_Name']}: Expiration days are outside the supported date range."
        item["Estimated_Expiry_Date"] = expiry_date.isoformat()
        item["Expiry_Date_Is_Default"] = is_default
    send_log(f"[AI] AI Recommendations: {json.dumps(data, indent=2)}")
    return data, None
#endregion

#region check AI response order matches original grocery_list
def check_ai_output(recommendations, grocery_list):
    if not isinstance(recommendations, list) or not isinstance(grocery_list, list):
        return False
    if len(recommendations) != len(grocery_list):
        return False
    for ai_item, original in zip(recommendations, grocery_list):
        if not isinstance(ai_item, dict) or not isinstance(original, dict):
            return False
        for ai_field, original_field in (
            ("Item_Name", "Item_Name"),
            ("Planned_Quantity", "Quantity"),
            ("Unit", "Unit")):
            if ai_field not in ai_item or original_field not in original:
                return False
            if ai_item[ai_field] != original[original_field]:
                return False
    return True
#endregion

#region Function to call AI API with all reqiured args
def get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock,remarks,days_until_next):
    update_ai_status("Checking AI API connection...")
    connected, errMsg = check_api_conn()
    # Check if the connection to the AI API is successful
    if not connected: 
        update_ai_status("AI API connection failed.")
        send_log(f"[AI] {errMsg}") 
        return None, errMsg
    update_ai_status("AI API connection successful.")
    update_ai_status("Preparing AI input...")
    # Prepare data for AI processing
    current_date = date.today()
    next_purchase_date = get_next_purchase_date(current_date,days_until_next)
    data = prepare_data(household_info, consumption_history, fridge_stock, purchase_stock,remarks,current_date, next_purchase_date)
    update_ai_status("Building AI prompt...")
    #build the prompt for AI processing
    prompt = build_ai_prompt(data)
    update_ai_status("Sending prompt to AI...")
    ai_output, error = call_ai_api(prompt, purchase_stock)
    if error:
        update_ai_status("AI request failed.")
        send_log(f"[AI] {error}")
        return None, error
    return ai_output, None

#endregion