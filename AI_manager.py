import json
import os
import time
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
        {
            "item": "Milk",
            "week": "Week 1",
            "consumed_quantity": 2,
            "unit": "cartons"
        },
        {
            "item": "Milk",
            "week": "Week 2",
            "consumed_quantity": 2,
            "unit": "cartons"
        },
        {
            "item": "Milk",
            "week": "Week 3",
            "consumed_quantity": 2,
            "unit": "cartons"
        },

        {
            "item": "Bread",
            "week": "Week 1",
            "consumed_quantity": 2,
            "unit": "loaves"
        },
        {
            "item": "Bread",
            "week": "Week 2",
            "consumed_quantity": 1,
            "unit": "loaves"
        },
        {
            "item": "Bread",
            "week": "Week 3",
            "consumed_quantity": 2,
            "unit": "loaves"
        },

        {
            "item": "Eggs",
            "week": "Week 1",
            "consumed_quantity": 10,
            "unit": "pieces"
        },
        {
            "item": "Eggs",
            "week": "Week 2",
            "consumed_quantity": 12,
            "unit": "pieces"
        },
        {
            "item": "Eggs",
            "week": "Week 3",
            "consumed_quantity": 11,
            "unit": "pieces"
        },

        {
            "item": "Chicken",
            "week": "Week 1",
            "consumed_quantity": 1.0,
            "unit": "kg"
        },
        {
            "item": "Chicken",
            "week": "Week 2",
            "consumed_quantity": 1.2,
            "unit": "kg"
        },
        {
            "item": "Chicken",
            "week": "Week 3",
            "consumed_quantity": 1.1,
            "unit": "kg"
        }
    ]

