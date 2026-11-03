import copy
import json
import pytest
import math
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from AI_manager import AIManager, AIResponseValidator
from core.AI_classes import AIProvider, OpenRouterProvider, MockAIProvider
from AI_manager import AIManager, AIResponseValidator
from core.AI_classes import AIProvider, OpenRouterProvider, MockAIProvider
from datetime import date, timedelta
import Logic_manager as logic

#region Hardcoded data
# Household information
household_info = [
    {"Person_ID": 1, "Name": "TestUser", "Age": 23, "Gender": "Male", "Dietary_Restriction": "none"},
    {"Person_ID": 2, "Name": "Alice", "Age": 40, "Gender": "Female", "Dietary_Restriction": "none"},
    {"Person_ID": 3, "Name": "Bob", "Age": 18, "Gender": "Male", "Dietary_Restriction": "none"}
]
# Consumption history (2 historical 7-day periods)
history = [
    {"Date_Range": 7, "Item_Name": "milk", "Quantity": 1.5, "Unit": "l", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "eggs", "Quantity": 8, "Unit": "pcs", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "rice", "Quantity": 1.0, "Unit": "kg", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "chicken", "Quantity": 0.8, "Unit": "kg", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "bananas", "Quantity": 6, "Unit": "pcs", "Remarks": "none"},

    {"Date_Range": 7, "Item_Name": "milk", "Quantity": 1.8, "Unit": "l", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "eggs", "Quantity": 10, "Unit": "pcs", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "rice", "Quantity": 1.2, "Unit": "kg", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "chicken", "Quantity": 0.9, "Unit": "kg", "Remarks": "none"},
    {"Date_Range": 7, "Item_Name": "bananas", "Quantity": 5, "Unit": "pcs", "Remarks": "none"}
]
# Current fridge stock
fridge = [
    {"Item_Name": "milk", "Quantity": 1.0, "Unit": "l", "Purchase_Date": str(date.today() - timedelta(days=2)), "Expiry_Date": str(date.today() + timedelta(days=3)), "Remarks": "opened"},
    {"Item_Name": "eggs", "Quantity": 6, "Unit": "pcs", "Purchase_Date": str(date.today() - timedelta(days=3)), "Expiry_Date": str(date.today() + timedelta(days=14)), "Remarks": "none"},
    {"Item_Name": "rice", "Quantity": 1.5, "Unit": "kg", "Purchase_Date": str(date.today() - timedelta(days=5)), "Expiry_Date": str(date.today() + timedelta(days=180)), "Remarks": "none"},
    {"Item_Name": "chicken", "Quantity": 0.3, "Unit": "kg", "Purchase_Date": str(date.today() - timedelta(days=1)), "Expiry_Date": str(date.today() + timedelta(days=2)), "Remarks": "none"},
    {"Item_Name": "bananas", "Quantity": 3, "Unit": "pcs", "Purchase_Date": str(date.today() - timedelta(days=2)), "Expiry_Date": str(date.today() + timedelta(days=3)), "Remarks": "none"}
]
# Planned grocery list
grocery_list = [
    {"Item_Name": "milk", "Quantity": 3.0, "Unit": "l"},
    {"Item_Name": "eggs", "Quantity": 2.0, "Unit": "pcs"},
    {"Item_Name": "rice", "Quantity": 2.0, "Unit": "kg"},
    {"Item_Name": "bread", "Quantity": 3.0, "Unit": "pcs"},
    {"Item_Name": "bananas", "Quantity": 10.0, "Unit": "pcs"},
    {"Item_Name": "yogurt", "Quantity": 4.0, "Unit": "pcs"}
]
# HARDCODED AI RECOMMENDATIONS
# These sample responses replace real AI output.
# This means the tests do not need a live API connection.
SAMPLE_AI_RESPONSE = json.loads(r'''{"Recommendations_List":[{"Item_Name":"milk","Planned_Quantity":3,"Unit":"l","Recommended_Quantity":3,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":1800,"Estimated_Calories":1800,"Estimated_Expiration_Days":7,"Estimated_Expiry_Date":"2026-10-20","Expiry_Date_Is_Default":false},{"Item_Name":"eggs","Planned_Quantity":2,"Unit":"pcs","Recommended_Quantity":2,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":140,"Estimated_Calories":140,"Estimated_Expiration_Days":21,"Estimated_Expiry_Date":"2026-11-03","Expiry_Date_Is_Default":false},{"Item_Name":"rice","Planned_Quantity":2,"Unit":"kg","Recommended_Quantity":2,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":7000,"Estimated_Calories":7000,"Estimated_Expiration_Days":365,"Estimated_Expiry_Date":"2027-10-13","Expiry_Date_Is_Default":false},{"Item_Name":"bread","Planned_Quantity":3,"Unit":"pcs","Recommended_Quantity":3,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":3600,"Estimated_Calories":3600,"Estimated_Expiration_Days":5,"Estimated_Expiry_Date":"2026-10-18","Expiry_Date_Is_Default":false},{"Item_Name":"bananas","Planned_Quantity":10,"Unit":"pcs","Recommended_Quantity":10,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":1000,"Estimated_Calories":1000,"Estimated_Expiration_Days":5,"Estimated_Expiry_Date":"2026-10-18","Expiry_Date_Is_Default":false},{"Item_Name":"yogurt","Planned_Quantity":4,"Unit":"pcs","Recommended_Quantity":4,"Estimated_Consumption_Rate":0,"Planned_Estimated_Calories":400,"Estimated_Calories":400,"Estimated_Expiration_Days":7,"Estimated_Expiry_Date":"2026-10-20","Expiry_Date_Is_Default":false}],"Total_Planned_Estimated_Calories":13940,"Total_Estimated_Calories":13940}''')
AI_RECOMMENDATIONS = SAMPLE_AI_RESPONSE["Recommendations_List"]
CAPTURE_DATE = date(2026, 10, 13)
#endregion

