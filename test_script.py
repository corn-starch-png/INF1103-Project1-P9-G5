import copy
import json
import pytest
import math
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from modules.ai.AI_manager import AIManager, AIResponseValidator
from modules.ai.AIProvider import AIProvider
from modules.ai.OpenRouterProvider import OpenRouterProvider
from modules.ai.MockAIProvider import MockAIProvider
from datetime import date, timedelta
from modules.core.AIRecData import AIRecData
from modules.core.Cart import Cart
from modules.core.CartItem import CartItem
from modules.core.ConsumptionHistory import ConsumptionHistory
from modules.core.ConsumptionRecord import ConsumptionRecord
from modules.core.Fridge import Fridge
from modules.core.FridgeItem import FridgeItem
from modules.core.Household import Household
from modules.core.Person import Person
from modules.logic.AnalysisContext import AnalysisContext
from modules.logic.BonusCalculator import BonusCalculator
from modules.logic.CaloriesSurplusAnalyzer import CaloriesSurplusAnalyzer
from modules.logic.CartEvaluator import CartEvaluator
from modules.logic.ConfidenceCalculator import ConfidenceCalculator
from modules.logic.ConfidenceMetrics import ConfidenceMetrics
from modules.logic.Finding import Finding
from modules.logic.Logic_manager import Logic_manager
from modules.logic.RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer
from modules.logic.UnderBuyAnalyzer import UnderBuyAnalyzer

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
# Expected result: Returns valid recommendations, preserves
# grocery-list integrity, attaches AI data to CartItem objects
# and produces correct calorie totals.
    def test_ai_manager_mock_recommendations(self):
        provider = MockAIProvider(json.dumps(RAW_AI_RESPONSE))
        manager = AIManager(provider)
        # Convert raw dict structures into classes
        household_obj = Household()
        assert household_obj.load_dicts(household_info) == []
        history_obj = ConsumptionHistory()
        assert history_obj.load_dicts(history) == []
        fridge_obj = Fridge()
        assert fridge_obj.load_dicts(fridge) == []
        cart_obj = Cart()
        for row in grocery_list:
            cart_obj.add_item(CartItem.from_dict(row))
        # Generate recommendations using the mock provider
        result, error = manager.get_ai_recommendations(household_info=household_obj, consumption_history=history_obj, fridge_stock=fridge_obj, purchase_stock=cart_obj, remarks="none", days_until_next=7)
        assert error is None
        assert result is not None
        # Verify recommendation count
        assert len(result["Recommendations_List"]) == len(grocery_list)
        # Verify recommendation identity, quantity, unit and order
        validator = AIResponseValidator()
        assert validator.check_ai_output(result["Recommendations_List"], grocery_list) is True
        # Verify calorie totals
        assert (result["Total_Planned_Estimated_Calories"] == RAW_AI_RESPONSE["Total_Planned_Estimated_Calories"])
        assert (result["Total_Estimated_Calories"] == RAW_AI_RESPONSE["Total_Estimated_Calories"])
        # Verify recommendation fields
        expected_fields = {
            "Item_Name", "Planned_Quantity", "Unit", "Recommended_Quantity",
            "Estimated_Consumption_Rate", "Planned_Estimated_Calories", "Estimated_Calories",
            "Estimated_Expiration_Days", "Estimated_Expiry_Date", "Expiry_Date_Is_Default"
        }
        for recommendation in result["Recommendations_List"]:
            assert set(recommendation) == expected_fields
        # Verify AI recommendations are attached to CartItem objects
        cart_items = cart_obj.get_items()
        for cart_item, recommendation in zip(cart_items, result["Recommendations_List"]):
            assert cart_item.is_enhanced() is True
            assert (cart_item.ai_data.recommended_qty == recommendation["Recommended_Quantity"])
            assert (cart_item.ai_data.consumption_rate == recommendation["Estimated_Consumption_Rate"])
            assert (cart_item.ai_data.est_expiry_date == recommendation["Estimated_Expiry_Date"])
#endregion