def get_grocery_input():
    return [
        {
            "item": "Milk",
            "current_stock": 1,
            "planned_quantity": 3,
            "unit": "cartons"
        },
        {
            "item": "Bread",
            "current_stock": 1,
            "planned_quantity": 2,
            "unit": "loaves"
        },
        {
            "item": "Eggs",
            "current_stock": 8,
            "planned_quantity": 12,
            "unit": "pieces"
        },
        {
            "item": "Chicken",
            "current_stock": 0,
            "planned_quantity": 0.5,
            "unit": "kg"
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
                        "recommendation": {
                            "type": "string",
                            "enum": [
                                "BUY_MORE",
                                "BUY_AS_PLANNED",
                                "BUY_LESS",
                                "DO_NOT_BUY"
                            ]
                        },
                        "recommended_quantity": {
                            "type": "number",
                            "minimum": 0
                        },
                        "food_waste_risk": {
                            "type": "string",
                            "enum": [
                                "LOW",
                                "MEDIUM",
                                "HIGH"
                            ]
                        },
                        "confidence_score": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0
                        },
                        "confidence_level": {
                            "type": "string",
                            "enum": [
                                "LOW",
                                "MEDIUM",
                                "HIGH"
                            ]
                        },
                        "reason": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "item",
                        "planned_quantity",
                        "unit",
                        "recommendation",
                        "recommended_quantity",
                        "food_waste_risk",
                        "confidence_score",
                        "confidence_level",
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
purchase recommendations for every item in the planned
grocery list.

Use ONLY the information provided below.

HOUSEHOLD PROFILE:
{data["household_profile"]}

CONSUMPTION HISTORY:
{data["consumption_log"]}

PLANNED PURCHASES AND CURRENT STOCK:
{data["purchase_stock"]}

ASSESSMENT CRITERIA:
Consider:
1. Historical consumption of the item
2. Current quantity already in stock
3. Planned purchase quantity
4. Household size and characteristics, where relevant
5. Consistency or variation in past consumption
6. Amount and quality of available historical data

RECOMMENDATION MEANINGS:

BUY_MORE
Use when the planned quantity appears lower than the
household's expected requirement.

BUY_AS_PLANNED
Use when the planned quantity reasonably matches expected
consumption after considering current stock.

BUY_LESS
Use when the planned quantity appears higher than expected
consumption and reducing it may lower food waste risk.

DO_NOT_BUY
Use when current stock appears sufficient and purchasing
additional units may create unnecessary surplus.

RECOMMENDED QUANTITY RULES:
- recommended_quantity means the amount the user should buy
- never return a negative quantity
- DO_NOT_BUY must return 0
- BUY_LESS must return less than planned_quantity
- BUY_AS_PLANNED must equal planned_quantity
- BUY_MORE must return more than planned_quantity

FOOD WASTE RISK:
Assess the likelihood that unused or excess food will remain
after considering historical consumption, current stock and
planned purchases.

Do not automatically assign HIGH food waste risk just because
the recommendation is BUY_LESS.

CONFIDENCE SCORE:
confidence_score must represent how strongly the available
evidence supports the recommendation.

Consider:
- amount of historical data available
- consistency of historical consumption
- completeness of household information
- completeness of current stock information
- how clearly planned quantity differs from expected usage
- whether multiple data sources support the same conclusion

Confidence guidance:

LOW: 0.00 to 0.49
Use when data is limited, missing, inconsistent or weak.

MEDIUM: 0.50 to 0.79
Use when sufficient information exists but some uncertainty remains.

HIGH: 0.80 to 1.00
Use only when sufficient historical data exists, consumption
patterns are relatively consistent, stock information is
available, and the evidence strongly supports the recommendation.

Do not assign HIGH confidence if the available information is
insufficient, incomplete, contradictory or highly inconsistent.

REASON:
Provide a short 1-2 sentence explanation.

The reason should:
- reference relevant consumption, stock, planned quantity
  or household information
- explain the main factor affecting the recommendation
- mention uncertainty when confidence is LOW
- not contain information that was not provided

Generate exactly one recommendation for every item in the
planned grocery list.

Do not add items that are not present in the planned grocery list.
"""
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

#region [DEV ONLY] (TO BE MOVE to Logic manager) bussiness rule
def get_expected_confidence_level(score):
    if score < 0.50:
        return "LOW"

    if score < 0.80:
        return "MEDIUM"

    return "HIGH"

def validate_business_rules(item):
    planned = item["planned_quantity"]
    recommended = item["recommended_quantity"]
    recommendation = item["recommendation"]

    score = item["confidence_score"]
    level = item["confidence_level"]

    # Recommendation quantity rules
    if recommendation == "DO_NOT_BUY":
        if recommended != 0:
            return False

    elif recommendation == "BUY_LESS":
        if recommended >= planned:
            return False

    elif recommendation == "BUY_AS_PLANNED":
        if recommended != planned:
            return False

    elif recommendation == "BUY_MORE":
        if recommended <= planned:
            return False

    # Confidence level must match score
    expected_level = get_expected_confidence_level(score)

    if level != expected_level:
        return False

    return True
#endregion

#region [DEV ONLY] TO BE MOVE to Logic manager) bussiness rule
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
    else:
        return [], (f"Unsupported AI response structure:\n {type(data).__name__}")
    
    valid_results = []
    for item in recommendations:
        if not isinstance(item, dict):
            return [], (f"Invalid recommendation structure.\nExpected object, received {type(item).__name__}.")
        if validate_business_rules(item):
            valid_results.append(item)
        else:
            print(f"Invalid business rule result for {item.get('item', 'Unknown')}")
        for item in recommendations:
            if not isinstance(item, dict):
                continue
        try:
            if validate_business_rules(item):
                valid_results.append(item)
        except (KeyError, TypeError, ValueError) as error:
            return [], (f"Invalid recommendation data: {error}")
    if not valid_results:
        return [], "There were no valid AI suggestions found."

    return valid_results, None
#endregion

#region [DEV ONLY] display final output
def display_recommendations(recommendations):
    if not recommendations:
        print("No recommendations available.")
        return

    print("\nGROCERY RECOMMENDATIONS")
    print("=" * 60)

    for item in recommendations:
        if not isinstance(item, dict):
            print("Error: Invalid recommendation format.")
            return
        print(f"Item: {item['item']}")
        print(f"Planned Quantity: {item['planned_quantity']} {item['unit']}")
        print(f"Recommendation: {item['recommendation']}")
        print(f"Recommended Quantity: {item['recommended_quantity']} {item['unit']}")
        print(f"Food Waste Risk: {item['food_waste_risk']}")
        print(f"Confidence Score: {item['confidence_score']:.2f}")
        print(f"Confidence Level: {item['confidence_level']}")
        print(f"Reason: {item['reason']}")
        print("-" * 60)
#endregion

#region [DEV ONLY] main ai process calling
def ai_main():
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

    update_ai_status("Preparing recommendation output...")
    display_recommendations(recommendations)
    
    update_ai_status("Completed.")
#endregion

if __name__ == "__main__":
    ai_main()