#region Raw AI Response
# Remove the two fields that are generated by AIResponseValidator.
# This simulates the original 8 field JSON response from AI api request.
RAW_AI_RESPONSE = copy.deepcopy(SAMPLE_AI_RESPONSE)
for item in RAW_AI_RESPONSE["Recommendations_List"]:
    item.pop("Estimated_Expiry_Date")
    item.pop("Expiry_Date_Is_Default")
#endregion

# =========================================================
# 1. AI RESPONSE VALIDATION
# Input: Hardcoded AI recommendations and grocery list.
# Expected: Validate response structure, item identity,
# planned quantities, units, order and invalid responses.
# =========================================================
#region AI Response Validation
class TestAIResponseValidator:
    def setup_method(self):
        self.validator = AIResponseValidator()
    # Test 1 - Verify top-level JSON fields
    # Expected result: Contains exactly the three required top-level fields.
    def test_final_output_exact_top_level_fields(self):
        expected = {"Recommendations_List", "Total_Planned_Estimated_Calories", "Total_Estimated_Calories"}
        assert set(SAMPLE_AI_RESPONSE) == expected
    # Test 2 - Verify all 10 recommendation fields
    # Expected result: All six recommendations contain exactly the 10 required fields.
    def test_final_output_has_all_10_item_fields(self):
        expected = {
            "Item_Name", "Planned_Quantity", "Unit", "Recommended_Quantity",
            "Estimated_Consumption_Rate", "Planned_Estimated_Calories",
            "Estimated_Calories", "Estimated_Expiration_Days",
            "Estimated_Expiry_Date", "Expiry_Date_Is_Default"
        }
        assert len(AI_RECOMMENDATIONS) == 6
        for item in AI_RECOMMENDATIONS:
            assert set(item) == expected
    # Test 3 - Verify recommendations match the original grocery list
    # Expected result: Returns True when item names, quantities, units and order match.
    def test_actual_output_matches_original_grocery_list(self):
        assert self.validator.check_ai_output(AI_RECOMMENDATIONS, grocery_list) is True
    # Test 4 - Reject incorrect grocery item order
    # Expected result: Returns False when the recommendation order differs from the grocery list.
    def test_ai_output_wrong_order(self):
        reversed_list = AI_RECOMMENDATIONS[::-1]
        assert self.validator.check_ai_output(reversed_list, grocery_list) is False
    # Test 5 - Reject changed planned quantity
    # Expected result: Returns False when the AI modifies the original planned quantity.
    def test_ai_output_changed_quantity(self):
        modified = copy.deepcopy(AI_RECOMMENDATIONS)
        modified[0]["Planned_Quantity"] = 5.0
        assert self.validator.check_ai_output(modified, grocery_list) is False
    # Test 6 - Reject changed unit
    # Expected result: Returns False when the AI changes the original grocery item's unit.
    def test_ai_output_changed_unit(self):
        modified = copy.deepcopy(AI_RECOMMENDATIONS)
        modified[0]["Unit"] = "kg"
        assert self.validator.check_ai_output(modified, grocery_list) is False
    # Test 7 - Reject missing grocery item
    # Expected result: Returns False when a recommendation is missing from the original grocery list.
    def test_ai_output_missing_item(self):
        modified = AI_RECOMMENDATIONS[:-1]
        assert self.validator.check_ai_output(modified, grocery_list) is False
    # Test 8 - Reject changed item name
    # Expected result: Returns False when the AI changes an original grocery item's name.
    def test_ai_output_changed_name(self):
        modified = copy.deepcopy(AI_RECOMMENDATIONS)
        modified[0]["Item_Name"] = "other"
        assert self.validator.check_ai_output(modified, grocery_list) is False
    # Test 9 - Process valid raw AI response
    # Expected result: Returns valid recommendations with the two expiry-date fields added.
    def test_process_valid_ai_response(self):
        result, error = self.validator.process_ai_response(json.dumps(RAW_AI_RESPONSE))
        assert error is None
        assert result is not None
        for item in result["Recommendations_List"]:
            assert "Estimated_Expiry_Date" in item
            assert "Expiry_Date_Is_Default" in item
    # Test 10 - Reject malformed JSON
    # Expected result: Returns None and an error message when the AI response is invalid JSON.
    def test_process_invalid_json(self):
        result, error = self.validator.process_ai_response("{invalid json}")
        assert result is None
        assert error == "AI returned invalid JSON response."
    # Test 11 - Reject missing required field
    # Expected result: Returns an error when a recommendation is missing a required field.
    def test_process_missing_required_field(self):
        modified = copy.deepcopy(RAW_AI_RESPONSE)
        modified["Recommendations_List"][0].pop("Estimated_Calories")
        result, error = self.validator.process_ai_response(json.dumps(modified))
        assert result is None
        assert error is not None
