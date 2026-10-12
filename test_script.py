import copy
from datetime import date
from unittest.mock import patch
import Logic_manager as logic
import AI_manager as ai

#region Hardcoded data
# HARDCODED GROCERY LIST
GROCERY_LIST = [{"Item_Name": "milk", "Quantity": 3.0, "Unit": "l"}, {"Item_Name": "eggs", "Quantity": 6.0, "Unit": "pcs"},{"Item_Name": "rice", "Quantity": 1.0, "Unit": "kg"}]

# HARDCODED AI RECOMMENDATIONS
# These sample responses replace real AI output.
# This means the tests do not need a live API connection.

AI_RECOMMENDATIONS = [
    {
        "Item_Name": "milk",
        "Planned_Quantity": 3.0,
        "Unit": "l",
        "Recommended_Quantity": 2.0,
        "Estimated_Consumption_Rate": 2.0,
        "Planned_Estimated_Calories": 1800,
        "Estimated_Calories": 1200,
        "Estimated_Expiration_Days": 7
    },
    {
        "Item_Name": "eggs",
        "Planned_Quantity": 6.0,
        "Unit": "pcs",
        "Recommended_Quantity": 8.0,
        "Estimated_Consumption_Rate": 7.0,
        "Planned_Estimated_Calories": 420,
        "Estimated_Calories": 560,
        "Estimated_Expiration_Days": 14
    },
    {
        "Item_Name": "rice",
        "Planned_Quantity": 1.0,
        "Unit": "kg",
        "Recommended_Quantity": 1.0,
        "Estimated_Consumption_Rate": 0.5,
        "Planned_Estimated_Calories": 3500,
        "Estimated_Calories": 3500,
        "Estimated_Expiration_Days": 365
    }
]

SAMPLE_AI_RESPONSE = {
    "Recommendations_List": AI_RECOMMENDATIONS,
    "Total_Planned_Estimated_Calories": 5720,
    "Total_Estimated_Calories": 5260
}
#endregion

# =========================================================
# 1. AI RECOMMENDATION HANDLING
# Input: planned quantity, recommended quantity and reason.
# Expected: correct over/under/good classification and advice.
# =========================================================
def test_all_hardcoded_ai_recommendations():
    assert ai.check_ai_output(AI_RECOMMENDATIONS,GROCERY_LIST) is True

# =========================================================
# 2. QUANTITY COMPARISON BOUNDARIES
# Input: planned quantity and AI-recommended quantity.
# Expected: over if planned is higher, under if lower,
#           and good if both quantities are equal.
# =========================================================

def test_ai_output_wrong_order():
    reversed_list = AI_RECOMMENDATIONS[::-1]
    assert ai.check_ai_output(reversed_list, GROCERY_LIST) is False

def test_ai_output_changed_quantity():
    modified = copy.deepcopy(AI_RECOMMENDATIONS)
    modified[0]["Planned_Quantity"] = 5.0
    assert ai.check_ai_output(modified, GROCERY_LIST) is False

def test_ai_output_changed_unit():
    modified = copy.deepcopy(AI_RECOMMENDATIONS)
    modified[0]["Unit"] = "kg"
    assert ai.check_ai_output(modified, GROCERY_LIST) is False

def test_ai_output_missing_item():
    modified = AI_RECOMMENDATIONS[:-1]
    assert ai.check_ai_output(modified, GROCERY_LIST) is False

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

    result = logic.calculate_family_weekly_kcal(family, kcal_table)

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
    with patch.object(logic,"calculate_family_weekly_kcal",return_value=weekly_need):
        result, message = logic.calories_surplus(database, calories)
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
    mock_date.today.return_value = date(2026, 10, 9)

    result = logic.risk_of_expiry(
        estimated_consumption_rate=1,
        planned_quantity=100,
        item_expiry_date="2026-10-10",
        item_name="Milk",
        unit="l"
    )
    assert result[0] is True
    assert result[1] is not None

@patch.object(logic, "date")
def test_expiry_risk_false(mock_date):
    mock_date.today.return_value = date(2026, 10, 9)
    result = logic.risk_of_expiry(
        estimated_consumption_rate=7,
        planned_quantity=1,
        item_expiry_date="2026-12-31",
        item_name="Milk",
        unit="l"
    )
    assert result == (False, None)

