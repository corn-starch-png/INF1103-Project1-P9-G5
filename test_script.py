import io
from datetime import date
from unittest.mock import patch
import Logic_manager as logic

# =========================================================
# HARDCODED AI RECOMMENDATIONS
# These sample responses replace real AI output.
# This means the tests do not need a live API connection.
# =========================================================

AI_RECOMMENDATIONS = [
    {
        "item": "Milk",
        "planned_quantity": 3,
        "unit": "l",
        "recommended_quantity": 1.7,
        "consumption_rate": 2.0,
        "estimated_calories": 1020,
        "reason": "Expired milk stock leaves no usable supply."
    },
    {
        "item": "Eggs",
        "planned_quantity": 12,
        "unit": "pcs",
        "recommended_quantity": 7,
        "consumption_rate": 7.7,
        "estimated_calories": 490,
        "reason": "Historical consumption indicates 7 eggs are needed."
    },
    {
        "item": "Chicken",
        "planned_quantity": 0.5,
        "unit": "kg",
        "recommended_quantity": 1.0,
        "consumption_rate": 1.2,
        "estimated_calories": 1650,
        "reason": "Expired chicken stock leaves no usable supply."
    },
    {
        "item": "Fanta",
        "planned_quantity": 30,
        "unit": "l",
        "recommended_quantity": 30,
        "consumption_rate": 1.2,
        "estimated_calories": 13500,
        "reason": "A house party increases drink demand."
    },
    {
        "item": "Apple",
        "planned_quantity": 13,
        "unit": "pcs",
        "recommended_quantity": 3,
        "consumption_rate": 2.8,
        "estimated_calories": 240,
        "reason": "Reduced household consumption lowers demand."
    },
    {
        "item": "Rice",
        "planned_quantity": 2,
        "unit": "kg",
        "recommended_quantity": 0,
        "consumption_rate": 0.6,
        "estimated_calories": 0,
        "reason": "Existing rice stock is sufficient."
    },
]


# =========================================================
# 1. AI RECOMMENDATION HANDLING
# Input: planned quantity, recommended quantity and reason.
# Expected: correct over/under/good classification and advice.
# =========================================================

def test_all_hardcoded_ai_recommendations():
    expected_results = [
        "over", "over", "under", "good", "over", "over"
    ]

    for recommendation, expected in zip(
        AI_RECOMMENDATIONS, expected_results
    ):
        user_input = {
            "item": recommendation["item"],
            "unit": recommendation["unit"],
            "planned_quantity": recommendation["planned_quantity"],
        }

        result = logic.give_recommendation(user_input, recommendation)

        # Check the classification against the expected result.
        assert result["result"] == expected

        # Check that the reason from the AI response is preserved.
        assert result["advice"] == recommendation["reason"]

        # These fields are currently unimplemented in the function.
        assert result["waste_risk"] is None
        assert result["confidence_score"] is None


# =========================================================
# 2. QUANTITY COMPARISON BOUNDARIES
# Input: planned quantity and AI-recommended quantity.
# Expected: over if planned is higher, under if lower,
#           and good if both quantities are equal.
# =========================================================

def test_quantity_comparison_boundaries():
    cases = [
        (0, 2, "under"),       # Planned quantity is zero.
        (1.99, 2, "under"),    # Planned quantity is slightly lower.
        (2, 2, "good"),        # Both quantities are equal.
        (2.01, 2, "over"),     # Planned quantity is slightly higher.
        (0, 0, "good"),        # Both quantities are zero.
    ]

    for planned, recommended, expected in cases:
        assert logic.check_over_under(planned, recommended) == expected


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
        (30, 19),
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
    with patch(
        "builtins.open",
        return_value=io.StringIO('{"household_info": []}')
    ), patch.object(
        logic,
        "calculate_family_weekly_kcal",
        return_value=weekly_need
    ):
        return logic.calories_surplus(calories)


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

    assert result is True


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

    assert result is False


def test_zero_consumption_rate():
    # No consumption means the function cannot estimate
    # how many days the food will take to finish.
    result = logic.risk_of_expiry(
        0, 3, "2026-12-31", "Milk", "l"
    )

    assert result is None