#endregion

# =========================================================
# 2. AI PROVIDER TESTS
# Input: Abstract provider, simulated connection errors
# and simulated primary/backup model responses.
# Expected: Prevent invalid provider usage, handle missing
# configuration and switch to backup when primary fails.
# =========================================================
#region AI Provider Tests
class TestAIProvider:
    # Test 12 - Prevent direct instantiation of abstract provider
    # Expected result: Raises TypeError because the abstract generate method is not implemented.
    def test_ai_provider_is_abstract(self):
        with pytest.raises(TypeError):
            AIProvider()
    # Test 13 - Handle missing API configuration
    # Expected result: Returns False and an error message without raising an exception.
    def test_missing_api_configuration(self, monkeypatch):
        provider = OpenRouterProvider()
        def raise_config_error():
            raise ValueError("API_KEY not found in environment file")
        monkeypatch.setattr(provider, "check_api_conn", raise_config_error)
        connected, message = provider.check_connection()
        assert connected is False
        assert "API_KEY" in message
    # Test 14 - Switch to backup after primary model failure
    # Expected result: Primary failure triggers the backup model, which returns a valid response.
    def test_primary_model_fallback(self, monkeypatch):
        provider = OpenRouterProvider()
        validator = AIResponseValidator()
        client = MagicMock()
        primary_response = SimpleNamespace(choices=[])
        backup_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(RAW_AI_RESPONSE)))],
            model="backup-model")
        client.with_options.return_value = client
        client.chat.completions.create.side_effect = [primary_response, backup_response]
        monkeypatch.setattr(provider, "_create_ai_client", lambda: client)
        monkeypatch.setattr(provider, "_get_ai_model", lambda model_type: "primary-model" if model_type == "AI_MODEL" else "backup-model")
        monkeypatch.setenv("MAX_RETRIES", "0")
        result, error = provider.generate("Test prompt", validator.get_recommendation_schema(), grocery_list, validator)
        assert error is None
        assert result is not None
        assert client.chat.completions.create.call_count == 2
        models_used = [call.kwargs["model"] for call in client.chat.completions.create.call_args_list]
        assert models_used == ["primary-model", "backup-model"]