def test_zero_consumption_rate():
    # No consumption means the function cannot estimate
    # how many days the food will take to finish.
    result = logic.risk_of_expiry(0, 3, "2026-12-31", "Milk", "l")
    assert result == (False, None)

def test_negative_consumption_rate():
    # A negative rate is invalid for estimating consumption.
    result = logic.risk_of_expiry(-1, 3, "2026-12-31", "Milk", "l")
    assert result == (False, None)

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
    mock_date.today.return_value = date(2026, 10, 9)

    result = logic.under_buy(
        item_name="Milk",
        planned_quantity=3,
        item_expiry_date="2026-10-20",
        next_purchase_date="2026-10-18",
        estimated_consumption_rate=7
    )
    assert result[0] is True
    assert "Milk" in result[1]
    assert "9.0" in result[1]

@patch.object(logic, "date")
def test_under_buy_skips_advice_if_food_expires_first(mock_date):
    mock_date.today.return_value = date(2026, 10, 9)

    result = logic.under_buy(
        item_name="Milk",
        planned_quantity=3,
        item_expiry_date="2026-10-10",
        next_purchase_date="2026-10-18",
        estimated_consumption_rate=7
    )
    assert result == (False, None)

def test_under_buy_handles_zero_consumption():
    result = logic.under_buy(
        item_name="Milk",
        planned_quantity=3,
        item_expiry_date="2026-10-20",
        next_purchase_date="2026-10-18",
        estimated_consumption_rate=0
    )
    assert result == (False, None)
# =========================================================
# 9. HISTORICAL DATA COMPLETENESS
# Input: consumption history and fridge records.
# Only matching item names with Remarks == "None" count.
# Expected: 3 valid Milk records out of 3 + 8 = 11.
# =========================================================

def test_no_history_completeness():
    # No records means no historical completeness.
    result = logic.calculate_historical_data_completeness(
        "Milk", [], []
    )
    assert result == 0

def test_history_completeness_matching_records():
    history = [
        {"Item_Name": "Milk", "Remarks": "None"},
        {"Item_Name": "MILK", "Remarks": "None"},
        {"Item_Name": "Milk", "Remarks": "Birthday"},
        {"Item_Name": "Rice", "Remarks": "None"},
    ]

    fridge = [
        {"Item_Name": "Milk", "Remarks": "None"}
    ]

    # Two Milk history records and one Milk fridge record qualify.
    # "Birthday" is excluded because its remark is not "None".
    result = logic.calculate_historical_data_completeness(
        "Milk", history, fridge
    )

    assert abs(result - (3 / 11)) < 1e-9


# =========================================================
# 10. DATA VARIABILITY SCORE
# Input: historical quantities for the same item.
# Expected: consistent quantities score 1.0.
# The zero-mean case checks the function's special handling
# when the average quantity is zero.
# =========================================================

def test_standard_deviation_consistent_values():
    history = [
        {"Item_Name": "Milk", "Quantity": 2, "Remarks": "None"},
        {"Item_Name": "Milk", "Quantity": 2, "Remarks": "None"},
    ]

    result = logic.calculate_data_standard_deviation(
        "Milk", history, []
    )

    assert result == 1.0


def test_standard_deviation_zero_mean():
    history = [
        {"Item_Name": "Milk", "Quantity": 0, "Remarks": "None"},
        {"Item_Name": "Milk", "Quantity": 0, "Remarks": "None"},
    ]

    result = logic.calculate_data_standard_deviation(
        "Milk", history, []
    )

    assert result == 1.0


# =========================================================
# 11. CONFIDENCE SCORE
# Input: a mocked variability score of 0.8 and completeness 
# score of 0.5.
# Expected: 0.8 x 0.5 x 100 = 40.0.
# Mocking ensures this test checks the combination formula,
# rather than recalculating the underlying historical data.
# =========================================================
def test_confidence_score():
    database = {
        "consumption_history": [],
        "fridge": []
    }
    with patch.object(logic,"calculate_data_standard_deviation",return_value=0.8
    ), patch.object(logic,"calculate_historical_data_completeness",return_value=0.5
    ):
        result = logic.calculate_confidence_score( "Milk", database)
    assert result == 40.0