from AI_classes import AIProvider, OpenRouterProvider
from datetime import date, timedelta
import json
import math
import os
import time
import requests
from dotenv import load_dotenv
from DB_manager import MAX_QUANTITY, send_log, shift_calendar_years

#region API config
load_dotenv()

#region AI Recommendation Entry Point
def get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock, remarks, days_until_next):
    manager = AIManager(OpenRouterProvider())
    return manager.get_ai_recommendations(household_info, consumption_history, fridge_stock, purchase_stock, remarks, days_until_next)
#endregion

#region Prompt Builder
class PromptBuilder:
    def build_ai_prompt(self, data: dict) -> str:
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

#region AI Response Validator
class AIResponseValidator:
    def get_recommendation_schema(self) -> dict:
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
    def process_ai_response(self, ai_response: str) -> tuple:
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
            
            # Validate AI quantity limits
            if planned_qty > MAX_QUANTITY or recommended_qty > MAX_QUANTITY:
                return None, (f"{item_name}: quantity exceeds\nthe supported maximum of {MAX_QUANTITY:,}.")
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
                expiry_date = self._get_expiration_date(date.today(),365 if is_default else expiration_days)
            except (OverflowError, ValueError):
                return None, (f"{item['Item_Name']}: Expiration days are outside the supported date range.")
            # Validate AI estimated expiry date (max 3 years)
            if expiry_date > shift_calendar_years(date.today(), 3):
                return None, (f"{item['Item_Name']}: estimated expiry exceeds the 3-year stock limit.")

            item["Estimated_Expiry_Date"] = expiry_date.isoformat()
            item["Expiry_Date_Is_Default"] = is_default
        send_log(f"[AI] AI Recommendations: {json.dumps(data, indent=2)}")
        return data, None
    def check_ai_output(self, recommendations: list, grocery_list: list) -> bool:
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
    def _get_expiration_date(self, current_date: date, expiration_days: int) -> date:
        try:
            expiration_date = current_date + timedelta(days=expiration_days)
            return expiration_date
        except ValueError:
            raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
    def _get_default_expiration_date(self, current_date: date, default_expiration_days: int) -> date:
        try:
            default_expiration_date = current_date + timedelta(days=default_expiration_days)
            return default_expiration_date
        except ValueError:
            raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
#endregion

#region AI Manager
class AIManager:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider
        self._prompt_builder = PromptBuilder()
        self._validator = AIResponseValidator()

    def _prepare_data(self, household_info: dict, consumption_history: list, fridge_stock: list, grocery_list_input: list, remarks: str, current_date: date, next_purchase_date: date) -> dict:
        return {"household_info": household_info, "consumption_history": consumption_history, 
                "fridge_stock": fridge_stock, "planned_grocery_list": grocery_list_input, 
                "remarks": remarks, "current_date": current_date, "next_purchase_date": next_purchase_date}
    
    def _get_next_purchase_date(self, current_date: date, days_until_next: int) -> date:
        try:
            next_purchase_date = current_date + timedelta(days=days_until_next)
            return next_purchase_date
        except ValueError:
            raise ValueError(f"Invalid date format: {current_date}. Expected format: YYYY-MM-DD.")
        
    def get_ai_recommendations(self, household_info: dict, consumption_history: list, fridge_stock: list, purchase_stock: list, remarks: str, days_until_next: int) -> tuple:
        # Check API connection
        if isinstance(self._provider, OpenRouterProvider):
            OpenRouterProvider._update_ai_statusupdate_ai_status("Checking AI API connection...")
            connected, message = self._provider.check_api_conn()
            if not connected:
                OpenRouterProvider._update_ai_status("AI API connection failed.")
                send_log(f"[AI] {message}")
                return None, message
            OpenRouterProvider._update_ai_statusupdate_ai_status("AI API connection successful.")
        # Prepare AI input
        OpenRouterProvider._update_ai_statusupdate_ai_status("Preparing AI input...")
        current_date = date.today()
        next_purchase_date = self._get_next_purchase_date(current_date, days_until_next)
        data = self._prepare_data(household_info, consumption_history, fridge_stock, purchase_stock, remarks, current_date, next_purchase_date)

        # Build AI prompt
        OpenRouterProvider._update_ai_statusupdate_ai_status("Building AI prompt...")
        prompt = self._prompt_builder.build_ai_prompt(data)

        # Generate AI recommendations
        OpenRouterProvider._update_ai_statusupdate_ai_status("Sending prompt to AI...")
        result, error = self._provider.generate(prompt, self._validator.get_recommendation_schema(), purchase_stock, self._validator)

        if error:
            OpenRouterProvider._update_ai_statusupdate_ai_status("AI request failed.")
            send_log(f"[AI] {error}")
        return result, error
#endregion