#endregion

# =========================================================
# 3. AI MANAGER INTEGRATION
# Input: Household data, consumption history, fridge stock,
# grocery list and a simulated AI response.
# Expected: Process the complete recommendation workflow
# without an API connection and preserve the output format.
# =========================================================
#region AI Manager Integration
class TestAIManager:
    # Test 15 - Generate recommendations using a mock provider
    # Expected result: Returns valid recommendations, preserves grocery-list integrity and produces correct calorie totals.
    def test_ai_manager_mock_recommendations(self):
        provider = MockAIProvider(json.dumps(RAW_AI_RESPONSE))
        manager = AIManager(provider)
        result, error = manager.get_ai_recommendations(household_info, history, fridge, grocery_list, "none", 7)
        assert error is None
        assert result is not None
        assert len(result["Recommendations_List"]) == len(grocery_list)
        validator = AIResponseValidator()
        assert validator.check_ai_output(result["Recommendations_List"], grocery_list) is True
        assert result["Total_Planned_Estimated_Calories"] == RAW_AI_RESPONSE["Total_Planned_Estimated_Calories"]
        assert result["Total_Estimated_Calories"] == RAW_AI_RESPONSE["Total_Estimated_Calories"]
        expected_fields = {
            "Item_Name", "Planned_Quantity", "Unit", "Recommended_Quantity",
            "Estimated_Consumption_Rate", "Planned_Estimated_Calories",
            "Estimated_Calories", "Estimated_Expiration_Days",
            "Estimated_Expiry_Date", "Expiry_Date_Is_Default"
        }
        for item in result["Recommendations_List"]:
            assert set(item) == expected_fields
#endregion

# =========================================================
# 3. AGE CATEGORY MAPPING
# Input: a person's age.
# Expected: map the age to the correct calorie-table category.
# =========================================================

def test_age_mapping():
    cases = [
        (0, 0),
        (18, 18),
        (19, 19),
        (30, 30),
        (31, 30),
        (59, 30),
        (60, 60),
        (100, 60),
    ]

    for age, expected in cases:
        assert logic.get_age_from_KCAL(age) == expected


# =========================================================
# 4. FAMILY WEEKLY CALORIE CALCULATION
# Input: two family members and daily calorie requirements.
# Male age 20 maps to age 19: 2,000 calories/day.
# Female age 35 maps to age 30: 2,200 calories/day.
# Expected: (2,000 + 2,200) x 7 = 29,400 calories/week.
# =========================================================

def test_family_weekly_calories():
    family = [
        {"Age": 20, "Gender": "Male"},
        {"Age": 35, "Gender": "Female"},
    ]
    kcal_table = {
        19: {"Male": 2000, "Female": 1800},
        30: {"Male": 2500, "Female": 2200},
        60: {"Male": 2000, "Female": 1800},
    }
    result = logic.calculate_family_kcal(family, 7, kcal_table)
    assert result == 29400

# =========================================================
# 5. CALORIE SURPLUS
# Input: estimated calories and family weekly calorie needs.
# Mocking: replace file reading and the family-calorie function
# so the test uses controlled sample data.
# Expected: True only when estimated calories exceed the need.
# =========================================================
def run_calorie_test(calories, weekly_need):
    database = {"household_info": []}
    with patch.object(logic, "calculate_family_kcal", return_value=weekly_need):
        result, message = logic.calories_surplus(database, calories, 7)
    return result

def test_calories_above_weekly_need():
    # 14,001 exceeds 14,000, so a surplus exists.
    assert run_calorie_test(14001, 14000) is True

