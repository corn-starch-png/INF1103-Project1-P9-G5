import json
import os
import time
from dotenv import load_dotenv
from google import genai

#region API config
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found")
client = genai.Client(api_key=api_key)
#endregion

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
                    ]
                }
            }
        },
        "required": [
            "recommendations"
        ]
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
def call_gemini_api(prompt):
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": get_recommendation_schema()
        }
    )
    return interaction.output_text
#endregion

#region (TO BE Pass to Logic manager) bussiness rule
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

#region (TO BE Pass to Logic manager) bussiness rule
def process_ai_response(ai_response):
    try:
        data = json.loads(ai_response)

    except json.JSONDecodeError:
        print("Error: Gemini returned invalid JSON.")
        print(ai_response)
        return []

    recommendations = data.get("recommendations", [])

    valid_results = []

    for item in recommendations:
        if validate_business_rules(item):
            valid_results.append(item)

        else:
            print(
                f"Invalid business rule result for "
                f"{item.get('item', 'Unknown')}"
            )

    return valid_results
#endregion

#region display final output
def display_recommendations(recommendations):
    if not recommendations:
        print("No recommendations available.")
        return

    print("\nGROCERY RECOMMENDATIONS")
    print("=" * 60)

    for item in recommendations:
        print(f"Item: {item['item']}")
        print(f"Planned Quantity: {item['planned_quantity']}")
        print(f"Recommendation: {item['recommendation']}")
        print(
            f"Recommended Quantity: "
            f"{item['recommended_quantity']}"
        )
        print(
            f"Food Waste Risk: "
            f"{item['food_waste_risk']}"
        )
        print(
            f"Confidence Score: "
            f"{item['confidence_score']:.2f}"
        )
        print(
            f"Confidence Level: "
            f"{item['confidence_level']}"
        )
        print(f"Reason: {item['reason']}")
        print("-" * 60)
#endregion

#region main ai process calling
def ai_main():
    user_id = 1
    household_profile = get_household_profile(user_id)
    consumption_log = get_consumption_log(user_id)
    purchase_stock = get_grocery_input()
    data = prepare_data(
        household_profile,
        consumption_log,
        purchase_stock
    )
    prompt = build_ai_prompt(data)
    ai_response = call_gemini_api(prompt)
    recommendations = process_ai_response(ai_response)
    display_recommendations(recommendations)
#endregion

if __name__ == "__main__":
    ai_main()