# =========================================================
# 4. LOGIC MANAGER TESTS
# Input: Household, cart, fridge, consumption history,
# AI recommendation data and analysis context.
# Expected: Verify the new object-oriented logic classes,
# calorie calculations, expiry risk, under-buy decisions,
# confidence scores and recommendation integration.
# =========================================================
#region Logic Manager Test Fixtures
@pytest.fixture
def make_context():
    # Helper fixture - Create a reusable analysis context
    # Expected: Provide valid core objects without API calls.
    def factory(quantity=3.0, weekly_rate=7.0, fridge_quantity=1.0, expiry_days=20, days_until_next=7, 
                total_calories=0, remarks="none", history_quantities=(7.0, 7.0)):
        # Household
        household = Household()
        household.add_member(Person(1, "TestUser", 20, "Male", "none"))
        household.add_member(Person(2, "Alice", 35, "Female", "none"))
        # Grocery cart with AI recommendation data
        cart = Cart(remarks=remarks)
        item = CartItem("milk", quantity, "l")
        item.set_ai_data(recommended_qty=quantity, consumption_rate=weekly_rate, 
                         est_expiry_date=( date.today() + timedelta(days=expiry_days)).isoformat())       
        cart.add_item(item)
        # Fridge stock
        fridge_obj = Fridge()
        if fridge_quantity > 0:
            fridge_obj.add_item(FridgeItem( "milk", fridge_quantity, "l", (date.today() - timedelta(days=1)).isoformat(), 
                                           (date.today() + timedelta(days=30)).isoformat(), "none"))
        # Consumption history
        consumption_history = ConsumptionHistory()
        for amount in history_quantities:
            consumption_history.add_record(ConsumptionRecord( "milk", amount, "l", 7, "none"))
        # Analysis context
        ctx = AnalysisContext(cart=cart, household=household, fridge=fridge_obj, history=consumption_history, 
                              total_est_calories=total_calories, next_purchase_date=days_until_next)        
        return item, ctx
    return factory
#endregion

#region Analysis Context Tests
class TestAnalysisContext:
    # Test 16 - Verify total item quantity
    # Expected: Total includes quantities from both cart and fridge.
    def test_total_items_includes_fridge_and_cart(self, make_context):
        _, ctx = make_context(quantity=3, fridge_quantity=2)
        assert ctx.get_total_items("milk") == pytest.approx(5)
    # Test 17 - Add valid findings
    # Expected: Valid Finding objects are added to the context.
    def test_update_findings_appends_valid_findings(self, make_context):
        _, ctx = make_context()
        finding = Finding("CaloriesSurplus", False, "No surplus")
        ctx.update_findings([finding])
        assert ctx.findings == [finding]
    # Test 18 - Reject invalid findings
    # Expected: Raise TypeError for invalid input types.
    @pytest.mark.parametrize("invalid", [None, {}, [True], ["text"]])
    def test_update_findings_rejects_invalid_values(self, make_context, invalid):
        _, ctx = make_context()
        with pytest.raises(TypeError): ctx.update_findings(invalid)
#endregion

#region Calories Surplus Analyzer Tests
class TestCaloriesSurplusAnalyzer:
    # Test 19 - Verify age category mapping
    # Expected: Ages map to the correct calorie-table categories.
    @pytest.mark.parametrize("age, expected", [ (1, 1), (18, 18), (19, 19), (29, 19), (30, 30), (59, 30), (60, 60), (100, 60)])
    def test_age_brackets(self, age, expected):
        analyzer = CaloriesSurplusAnalyzer()
        result = analyzer._CaloriesSurplusAnalyzer__get_age_from_KCAL(age)
        assert result == expected
    # Test 20 - Calculate family weekly calories
    # Expected: Male aged 20 and female aged 35 require
    # 33145 kcal over seven days.
    def test_family_calories_for_seven_days(self, make_context):
        _, ctx = make_context()
        analyzer = CaloriesSurplusAnalyzer()
        result = (analyzer._CaloriesSurplusAnalyzer__calculate_family_kcal( 7, ctx.household))
        assert result == 33145
    # Test 21 - Detect calorie surplus boundaries
    # Expected:
    # Above requirement = True
    # Equal requirement = False
    # Below requirement = False
    @pytest.mark.parametrize("calories, expected", [ (33146, True), (33145, False), (33144, False)])
    def test_surplus_boundary(self, make_context, calories, expected):
        _, ctx = make_context(total_calories=calories)
        finding = CaloriesSurplusAnalyzer().analyze(ctx)
        assert isinstance(finding, Finding)
        assert finding.analyzer_name == "CaloriesSurplus"
        assert finding.result is expected
        assert "kcal" in finding.message
#endregion