def test_calories_equal_weekly_need():
    # Exactly meeting the need is not considered a surplus.
    assert run_calorie_test(14000, 14000) is False

def test_calories_below_weekly_need():
    # 13,999 is below the family's weekly need.
    assert run_calorie_test(13999, 14000) is False

# =========================================================
# 6. EXPIRY RISK
# Input: consumption rate, planned quantity and expiry date.
# The date is fixed at 9 October 2026 to make results repeatable.
# Expected: True if estimated consumption finishes after expiry;
#           False if the food should be consumed before expiry.
# =========================================================
@patch.object(logic, "date")
def test_expiry_risk_true(mock_date):
    mock_date.today.return_value = CAPTURE_DATE
    item = copy.deepcopy(AI_RECOMMENDATIONS[0])
    item["Estimated_Consumption_Rate"] = 0.5
    result = logic.risk_of_expiry(item, 3)
    assert result[0] is True
    assert result[1] is not None
    assert AI_RECOMMENDATIONS[0]["Estimated_Consumption_Rate"] == 0

@patch.object(logic, "date")
def test_expiry_risk_false(mock_date):
    mock_date.today.return_value = CAPTURE_DATE
    item = copy.deepcopy(AI_RECOMMENDATIONS[0])
    item["Estimated_Consumption_Rate"] = 7
    result = logic.risk_of_expiry(item, 1)
    assert result == (False, None)

def test_zero_consumption_rate():
    for item in AI_RECOMMENDATIONS:
        assert item["Estimated_Consumption_Rate"] == 0
        assert logic.risk_of_expiry(item, item["Planned_Quantity"]) == (False, None)

def test_negative_consumption_rate():
    item = copy.deepcopy(AI_RECOMMENDATIONS[0])
    item["Estimated_Consumption_Rate"] = -1
    assert logic.risk_of_expiry(item, 3) == (False, None)
# =========================================================
# 7. UNDER-BUY EVALUATION
# Input: whether calorie surplus and expiry risk exist.
# Expected: under_buy() runs only when both values are False.
# Mocking: prevent the real functions and advice from running.
# =========================================================
def test_no_surplus_no_expiry_allows_underbuy():
    assert logic.should_evaluate_underbuy(False, False) is True

def test_surplus_only_skips_underbuy():
    assert logic.should_evaluate_underbuy(True, False) is False

def test_expiry_only_skips_underbuy():
    assert logic.should_evaluate_underbuy(False, True) is False

def test_surplus_and_expiry_skip_underbuy():
    assert logic.should_evaluate_underbuy(True, True) is False

# =========================================================
# 8. TEST THE UNDER_BUY FUNCTION
# Input: planned quantity, consumption rate, expiry date,
#        and next purchase date.
# Expected: correct advice and top-up amount.
# Tests execute the REAL under_buy() function. 
# Only the date and confidence-score calculation
# are controlled where needed.
# =========================================================
@patch.object(logic, "date")
def test_under_buy_calculates_top_up(mock_date):
    mock_date.today.return_value = CAPTURE_DATE
    item = copy.deepcopy(AI_RECOMMENDATIONS[0])
    item["Estimated_Consumption_Rate"] = 7
    result = logic.under_buy(item, "2026-10-20", 3)
    assert result[0] is True
    assert "milk" in result[1]
    assert "recommended to buy more" in result[1]
    assert AI_RECOMMENDATIONS[0]["Estimated_Consumption_Rate"] == 0

@patch.object(logic, "date")
def test_under_buy_sufficient_stock(mock_date):
    mock_date.today.return_value = CAPTURE_DATE
    item = copy.deepcopy(AI_RECOMMENDATIONS[0])
    item["Estimated_Consumption_Rate"] = 7
    result = logic.under_buy(item, "2026-10-20",10)
    assert result == (False, None)

def test_under_buy_handles_zero_consumption():
    for item in AI_RECOMMENDATIONS:
        result = logic.under_buy(item, "2026-10-20", item["Planned_Quantity"])
        assert result == (False, None)