def test_negative_consumption_rate():
    # A negative rate is invalid for estimating consumption.
    result = logic.risk_of_expiry(
        -1, 3, "2026-12-31", "Milk", "l"
    )

    assert result is None


# =========================================================
# 7. UNDER-BUY EVALUATION
# Input: whether calorie surplus and expiry risk exist.
# Expected: under_buy() runs only when both values are False.
# Mocking: prevent the real functions and advice from running.
# =========================================================

def run_underbuy_case(surplus, expiry):
    with patch.object(
        logic, "calories_surplus", return_value=surplus
    ), patch.object(
        logic, "risk_of_expiry", return_value=expiry
    ), patch.object(
        logic, "under_buy"
    ) as mock_underbuy:

        logic.evaluate_underbuy(
            item_name="Milk",
            planned_quantity=3,
            item_expiry_date="2026-11-04",
            next_purchase_date="2026-10-18",
            estimated_consumption_rate=1.37,
            unit="l",
            total_estimated_calories=15000
        )

        # Return the mock so each test can check whether
        # under_buy() was called.
        return mock_underbuy


def test_no_surplus_no_expiry_calls_underbuy():
    # Neither risk exists, so under-buy advice is allowed.
    mock = run_underbuy_case(False, False)
    mock.assert_called_once()


def test_surplus_only_skips_underbuy():
    # Calorie surplus exists, so skip under-buy advice.
    mock = run_underbuy_case(True, False)
    mock.assert_not_called()


def test_expiry_only_skips_underbuy():
    # Expiry risk exists, so skip under-buy advice.
    mock = run_underbuy_case(False, True)
    mock.assert_not_called()


def test_surplus_and_expiry_skip_underbuy():
    # Both risks exist, so skip under-buy advice.
    mock = run_underbuy_case(True, True)
    mock.assert_not_called()



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
def test_under_buy_calculates_top_up(mock_date, capsys):
    # Fix today's date so the test is repeatable.
    mock_date.today.return_value = date(2026, 10, 9)

    # Avoid reading the real database for the confidence score.
    with patch.object(
        logic, "calculate_confidence_score", return_value=80.0
    ):
        result = logic.under_buy(
            item_name="Milk",
            planned_quantity=3,
            item_expiry_date="2026-10-20",
            next_purchase_date="2026-10-18",
            estimated_consumption_rate=7
        )

    output = capsys.readouterr().out

    # Weekly consumption = 7 L.
    # Daily consumption = 7 / 7 = 1 L.
    # Planned 3 L will last 3 days.
    # Next purchase is 9 days away.
    # Quantity needed = 1 x 9 = 9 L.
    # Top-up = 9 - 3 = 6 L.

    assert result is None
    assert "Milk" in output
    assert "3 days" in output
    assert "buy 6.0 more" in output
    assert "80.0%" in output


@patch.object(logic, "date")
def test_under_buy_skips_advice_if_food_expires_first(
    mock_date, capsys
):
    mock_date.today.return_value = date(2026, 10, 9)

    with patch.object(
        logic, "calculate_confidence_score", return_value=80.0
    ):
        result = logic.under_buy(
            item_name="Milk",
            planned_quantity=3,
            item_expiry_date="2026-10-10",
            next_purchase_date="2026-10-18",
            estimated_consumption_rate=7
        )

    output = capsys.readouterr().out

    # The planned quantity takes 3 days to consume,
    # finishing on 12 October, after the 10 October expiry.
    # Therefore, no under-buy advice should be displayed.

    assert result is None
    assert output == ""


def test_under_buy_handles_zero_consumption(capsys):
    # This calls the REAL under_buy() function.
    result = logic.under_buy(
        item_name="Milk",
        planned_quantity=3,
        item_expiry_date="2026-10-20",
        next_purchase_date="2026-10-18",
        estimated_consumption_rate=0
    )

    output = capsys.readouterr().out

    assert result is None
    assert "Consumption rate is 0" in output


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
    with patch(
        "builtins.open",
        return_value=io.StringIO(
            '{"consumption_history": [], "fridge": []}'
        )
    ), patch.object(
        logic,
        "calculate_data_standard_deviation",
        return_value=0.8
    ), patch.object(
        logic,
        "calculate_historical_data_completeness",
        return_value=0.5
    ):
        result = logic.calculate_confidence_score("Milk")

    assert result == 40.0