#region Risk Of Expiry Analyzer Tests
class TestRiskOfExpiryAnalyzer:
    # Test 22 - Detect food expiry risk
    # Expected: True when stock cannot be consumed before expiry.
    def test_risk_when_stock_outlasts_expiry(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=1, weekly_rate=1, expiry_days=3)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert finding.analyzer_name == "RiskOfExpiry"
        assert finding.result is True
        assert "milk" in finding.message
    # Test 23 - Verify no expiry risk
    # Expected: False when stock can be consumed before expiry.
    def test_no_risk_when_stock_consumed_before_expiry(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=1, weekly_rate=7, expiry_days=20)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert finding.result is False
        assert finding.message is None
    # Test 24 - Handle zero or negative consumption rate
    # Expected: Return a Finding with result False.
    # Verify the analyzer returns a false Finding when the consumption rate is zero or negative.
    @pytest.mark.parametrize("rate", [0, -1])
    def test_nonpositive_rate_returns_false_finding(self, make_context, rate):
        item, ctx = make_context(weekly_rate=rate)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert isinstance(finding, Finding)
        assert finding.result is False
        assert finding.message is None
#endregion

#region Under Buy Analyzer Tests
class TestUnderBuyAnalyzer:
    # Test 25 - Verify under-buy evaluation conditions
    # Expected:
    # No calorie surplus and no expiry risk = Evaluate
    # Calorie surplus or expiry risk = Skip
    @pytest.mark.parametrize("surplus, expiry_risk, should_buy", [ (False, False, True), (True, False, False), (False, True, False), (True, True, False)])
    def test_analysis_gate(self, make_context, surplus, expiry_risk, should_buy):
        item, ctx = make_context(quantity=1, fridge_quantity=1, weekly_rate=7)
        ctx.update_findings([Finding( "CaloriesSurplus", surplus, "test" )])
        if expiry_risk:
            ctx.update_findings([Finding( "RiskOfExpiry", True, "milk will expire")])
        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.analyzer_name == "UnderBuy"
        assert finding.result is should_buy
    # Test 26 - Verify sufficient existing stock
    # Expected: No additional quantity is recommended.
    def test_no_top_up_when_stock_is_sufficient(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=10, weekly_rate=7)
        ctx.update_findings([Finding("CaloriesSurplus", False, "test")])
        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.result is False
        assert finding.message is None
    # Test 27 - Handle zero consumption
    # Expected: No additional quantity is recommended.
    def test_zero_consumption_never_requests_more(self, make_context):
        item, ctx = make_context(weekly_rate=0)
        ctx.update_findings([Finding("CaloriesSurplus", False, "test")])
        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.result is False
#endregion

#region Confidence Calculator Tests
class TestConfidenceCalculator:
    # Test 28 - Calculate confidence without consumption history
    # Expected: Return 0.0 when no historical records exist.
    def test_no_history_returns_zero(self, make_context):
        item, ctx = make_context(history_quantities=())
        result = ConfidenceCalculator().calculate_confidence_score(item, ctx)
        assert result == 0.0
    # Test 29 - Reject items without AI data
    # Expected: Raise NotImplementedError.
    def test_item_without_ai_data_is_rejected(self, make_context):
        _, ctx = make_context()
        item = CartItem("milk", 2, "l")
        with pytest.raises(NotImplementedError):
            ConfidenceCalculator().calculate_confidence_score(item, ctx)
    # Test 30 - Handle zero-mean consumption history
    # Expected: Return 49.5 without division-by-zero errors.
    def test_zero_history_does_not_divide_by_zero(self, make_context):
        item, ctx = make_context(quantity=1, fridge_quantity=0, history_quantities=(0,))
        item.set_ai_data(recommended_qty=0, consumption_rate=0, est_expiry_date=item.ai_data.est_expiry_date)
        result = ConfidenceCalculator().calculate_confidence_score(item, ctx)
        assert result == 49.5
    # Test 31 - Verify AI recommendation agreement
    # Expected: A recommendation closer to historical
    # consumption requirements produces higher confidence.
    def test_agreement_improves_confidence(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=1, history_quantities=(7, 7) )
        calculator = ConfidenceCalculator()
        first_score = calculator.calculate_confidence_score(item, ctx)
        # Historical requirement:
        # 7l consumed per week - 1l existing stock = 6l needed.
        item.set_ai_data(recommended_qty=6, consumption_rate=7, est_expiry_date=item.ai_data.est_expiry_date)        
        second_score = calculator.calculate_confidence_score(item, ctx)
        assert second_score > first_score
    # Test 32 - Verify actionable remarks bonus
    # Expected: Relevant remarks increase confidence by 5
    # without exceeding the maximum score of 100.
    def test_actionable_remarks_bonus(self, make_context):
        item, ctx = make_context(remarks="none")
        calculator = ConfidenceCalculator()
        baseline = calculator.calculate_confidence_score(item, ctx)
        ctx.cart.set_remarks("hosting guests")
        with_bonus = calculator.calculate_confidence_score(item, ctx)
        assert with_bonus == min(100, round(baseline + 5, 1))
    # Test 33 - Verify bonus keyword categories
    # Expected:
    # Full bonus = 5
    # Partial bonus = 2.5
    # No actionable remarks = 0
    @pytest.mark.parametrize("remarks, expected", [ ("none", 0), ("", 0), ("hosting guests", 5), ("eating out", 2.5), ("ordinary note", 0)])
    def test_bonus_keywords(self, remarks, expected):
        result = BonusCalculator().bonus(remarks)
        assert result == expected
    # Test 34 - Handle zero-mean consistency calculation
    # Expected: Return 0.0 without division-by-zero errors.
    def test_zero_mean_consistency(self):
        result = ConfidenceMetrics().consistency_score([0.0, 0.0])
        assert result == 0.0
