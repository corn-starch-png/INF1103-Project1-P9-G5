from datetime import date, timedelta
import json
import math
from modules.core.ItemRecord import ItemRecord
from logger import app_logger

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
            if planned_qty > ItemRecord.MAX_QUANTITY or recommended_qty > ItemRecord.MAX_QUANTITY:
                return None, (f"{item_name}: quantity exceeds\nthe supported maximum of {ItemRecord.MAX_QUANTITY:,}.")
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
            if expiry_date > ItemRecord.shift_calendar_years(date.today(), 3):
                return None, (f"{item['Item_Name']}: estimated expiry exceeds the 3-year stock limit.")

            item["Estimated_Expiry_Date"] = expiry_date.isoformat()
            item["Expiry_Date_Is_Default"] = is_default
        app_logger.send_log(f"[AI] AI Recommendations: {json.dumps(data, indent=2)}")
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