# =========================================================
# 9. HISTORICAL DATA AVAILABILITY
# Input: Consumption history and fridge records.
# Expected: Return 0 when no history exists.
# With history, confidence should be between 0 and 100.
# =========================================================
def test_confidence_score_no_history():
    database = {"consumption_history": [], "fridge": []}
    result = logic.calculate_confidence_score("yogurt", database, 4, 0, 7, "none")
    assert result == 0.0

def test_confidence_score_using_existing_history():
    database = {"consumption_history": history, "fridge": fridge}
    result = logic.calculate_confidence_score("milk", database, AI_RECOMMENDATIONS[0]["Recommended_Quantity"], 1.0, 7, "none")
    assert 0 < result <= 100

def test_confidence_score_zero_mean_should_not_crash():
    zero_history = [
        {
            "Date_Range": 7,
            "Item_Name": "milk",
            "Quantity": 0,
            "Unit": "l",
            "Remarks": "none"
        }
    ]
    score = logic.calculate_confidence_score("milk",{"consumption_history": zero_history, "fridge": []},0, 0, 7, "none")
    assert score == 49.5
# =========================================================
# 10. CONFIDENCE SCORE REMARKS BONUS
# Input: Consumption history, AI quantity and remarks.
# Expected: Actionable remarks add a 5% bonus.
# Final confidence score cannot exceed 100%.
# =========================================================
def test_confidence_score_remarks_bonus():
    database = {"consumption_history": history, "fridge": fridge}
    qty = AI_RECOMMENDATIONS[0]["Recommended_Quantity"]
    without_bonus = logic.calculate_confidence_score("milk", database, qty, 1.0, 7, "none")
    with_bonus = logic.calculate_confidence_score("milk", database, qty, 1.0, 7, "hosting guests")
    assert with_bonus == min(100, round(without_bonus + 5, 1))

# =========================================================
# 11. AI AGREEMENT SCORE
# Input: Actual AI recommended quantity and consumption history.
# Expected: A recommendation closer to the calculated
# required quantity produces a higher confidence score.
# =========================================================
def test_confidence_score_agreement():
    database = {"consumption_history": history, "fridge": fridge}
    # Milk history: (1.5 + 1.8) / 2 = 1.65 l/week
    # Existing fridge: 1.0 l
    # Logic calculated purchase: 0.65 l
    agreement = logic.calculate_confidence_score("milk", database, 0.65, 1.0, 7, "none")
    captured_ai = logic.calculate_confidence_score("milk", database, AI_RECOMMENDATIONS[0]["Recommended_Quantity"], 1.0, 7, "none")
    assert agreement > captured_ai

# =========================================================
# 12. FINAL AI RESPONSE VALIDATION
# =========================================================
def test_final_calorie_totals_match_individual_items():
    assert SAMPLE_AI_RESPONSE["Total_Planned_Estimated_Calories"] == sum(item["Planned_Estimated_Calories"] for item in AI_RECOMMENDATIONS)
    assert SAMPLE_AI_RESPONSE["Total_Estimated_Calories"] == sum(item["Estimated_Calories"] for item in AI_RECOMMENDATIONS)

def test_final_expiry_dates_match_capture_date():
    for item in AI_RECOMMENDATIONS:
        days = item["Estimated_Expiration_Days"]
        assert days is None or (type(days) is int and days >= 0)
        assert type(item["Expiry_Date_Is_Default"]) is bool
        assert item["Expiry_Date_Is_Default"] is (days is None)
        expected = CAPTURE_DATE + timedelta(days=365 if days is None else days)
        assert item["Estimated_Expiry_Date"] == expected.isoformat()

def test_snapshot_calories_per_unit_are_consistent():
    for item in AI_RECOMMENDATIONS:
        planned = item["Planned_Quantity"]
        recommended = item["Recommended_Quantity"]

        if planned > 0 and recommended > 0:
            planned_kcal = (item["Planned_Estimated_Calories"] / planned )
            recommended_kcal = (item["Estimated_Calories"] / recommended)
            assert math.isclose(planned_kcal, recommended_kcal, rel_tol=0.05, abs_tol=1)

def test_snapshot_json_round_trip():
    assert json.loads(json.dumps(SAMPLE_AI_RESPONSE)) == SAMPLE_AI_RESPONSE