#endregion

#region Logic Manager Integration Tests
class TestLogicManagerIntegration:
    # Test 35 - Verify CartEvaluator integration
    # Expected: Generate calorie surplus, expiry risk and
    # under-buy findings for each cart item.
    def test_cart_evaluator_produces_three_findings_per_item(self, make_context):
        _, ctx = make_context(quantity=3, fridge_quantity=1, weekly_rate=7, expiry_days=20)
        findings = CartEvaluator().evaluate(ctx)
        expected = ["CaloriesSurplus", "RiskOfExpiry", "UnderBuy"]
        assert [f.analyzer_name for f in findings] == expected
        assert ctx.findings == findings
    # Test 36 - Verify recommendation output formatting
    # Expected: Display valid findings and exclude false findings.
    def test_manager_gets_findings(self, make_context):
        _, ctx = make_context()
        manager = Logic_manager()
        manager.process_recommendations(ctx)
        findings = manager.get_recommedations("RiskOfExpiry", True)
        assert isinstance(findings, list)
        assert all(isinstance(message, str) for message in findings)
    # Test 37 - Verify confidence scores are attached to cart items
    # Expected: Each AI-enhanced cart item receives a valid
    # confidence score between 0 and 100.
    def test_manager_adds_confidence_to_cart(self, make_context):
        item, ctx = make_context(quantity=6, fridge_quantity=1)
        Logic_manager().add_confidence_score(ctx)
        assert 0 < item.ai_data.confidence_score <= 100
#endregion

# =========================================================
# 5. AI OUTPUT SNAPSHOT TESTS
# Input: Previously captured AI recommendation data.
# Expected: Verify calorie totals, expiry-date calculations,
# nutritional consistency and JSON serialization.
# =========================================================
#region AI Output Snapshot Tests
class TestAIOutputSnapshot:
    # Test 38 - Verify final calorie totals
    # Expected result: Both calorie totals equal the sums of their respective item-level values.
    def test_final_calorie_totals_match_individual_items(self):
        assert SAMPLE_AI_RESPONSE["Total_Planned_Estimated_Calories"] == sum(item["Planned_Estimated_Calories"] for item in AI_RECOMMENDATIONS)
        assert SAMPLE_AI_RESPONSE["Total_Estimated_Calories"] == sum(item["Estimated_Calories"] for item in AI_RECOMMENDATIONS)
    # Test 39 - Verify estimated expiry dates
    # Expected result: Each expiry date matches the captured date plus its estimated expiration days.
    def test_final_expiry_dates_match_capture_date(self):
        for item in AI_RECOMMENDATIONS:
            days = item["Estimated_Expiration_Days"]
            assert days is None or (type(days) is int and days >= 0)
            assert type(item["Expiry_Date_Is_Default"]) is bool
            assert item["Expiry_Date_Is_Default"] is (days is None)
            expected = CAPTURE_DATE + timedelta(days=365 if days is None else days)
            assert item["Estimated_Expiry_Date"] == expected.isoformat()
    # Test 40 - Verify calorie consistency per unit
    # Expected result: Planned and recommended calorie estimates use approximately the same calories per unit.
    def test_snapshot_calories_per_unit_are_consistent(self):
        for item in AI_RECOMMENDATIONS:
            planned = item["Planned_Quantity"]
            recommended = item["Recommended_Quantity"]
            if planned > 0 and recommended > 0:
                planned_kcal = item["Planned_Estimated_Calories"] / planned
                recommended_kcal = item["Estimated_Calories"] / recommended
                assert math.isclose(planned_kcal, recommended_kcal, rel_tol=0.05, abs_tol=1)
    # Test 41 - Verify JSON serialization
    # Expected result: Converting the response into JSON and back preserves all original data.
    def test_snapshot_json_round_trip(self):
        assert json.loads(json.dumps(SAMPLE_AI_RESPONSE)) == SAMPLE_AI_RESPONSE
#endregion

