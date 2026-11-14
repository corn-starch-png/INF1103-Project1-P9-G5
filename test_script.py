# region Imports
import copy
import json
import subprocess
import sys
import runpy
from Application import Application
from modules.repositories.DB_manager import DB_manager
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from logger import Logger, app_logger
from modules.ai.AI_manager import AIManager
from modules.ai.AIProvider import AIProvider
from modules.ai.AIResponseValidator import AIResponseValidator
from modules.ai.MockAIProvider import MockAIProvider
from modules.ai.OpenRouterProvider import OpenRouterProvider
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
from modules.logic.CartRecommender import CartRecommender
from modules.logic.ConfidenceCalculator import ConfidenceCalculator
from modules.logic.ConfidenceMetrics import ConfidenceMetrics
from modules.logic.Finding import Finding
from modules.logic.Logic_manager import Logic_manager
from modules.logic.RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer
from modules.logic.UnderBuyAnalyzer import UnderBuyAnalyzer
from modules.repositories.AppPaths import AppPaths
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.RepositoryFunctions import RepositoryFunctions
from modules.repositories.StorageErrors import SaveConflict, LocalConflict
from modules.HouseholdSession import SaveOutcome
from modules.io.IO_manager import IO_manager
# endregion

# region Test Data
CAPTURE_DATE = date(2026, 10, 13)
HOUSEHOLD_DATA = [
    {"Person_ID": 1, "Name": "TestUser", "Age": 23, "Gender": "Male", "Dietary_Restriction": "none"},
    {"Person_ID": 2, "Name": "Alice", "Age": 40, "Gender": "Female", "Dietary_Restriction": "none"},
    {"Person_ID": 3, "Name": "Bob", "Age": 18, "Gender": "Male", "Dietary_Restriction": "none"},
]
HISTORY_DATA = [
    {"Item_Name": "milk", "Quantity": 1.5, "Unit": "l", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "eggs", "Quantity": 8, "Unit": "pcs", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "rice", "Quantity": 1.0, "Unit": "kg", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "chicken", "Quantity": 0.8, "Unit": "kg", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "bananas", "Quantity": 6, "Unit": "pcs", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "milk", "Quantity": 1.8, "Unit": "l", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "eggs", "Quantity": 10, "Unit": "pcs", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "rice", "Quantity": 1.2, "Unit": "kg", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "chicken", "Quantity": 0.9, "Unit": "kg", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
    {"Item_Name": "bananas", "Quantity": 5, "Unit": "pcs", "Date_Range": 7, "Remarks": "none", "Record_Date": "2026-10-06"},
]
GROCERY_LIST = [
    {"Item_Name": "milk", "Quantity": 3, "Unit": "l"},
    {"Item_Name": "eggs", "Quantity": 2, "Unit": "pcs"},
    {"Item_Name": "rice", "Quantity": 2, "Unit": "kg"},
    {"Item_Name": "bread", "Quantity": 3, "Unit": "pcs"},
    {"Item_Name": "bananas", "Quantity": 10, "Unit": "pcs"},
    {"Item_Name": "yogurt", "Quantity": 4, "Unit": "pcs"},
]
# Raw responses contain eight item fields; the validator adds two expiry fields.
RAW_AI_RESPONSE = {
    "Recommendations_List": [
        {"Item_Name": "milk", "Planned_Quantity": 3, "Unit": "l", "Recommended_Quantity": 3, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 1800, "Estimated_Calories": 1800, "Estimated_Expiration_Days": 7},
        {"Item_Name": "eggs", "Planned_Quantity": 2, "Unit": "pcs", "Recommended_Quantity": 2, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 140, "Estimated_Calories": 140, "Estimated_Expiration_Days": 21},
        {"Item_Name": "rice", "Planned_Quantity": 2, "Unit": "kg", "Recommended_Quantity": 2, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 7000, "Estimated_Calories": 7000, "Estimated_Expiration_Days": 365},
        {"Item_Name": "bread", "Planned_Quantity": 3, "Unit": "pcs", "Recommended_Quantity": 3, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 3600, "Estimated_Calories": 3600, "Estimated_Expiration_Days": 5},
        {"Item_Name": "bananas", "Planned_Quantity": 10, "Unit": "pcs", "Recommended_Quantity": 10, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 1000, "Estimated_Calories": 1000, "Estimated_Expiration_Days": 5},
        {"Item_Name": "yogurt", "Planned_Quantity": 4, "Unit": "pcs", "Recommended_Quantity": 4, "Estimated_Consumption_Rate": 0, "Planned_Estimated_Calories": 400, "Estimated_Calories": 400, "Estimated_Expiration_Days": 7},
    ],
    "Total_Planned_Estimated_Calories": 13940,
    "Total_Estimated_Calories": 13940,
}

EXPECTED_TOP_FIELDS = {"Recommendations_List", "Total_Planned_Estimated_Calories", "Total_Estimated_Calories"}
EXPECTED_ITEM_FIELDS = {"Item_Name", "Planned_Quantity", "Unit", "Recommended_Quantity", "Estimated_Consumption_Rate", "Planned_Estimated_Calories", "Estimated_Calories", "Estimated_Expiration_Days", "Estimated_Expiry_Date", "Expiry_Date_Is_Default"}
# endregion

# =========================================================
# SHARED FIXTURES
# Input: Temporary paths, mocked services and domain objects.
# Expected: Repeatable tests without changing real user data.
# =========================================================
# region Shared Fixtures
# Redirect application log writes into a temporary file for each test.
@pytest.fixture(autouse=True)
def isolate_test_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(app_logger, "filename", str(tmp_path / "application.log"))
# Create fresh raw response data so individual tests cannot affect each other.
@pytest.fixture
def raw_response():
    return copy.deepcopy(RAW_AI_RESPONSE)
@pytest.fixture
def validator():
    return AIResponseValidator()
# Build an enhanced cart and its related analysis objects.
@pytest.fixture
def make_context():
    def factory(quantity=3.0, weekly_rate=7.0, fridge_quantity=1.0, expiry_days=20, days_until_next=7, total_calories=0, remarks="none", history_quantities=(7.0, 7.0)):
        today = date.today()
        household = Household()
        household.add_member(Person(1, "TestUser", 20, "Male", "none"))
        household.add_member(Person(2, "Alice", 35, "Female", "none"))
        cart = Cart(remarks=remarks)
        item = CartItem("milk", quantity, "l")
        item.set_ai_data(recommended_qty=quantity, consumption_rate=weekly_rate, est_expiry_date=(today + timedelta(days=expiry_days)).isoformat())
        cart.add_item(item)
        fridge_obj = Fridge()
        if fridge_quantity > 0:
            fridge_obj.add_item(FridgeItem("milk", fridge_quantity, "l", (today - timedelta(days=1)).isoformat(), (today + timedelta(days=30)).isoformat(), "none"))
        history_obj = ConsumptionHistory()
        for amount in history_quantities:
            history_obj.add_record(ConsumptionRecord("milk", amount, "l", 7, "none"))
        ctx = AnalysisContext(cart=cart, household=household, fridge=fridge_obj, history=history_obj, total_est_calories=total_calories, next_purchase_date=days_until_next)
        return item, ctx
    return factory
# Build history and fridge stock for the initial cart recommendation feature.
@pytest.fixture
def make_recommendation_context():
    def factory(history_quantities=(7,), stock=0, expired_stock=0, unit="l", age_days=0, today=None):
        today = today or date.today()
        fridge_obj = Fridge()
        history_obj = ConsumptionHistory()
        for quantity in history_quantities:
            history_obj.add_record(ConsumptionRecord("milk", quantity, unit, 7, "none", record_date=(today - timedelta(days=age_days)).isoformat()))
        if stock > 0:
            fridge_obj.add_item(FridgeItem("milk", stock, unit, (today - timedelta(days=2)).isoformat(), (today + timedelta(days=10)).isoformat(), "none"))
        if expired_stock > 0:
            fridge_obj.add_item(FridgeItem("milk", expired_stock, unit, (today - timedelta(days=3)).isoformat(), (today - timedelta(days=1)).isoformat(), "none"))
        return fridge_obj, history_obj
    return factory
# Create a complete input bundle for AI manager integration tests.
@pytest.fixture
def ai_input():
    today = date.today()
    household = Household()
    history = ConsumptionHistory()
    fridge = Fridge()
    cart = Cart()
    assert household.load_dicts(copy.deepcopy(HOUSEHOLD_DATA)) == []
    assert history.load_dicts(copy.deepcopy(HISTORY_DATA)) == []
    for name, quantity, unit in [("milk", 1, "l"), ("eggs", 6, "pcs"), ("rice", 1.5, "kg")]:
        fridge.add_item(FridgeItem(name, quantity, unit, (today - timedelta(days=2)).isoformat(), (today + timedelta(days=10)).isoformat(), "none"))
    for row in GROCERY_LIST:
        cart.add_item(CartItem.from_dict(row))
    return household, history, fridge, cart
# Configure a fake OpenAI client with no retry delays or real network calls.
@pytest.fixture
def provider_client(monkeypatch):
    provider = OpenRouterProvider()
    client = MagicMock()
    client.with_options.return_value = client
    monkeypatch.setattr(provider, "_create_ai_client", lambda: client)
    monkeypatch.setattr(provider, "_get_ai_model", lambda name: "primary-model" if name == "AI_MODEL" else "backup-model")
    monkeypatch.setenv("MAX_RETRIES", "0")
    return provider, client
# endregion

# =========================================================
# 1. AI TESTS
# Input: Raw responses, mocked providers and domain objects.
# Expected: Validate responses, handle failures and attach
# AI data before business-rule evaluation.
# =========================================================
# region AI Tests

# region AI Response Validation
class TestAIResponseValidator:
    # Test 1 - Verify the complete structure of processed AI output.
    # Expected: Exact top-level fields and ten fields per recommendation.
    def test_processed_response_has_expected_structure(self, validator, raw_response):
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert error is None
        assert set(result) == EXPECTED_TOP_FIELDS
        assert len(result["Recommendations_List"]) == len(GROCERY_LIST)
        for item in result["Recommendations_List"]:
            assert set(item) == EXPECTED_ITEM_FIELDS

    # Test 2 - Accept recommendations matching the original grocery list.
    # Expected: Names, quantities, units and ordering are preserved.
    def test_matching_grocery_list_is_accepted(self, validator, raw_response):
        assert validator.check_ai_output(raw_response["Recommendations_List"], GROCERY_LIST) is True

    # Test 3 - Reject changes to original grocery fields.
    # Expected: Modified names, quantities or units fail the integrity check.
    @pytest.mark.parametrize("field, value", [("Item_Name", "other"), ("Planned_Quantity", 5), ("Unit", "kg")])
    def test_rejects_changed_grocery_fields(self, validator, raw_response, field, value):
        raw_response["Recommendations_List"][0][field] = value
        assert validator.check_ai_output(raw_response["Recommendations_List"], GROCERY_LIST) is False

    # Test 4 - Reject recommendations returned in the wrong order.
    # Expected: Reversing the list fails the integrity check.
    def test_rejects_wrong_order(self, validator, raw_response):
        assert validator.check_ai_output(raw_response["Recommendations_List"][::-1], GROCERY_LIST) is False

    # Test 5 - Reject missing grocery recommendations.
    # Expected: Removing a recommendation fails the integrity check.
    def test_rejects_missing_item(self, validator, raw_response):
        assert validator.check_ai_output(raw_response["Recommendations_List"][:-1], GROCERY_LIST) is False

    # Test 6 - Calculate expiry dates from a controlled date.
    # Expected: Known expiration days generate correct dates and false default flags.
    def test_calculated_expiry_dates(self, validator, raw_response):
        with patch("modules.ai.AIResponseValidator.date") as mock_date:
            mock_date.today.return_value = CAPTURE_DATE
            result, error = validator.process_ai_response(json.dumps(raw_response))

        assert error is None
        for item in result["Recommendations_List"]:
            expected = CAPTURE_DATE + timedelta(days=item["Estimated_Expiration_Days"])
            assert item["Estimated_Expiry_Date"] == expected.isoformat()
            assert item["Expiry_Date_Is_Default"] is False

    # Test 7 - Reject malformed JSON.
    # Expected: Invalid JSON returns an error instead of raising an exception.
    def test_rejects_invalid_json(self, validator):
        result, error = validator.process_ai_response("{invalid json}")
        assert result is None
        assert error == "AI returned invalid JSON response."

    # Test 8 - Reject a response missing a required item field.
    # Expected: Incomplete recommendations return an error.
    def test_rejects_missing_required_field(self, validator, raw_response):
        raw_response["Recommendations_List"][0].pop("Estimated_Calories")
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert result is None
        assert error

    # Test 9 - Reject invalid numeric, unit and expiration values.
    # Expected: Each invalid value produces an error.
    @pytest.mark.parametrize("field, value", [
        ("Recommended_Quantity", -1), ("Estimated_Consumption_Rate", -1), ("Unit", "bucket"),
        ("Estimated_Expiration_Days", -1), ("Estimated_Expiration_Days", 1.5),
        ("Estimated_Expiration_Days", True), ("Estimated_Expiration_Days", 2000),
        ("Estimated_Calories", float("nan")), ("Estimated_Calories", float("inf")),])
    def test_rejects_invalid_item_values(self, validator, raw_response, field, value):
        raw_response["Recommendations_List"][0][field] = value
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert result is None
        assert error

    # Test 10 - Reject fractional quantities for whole-piece items.
    # Expected: Quantities in pcs must be whole numbers.
    def test_rejects_fractional_piece_quantity(self, validator, raw_response):
        raw_response["Recommendations_List"][1]["Recommended_Quantity"] = 1.5
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert result is None
        assert "whole" in error.lower()

    # Test 11 - Reject totals that disagree with individual calorie values.
    # Expected: Both planned and recommended calorie totals are validated.
    @pytest.mark.parametrize("field", ["Total_Planned_Estimated_Calories", "Total_Estimated_Calories"])
    def test_rejects_incorrect_calorie_totals(self, validator, raw_response, field):
        raw_response[field] += 100
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert result is None
        assert field in error

    # Test 12 - Reject inconsistent calories per unit despite matching totals.
    # Expected: Invalid nutritional consistency cannot pass through correct summation.
    def test_rejects_inconsistent_calories_per_unit(self, validator, raw_response):
        raw_response["Recommendations_List"][0]["Estimated_Calories"] += 1000
        raw_response["Total_Estimated_Calories"] += 1000
        result, error = validator.process_ai_response(json.dumps(raw_response))
        assert result is None
        assert "inconsistent" in error.lower()

    # Test 13 - Apply the documented default when expiration days are unknown.
    # Expected: Null days produce a 365-day date and a true default flag.
    def test_default_expiration_date(self, validator, raw_response):
        raw_response["Recommendations_List"][0]["Estimated_Expiration_Days"] = None
        with patch("modules.ai.AIResponseValidator.date") as mock_date:
            mock_date.today.return_value = CAPTURE_DATE
            result, error = validator.process_ai_response(json.dumps(raw_response))

        assert error is None
        item = result["Recommendations_List"][0]
        assert item["Estimated_Expiry_Date"] == (CAPTURE_DATE + timedelta(days=365)).isoformat()
        assert item["Expiry_Date_Is_Default"] is True
# endregion

# region AI Provider
class TestAIProvider:
    # Test 14 - Prevent direct construction of the abstract provider.
    # Expected: AIProvider cannot be instantiated without implementing its contract.
    def test_ai_provider_is_abstract(self):
        with pytest.raises(TypeError) as captured:
            AIProvider()
        print(f"Expected error: {captured.value}")

    # Test 15 - Detect missing configuration before contacting the API.
    # Expected: A clear error is returned and no HTTP request occurs.
    @pytest.mark.parametrize("missing_variable", ["API_KEY", "API_CONN_URL"])
    def test_missing_api_configuration(self, monkeypatch, missing_variable):
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("API_CONN_URL", "https://test.invalid/key")
        monkeypatch.delenv(missing_variable, raising=False)

        with patch("modules.ai.OpenRouterProvider.requests.get") as request:
            connected, message = OpenRouterProvider().check_connection()

        assert connected is False
        assert missing_variable in message
        request.assert_not_called()

    # Test 16 - Switch to the backup model after primary failure.
    # Expected: The backup result is returned after both models are attempted in order.
    def test_primary_model_fallback(self, provider_client, validator, raw_response):
        provider, client = provider_client
        primary_response = SimpleNamespace(choices=[])
        backup_response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(raw_response)))], model="backup-model")
        client.chat.completions.create.side_effect = [primary_response, backup_response]

        result, error = provider.generate("Test prompt", validator.get_recommendation_schema(), GROCERY_LIST, validator)
        assert error is None
        assert result is not None
        assert [call.kwargs["model"] for call in client.chat.completions.create.call_args_list] == ["primary-model", "backup-model"]

    # Test 17 - Report failure when neither model returns a usable response.
    # Expected: Both models are attempted and the caller receives an error.
    def test_both_models_fail(self, provider_client, validator):
        provider, client = provider_client
        client.chat.completions.create.return_value = SimpleNamespace(choices=[])

        result, error = provider.generate("Test prompt", validator.get_recommendation_schema(), GROCERY_LIST, validator)
        assert result is None
        assert "Both AI models failed" in error
        assert [call.kwargs["model"] for call in client.chat.completions.create.call_args_list] == ["primary-model", "backup-model"]
# endregion

# region AI Manager
class TestAIManager:
    # Test 18 - Process a complete recommendation request using a mock provider.
    # Expected: Original grocery data is preserved and every item receives AI data.
    def test_ai_manager_mock_recommendations(self, ai_input, raw_response, validator):
        household, history, fridge, cart = ai_input
        original_cart = [item.to_dict() for item in cart.get_items()]
        manager = AIManager(MockAIProvider(json.dumps(raw_response)))

        result, error = manager.get_ai_recommendations(household_info=household, consumption_history=history, fridge_stock=fridge, purchase_stock=cart, remarks="none", days_until_next=7)

        assert error is None
        assert validator.check_ai_output(result["Recommendations_List"], GROCERY_LIST) is True
        assert [item.to_dict() for item in cart.get_items()] == original_cart
        assert result["Total_Planned_Estimated_Calories"] == 13940
        assert result["Total_Estimated_Calories"] == 13940

        for item, recommendation in zip(cart.get_items(), result["Recommendations_List"]):
            assert item.is_enhanced() is True
            assert item.ai_data.recommended_qty == recommendation["Recommended_Quantity"]
            assert item.ai_data.consumption_rate == recommendation["Estimated_Consumption_Rate"]
            assert item.ai_data.est_expiry_date == recommendation["Estimated_Expiry_Date"]

    # Test 19 - Stop generation when the provider connection fails.
    # Expected: Planned items stay unchanged and no AI data is attached.
    def test_connection_failure_stops_generation(self, ai_input):
        household, history, fridge, cart = ai_input
        original_cart = [item.to_dict() for item in cart.get_items()]
        provider = MagicMock(spec=AIProvider)
        provider.check_connection.return_value = (False, "Provider unavailable")

        result, error = AIManager(provider).get_ai_recommendations(household_info=household, consumption_history=history, fridge_stock=fridge, purchase_stock=cart, remarks="none", days_until_next=7)

        assert result is None
        assert error == "Provider unavailable"
        provider.generate.assert_not_called()
        assert [item.to_dict() for item in cart.get_items()] == original_cart
        assert all(item.is_enhanced() is False for item in cart.get_items())

    # Test 20 - Exclude expired fridge stock and notify the user.
    # Expected: Only usable stock reaches the prompt builder.
    def test_expired_stock_is_excluded(self, make_context):
        _, ctx = make_context()
        today = date.today()
        usable_stock = copy.deepcopy(ctx.fridge.to_dicts())
        ctx.fridge.add_item(FridgeItem("milk", 2, "l", (today - timedelta(days=3)).isoformat(), (today - timedelta(days=1)).isoformat(), "expired"))
        provider = MagicMock(spec=AIProvider)
        provider.check_connection.return_value = (True, "Ready")
        provider.generate.return_value = (None, "Simulated generation failure")
        notify = MagicMock()

        with patch("modules.ai.AI_manager.PromptBuilder") as builder_class:
            builder_class.return_value.build_ai_prompt.return_value = "Test prompt"
            result, error = AIManager(provider).get_ai_recommendations(household_info=ctx.household, consumption_history=ctx.history, fridge_stock=ctx.fridge, purchase_stock=ctx.cart, remarks="none", days_until_next=7, notify=notify)
            supplied_data = builder_class.return_value.build_ai_prompt.call_args.args[0]

        assert result is None
        assert error == "Simulated generation failure"
        assert supplied_data["fridge_stock"] == usable_stock
        notify.assert_called_once()
        assert "expired" in notify.call_args.args[0].lower()
# endregion

# region AI Pipeline Integration
class TestAIPipelineIntegration:
    # Test 21 - Verify AI consumption estimates influence the final business decision.
    # Expected: The same cart is sufficient at seven litres/week but insufficient at fourteen.
    @pytest.mark.parametrize("weekly_rate, expected_underbuy", [(7, False), (14, True)])
    def test_recommended_cart_runs_through_ai_and_logic(self, make_recommendation_context, weekly_rate, expected_underbuy):
        fridge, history = make_recommendation_context(stock=3)
        cart = CartRecommender(fridge, history).generate_recommendation()
        household = Household()
        household.add_member(Person(1, "TestUser", 20, "Male", "none"))

        response = {
            "Recommendations_List": [
                {"Item_Name": "milk", "Planned_Quantity": 4, "Unit": "l", "Recommended_Quantity": 4, "Estimated_Consumption_Rate": weekly_rate, "Planned_Estimated_Calories": 2400, "Estimated_Calories": 2400, "Estimated_Expiration_Days": 20}
            ],
            "Total_Planned_Estimated_Calories": 2400,
            "Total_Estimated_Calories": 2400,
        }

        manager = AIManager(MockAIProvider(json.dumps(response)))
        result, error = manager.get_ai_recommendations(household_info=household, consumption_history=history, fridge_stock=fridge, purchase_stock=cart, remarks="none", days_until_next=7)

        assert error is None
        assert cart.get_items()[0].is_enhanced() is True
        assert cart.get_items()[0].ai_data.consumption_rate == weekly_rate

        ctx = AnalysisContext(cart=cart, household=household, fridge=fridge, history=history, total_est_calories=result["Total_Planned_Estimated_Calories"], next_purchase_date=7)
        findings = CartEvaluator().evaluate(ctx)
        assert [finding.analyzer_name for finding in findings] == ["CaloriesSurplus", "RiskOfExpiry", "UnderBuy"]
        assert next(finding.result for finding in findings if finding.analyzer_name == "RiskOfExpiry") is False
        assert next(finding.result for finding in findings if finding.analyzer_name == "UnderBuy") is expected_underbuy
# endregion
# endregion

# =========================================================
# 2. BUSINESS LOGIC TESTS
# Input: Enhanced cart items, household data and history.
# Expected: Correct totals, calories, expiry, under-buy,
# confidence scoring and coordinated analysis.
# =========================================================
# region Business Logic Tests
# region Analysis Context
class TestAnalysisContext:
    # Test 22 - Combine usable fridge and cart quantities.
    # Expected: Both sources contribute to the total.
    def test_total_items_includes_fridge_and_cart(self, make_context):
        _, ctx = make_context(quantity=3, fridge_quantity=2)
        assert ctx.get_total_items("milk") == pytest.approx(5)

    # Test 23 - Append valid findings to the context.
    # Expected: Existing findings remain when new findings are added.
    def test_update_findings_appends_valid_findings(self, make_context):
        _, ctx = make_context()
        first = Finding("CaloriesSurplus", False, "No surplus")
        second = Finding("RiskOfExpiry", False, None, item_name="milk")
        ctx.update_findings([first])
        ctx.update_findings([second])
        assert ctx.findings == [first, second]

    # Test 24 - Reject invalid finding containers or entries.
    # Expected: Invalid values raise TypeError.
    @pytest.mark.parametrize("invalid", [None, {}, [True], ["text"]])
    def test_update_findings_rejects_invalid_values(self, make_context, invalid):
        _, ctx = make_context()
        with pytest.raises(TypeError) as captured:
            ctx.update_findings(invalid)
        print(f"Expected error: {captured.value}")

    # Test 25 - Handle normalized names, fridge-only items and absent items.
    # Expected: Names match consistently and missing quantities contribute zero.
    def test_total_items_handles_missing_cart_and_normalized_names(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=2)
        assert ctx.get_total_items(" MILK ") == pytest.approx(5)
        ctx.cart.remove_item(item)
        assert ctx.get_total_items("milk") == pytest.approx(2)
        assert ctx.get_total_items("unknown") == pytest.approx(0)

    # Test 26 - Exclude expired batches from available stock.
    # Expected: Only the planned cart quantity remains available.
    def test_total_items_excludes_expired_stock(self, make_context):
        _, ctx = make_context(quantity=3, fridge_quantity=0)
        today = date.today()
        ctx.fridge.add_item(FridgeItem("milk", 2, "l", (today - timedelta(days=2)).isoformat(), (today - timedelta(days=1)).isoformat(), "none"))
        assert ctx.get_total_items("milk") == pytest.approx(3)
# endregion

# region Calories Surplus
class TestCaloriesSurplusAnalyzer:
    # Test 27 - Verify age categories at their boundaries.
    # Expected: Ages map to the correct calorie-table entries.
    @pytest.mark.parametrize("age, expected", [(1, 1), (18, 18), (19, 19), (29, 19), (30, 30), (59, 30), (60, 60), (100, 60)])
    def test_age_brackets(self, age, expected):
        analyzer = CaloriesSurplusAnalyzer()
        assert analyzer._CaloriesSurplusAnalyzer__get_age_from_KCAL(age) == expected

    # Test 28 - Calculate the household's seven-day calorie requirement.
    # Expected: A male aged twenty and female aged thirty-five require 33145 kcal.
    def test_family_calories_for_seven_days(self, make_context):
        _, ctx = make_context()
        analyzer = CaloriesSurplusAnalyzer()
        assert analyzer._CaloriesSurplusAnalyzer__calculate_family_kcal(7, ctx.household) == 33145

    # Test 29 - Detect calorie surplus at the requirement boundary.
    # Expected: Only totals strictly above the requirement produce a surplus.
    @pytest.mark.parametrize("calories, expected", [(33146, True), (33145, False), (33144, False)])
    def test_surplus_boundary(self, make_context, calories, expected):
        _, ctx = make_context(total_calories=calories)
        finding = CaloriesSurplusAnalyzer().analyze(ctx)
        assert isinstance(finding, Finding)
        assert finding.analyzer_name == "CaloriesSurplus"
        assert finding.result is expected
        assert "kcal" in finding.message
# endregion

# region Risk Of Expiry
class TestRiskOfExpiryAnalyzer:
    # Test 30 - Evaluate normal and fractional consumption boundaries.
    # Expected: Exact consumption capacity is safe; quantities exceeding it are risky.
    @pytest.mark.parametrize("quantity, fridge_quantity, weekly_rate, expiry_days, expected", [
        (3, 1, 1, 3, True), (3, 1, 7, 20, False), (3, 0, 7, 3, False), (3.4, 0, 7, 3, True)])
    def test_expiry_risk_boundaries(self, make_context, quantity, fridge_quantity, weekly_rate, expiry_days, expected):
        item, ctx = make_context(quantity=quantity, fridge_quantity=fridge_quantity, weekly_rate=weekly_rate, expiry_days=expiry_days)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert isinstance(finding, Finding)
        assert finding.analyzer_name == "RiskOfExpiry"
        assert finding.result is expected
        assert finding.item_name == item.name
        if expected:
            assert item.name in finding.message
        else:
            assert finding.message is None

    # Test 31 - Preserve item identity when consumption is nonpositive.
    # Expected: A false finding with no warning message is returned for the correct item.
    @pytest.mark.parametrize("rate", [0, -1])
    def test_nonpositive_rate_returns_false_finding(self, make_context, rate):
        item, ctx = make_context(weekly_rate=rate)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert isinstance(finding, Finding)
        assert finding.analyzer_name == "RiskOfExpiry"
        assert finding.result is False
        assert finding.message is None
        assert finding.item_name == item.name

    # Test 32 - Handle extremely small positive consumption rates.
    # Expected: Expiry analysis returns a risk without date overflow.
    def test_tiny_rate_does_not_overflow(self, make_context):
        item, ctx = make_context(quantity=1, fridge_quantity=0, weekly_rate=1e-12, expiry_days=3)
        finding = RiskOfExpiryAnalyzer().analyze(item, ctx)
        assert finding.result is True
        assert finding.item_name == item.name
# endregion

# region Under Buy
class TestUnderBuyAnalyzer:
    # Test 33 - Apply both calorie and expiry conditions before recommending more stock.
    # Expected: Under-buy is evaluated only when neither blocking condition is true.
    @pytest.mark.parametrize("surplus, expiry_risk, should_buy", [(False, False, True), (True, False, False), (False, True, False), (True, True, False)])
    def test_analysis_gate(self, make_context, surplus, expiry_risk, should_buy):
        item, ctx = make_context(quantity=1, fridge_quantity=1, weekly_rate=7)
        ctx.update_findings([Finding("CaloriesSurplus", surplus, "test")])
        if expiry_risk:
            ctx.update_findings([Finding("RiskOfExpiry", True, "milk will expire", item_name=item.name)])

        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.analyzer_name == "UnderBuy"
        assert finding.result is should_buy

    # Test 34 - Avoid recommending more when stock is sufficient.
    # Expected: False result with no under-buy message.
    def test_no_top_up_when_stock_is_sufficient(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=10, weekly_rate=7)
        ctx.update_findings([Finding("CaloriesSurplus", False, "test")])
        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.result is False
        assert finding.message is None

    # Test 35 - Avoid recommending additional stock for zero consumption.
    # Expected: No under-buy warning is produced.
    def test_zero_consumption_never_requests_more(self, make_context):
        item, ctx = make_context(weekly_rate=0)
        ctx.update_findings([Finding("CaloriesSurplus", False, "test")])
        finding = UnderBuyAnalyzer().analyze(item, ctx)
        assert finding.result is False

    # Test 36 - Match expiry warnings by identity rather than message wording.
    # Expected: Only a warning belonging to the exact item blocks under-buy analysis.
    @pytest.mark.parametrize("warning_item, message, expected", [("brown rice", "brown rice will expire", True), ("rice", "Food will expire", False)])
    def test_underbuy_uses_exact_item_identity(self, make_context, warning_item, message, expected):
        _, ctx = make_context()
        rice = CartItem("rice", 1, "kg")
        rice.set_ai_data(recommended_qty=1, consumption_rate=7, est_expiry_date=(date.today() + timedelta(days=20)).isoformat())
        ctx.cart.add_item(rice)
        ctx.update_findings([Finding("CaloriesSurplus", False, "No surplus"), Finding("RiskOfExpiry", True, message, item_name=warning_item)])
        assert UnderBuyAnalyzer().analyze(rice, ctx).result is expected
# endregion

# region Confidence
class TestConfidenceCalculator:
    # Test 37 - Handle items without consumption history.
    # Expected: Confidence is zero when historical evidence is unavailable.
    def test_no_history_returns_zero(self, make_context):
        item, ctx = make_context(history_quantities=())
        assert ConfidenceCalculator().calculate_confidence_score(item, ctx) == 0.0

    # Test 38 - Reject confidence calculation before AI enhancement.
    # Expected: An item without AI data raises NotImplementedError.
    def test_item_without_ai_data_is_rejected(self, make_context):
        _, ctx = make_context()
        with pytest.raises(NotImplementedError) as captured:
            ConfidenceCalculator().calculate_confidence_score(CartItem("milk", 2, "l"), ctx)
        print(f"Expected error: {captured.value}")

    # Test 39 - Handle zero-consumption history without division by zero.
    # Expected: The current weighted formula returns 49.5.
    def test_zero_history_does_not_divide_by_zero(self, make_context):
        item, ctx = make_context(quantity=1, fridge_quantity=0, history_quantities=(0,))
        item.set_ai_data(recommended_qty=0, consumption_rate=0, est_expiry_date=item.ai_data.est_expiry_date)
        assert ConfidenceCalculator().calculate_confidence_score(item, ctx) == 49.5

    # Test 40 - Reward agreement between AI recommendations and historical demand.
    # Expected: Six litres receives a higher score than three when six litres are needed.
    def test_agreement_improves_confidence(self, make_context):
        item, ctx = make_context(quantity=3, fridge_quantity=1, history_quantities=(7, 7))
        calculator = ConfidenceCalculator()
        first_score = calculator.calculate_confidence_score(item, ctx)
        item.set_ai_data(recommended_qty=6, consumption_rate=7, est_expiry_date=item.ai_data.est_expiry_date)
        assert calculator.calculate_confidence_score(item, ctx) > first_score

    # Test 41 - Apply the actionable-remarks bonus through cart remarks.
    # Expected: Hosting guests increases the result by five, capped at one hundred.
    def test_actionable_remarks_bonus(self, make_context):
        item, ctx = make_context(remarks="none")
        calculator = ConfidenceCalculator()
        baseline = calculator.calculate_confidence_score(item, ctx)
        ctx.cart.set_remarks("hosting guests")
        assert calculator.calculate_confidence_score(item, ctx) == min(100, round(baseline + 5, 1))

    # Test 42 - Distinguish full, partial and absent remarks bonuses.
    # Expected: Each keyword category returns its configured bonus.
    @pytest.mark.parametrize("remarks, expected", [("none", 0), ("", 0), ("hosting guests", 5), ("eating out", 2.5), ("ordinary note", 0)])
    def test_bonus_keywords(self, remarks, expected):
        assert BonusCalculator().bonus(remarks) == expected

    # Test 43 - Handle zero-mean consumption consistency.
    # Expected: Consistency is zero instead of a division-by-zero error.
    def test_zero_mean_consistency(self):
        assert ConfidenceMetrics().consistency_score([0.0, 0.0]) == 0.0
# endregion

# region Logic Integration
class TestLogicManagerIntegration:
    # Test 44 - Produce cart-level and item-level findings for multiple items.
    # Expected: One calorie finding per cart and two findings per item.
    def test_cart_evaluator_produces_cart_and_item_findings(self, make_context):
        _, ctx = make_context()
        eggs = CartItem("eggs", 2, "pcs")
        eggs.set_ai_data(recommended_qty=2, consumption_rate=7, est_expiry_date=(date.today() + timedelta(days=20)).isoformat())
        ctx.cart.add_item(eggs)

        findings = CartEvaluator().evaluate(ctx)
        assert [finding.analyzer_name for finding in findings] == ["CaloriesSurplus", "RiskOfExpiry", "UnderBuy", "RiskOfExpiry", "UnderBuy"]
        assert ctx.findings == findings
        assert [finding.item_name for finding in findings if finding.analyzer_name == "RiskOfExpiry"] == ["milk", "eggs"]

    # Test 45 - Return true expiry messages and exclude false results.
    # Expected: Risky stock produces the known message; safe stock returns an empty list.
    @pytest.mark.parametrize("expiry_days, expected_count", [(1, 1), (20, 0)])
    def test_manager_gets_findings(self, make_context, expiry_days, expected_count):
        item, ctx = make_context(quantity=3, fridge_quantity=1, weekly_rate=7, expiry_days=expiry_days)
        manager = Logic_manager()
        manager.process_recommendations(ctx)
        messages = manager.get_recommedations("RiskOfExpiry", True)

        if expected_count:
            expected_message = f"3l of milk --> estimated expiry: {item.ai_data.est_expiry_date}. (AI estimated consumption: 7 l a week)"
            assert messages == [expected_message]
        else:
            assert messages == []

    # Test 46 - Attach calculated confidence scores to every enhanced cart item.
    # Expected: Stored scores match calculations, including zero without history.
    def test_manager_adds_confidence_to_cart(self, make_context):
        milk, ctx = make_context(quantity=6, fridge_quantity=1)
        eggs = CartItem("eggs", 2, "pcs")
        eggs.set_ai_data(recommended_qty=2, consumption_rate=7, est_expiry_date=(date.today() + timedelta(days=20)).isoformat())
        ctx.cart.add_item(eggs)
        calculator = ConfidenceCalculator()
        expected = {item.name: calculator.calculate_confidence_score(item, ctx) for item in ctx.cart.get_items()}

        Logic_manager().add_confidence_score(ctx)
        for item in ctx.cart.get_items():
            assert item.ai_data.confidence_score == pytest.approx(expected[item.name])
        assert milk.ai_data.confidence_score > 0
        assert eggs.ai_data.confidence_score == 0

    # Test 47 - Discard stale findings when the same context is evaluated again.
    # Expected: Updated quantities produce fresh expiry and under-buy decisions.
    def test_reevaluation_replaces_old_findings(self, make_context):
        item, ctx = make_context(quantity=10, fridge_quantity=0, weekly_rate=7, expiry_days=3)
        evaluator = CartEvaluator()
        first = evaluator.evaluate(ctx)
        assert next(f.result for f in first if f.analyzer_name == "RiskOfExpiry") is True

        item.set_quantity(1)
        second = evaluator.evaluate(ctx)
        assert len(second) == 3
        assert ctx.findings == second
        assert next(f.result for f in second if f.analyzer_name == "RiskOfExpiry") is False
        assert next(f.result for f in second if f.analyzer_name == "UnderBuy") is True
# endregion
# endregion

# =========================================================
# 3. CART RECOMMENDATION TESTS
# Input: Historical consumption and current fridge stock.
# Expected: Recommend shortages using the current historical
# shopping-period calculation without changing source data.
# =========================================================
# region Cart Recommendation Tests
class TestCartRecommender:
    # Test 48 - Handle missing history and recorded zero consumption.
    # Expected: Neither situation produces an initial recommendation.
    @pytest.mark.parametrize("quantities", [(), (0,)])
    def test_no_demand_returns_empty_cart(self, make_recommendation_context, quantities):
        fridge, history = make_recommendation_context(history_quantities=quantities)
        result = CartRecommender(fridge, history).generate_recommendation()
        assert isinstance(result, Cart)
        assert result.get_items() == []

    # Test 49 - Deduct usable stock and exclude expired stock.
    # Expected: Only the remaining shortage is recommended.
    @pytest.mark.parametrize("stock, expired_stock, expected", [(0, 0, 7), (3, 0, 4), (7, 0, 0), (10, 0, 0), (0, 3, 7), (2, 3, 5)])
    def test_recommends_only_shortage(self, make_recommendation_context, stock, expired_stock, expected):
        fridge, history = make_recommendation_context(stock=stock, expired_stock=expired_stock)
        items = CartRecommender(fridge, history).generate_recommendation().get_items()
        if expected == 0:
            assert items == []
        else:
            assert len(items) == 1
            assert items[0].name == "milk"
            assert items[0].unit == "l"
            assert items[0].quantity == pytest.approx(expected)

    # Test 50 - Apply the fourteen-day history recency boundary.
    # Expected: Fourteen-day-old history is eligible; fifteen-day-old history is not.
    @pytest.mark.parametrize("age_days, expected_count", [(0, 1), (14, 1), (15, 0)])
    def test_recent_history_boundary(self, make_recommendation_context, age_days, expected_count):
        today = date.today()
        fridge, history = make_recommendation_context(age_days=age_days, today=today)

        with patch("modules.logic.CartRecommender.date") as mock_date:
            mock_date.today.return_value = today
            mock_date.fromisoformat.side_effect = date.fromisoformat
            items = CartRecommender(fridge, history).generate_recommendation().get_items()

        assert len(items) == expected_count

    # Test 51 - Use the newest record to determine recommendation eligibility.
    # Expected: Recent history makes an item eligible even when older records also exist.
    def test_latest_record_controls_eligibility(self, make_recommendation_context):
        fridge, history = make_recommendation_context(age_days=15)
        history.add_record(ConsumptionRecord("milk", 7, "l", 7, "none", record_date=date.today().isoformat()))
        items = CartRecommender(fridge, history).generate_recommendation().get_items()
        assert len(items) == 1
        assert items[0].quantity == pytest.approx(7)

    # Test 52 - Round recommended quantities according to their units.
    # Expected: Pieces round upward and other quantities use four decimal places.
    @pytest.mark.parametrize("quantities, unit, expected", [((3, 4), "pcs", 4), ((1, 1, 2), "l", 1.3333)])
    def test_quantity_rounding(self, make_recommendation_context, quantities, unit, expected):
        fridge, history = make_recommendation_context(history_quantities=quantities, unit=unit)
        items = CartRecommender(fridge, history).generate_recommendation().get_items()
        assert len(items) == 1
        assert items[0].quantity == pytest.approx(expected)
        assert items[0].validate() is True

    # Test 53 - Recommend multiple items without mutating fridge or history.
    # Expected: Only shortages appear and the new cart still requires AI processing.
    def test_multiple_items_preserve_sources(self, make_recommendation_context):
        fridge, history = make_recommendation_context(stock=3)
        history.add_record(ConsumptionRecord("eggs", 4, "pcs", 7, "none"))
        history.add_record(ConsumptionRecord("rice", 0, "kg", 7, "none"))
        before_fridge = copy.deepcopy(fridge.to_dicts())
        before_history = copy.deepcopy(history.to_dicts())

        cart = CartRecommender(fridge, history).generate_recommendation()
        actual = {item.name: (item.quantity, item.unit) for item in cart.get_items()}
        assert actual == {"eggs": (4, "pcs"), "milk": (4, "l")}
        assert fridge.to_dicts() == before_fridge
        assert history.to_dicts() == before_history
        assert cart.get_ai_enhanced() is False
        assert all(item.is_enhanced() is False for item in cart.get_items())

    # Test 54 - Calculate demand from records with different historical periods.
    # Expected: The current average historical shopping period produces 10.5 litres.
    def test_different_history_periods(self):
        fridge = Fridge()
        history = ConsumptionHistory()
        history.add_record(ConsumptionRecord("milk", 7, "l", 7, "none"))
        history.add_record(ConsumptionRecord("milk", 14, "l", 14, "none"))
        items = CartRecommender(fridge, history).generate_recommendation().get_items()
        assert len(items) == 1
        assert items[0].quantity == pytest.approx(10.5)
# endregion

# =========================================================
# 4. FRIDGE CONSUMPTION TESTS
# Input: Decimal batches and mixed-item inventory.
# Expected: Correct stock reduction without rounding errors
# or loops that fail to advance.
# =========================================================
# region Fridge Consumption Tests
class TestFridgeConsumption:
    # Test 55 - Consume the exact quantity across separate decimal batches.
    # Expected: Both batches are removed and a valid consumption record is returned.
    def test_decimal_batches_are_consumed_exactly(self):
        fridge = Fridge()
        today = date.today()
        fridge.add_item(FridgeItem("milk", 0.1, "l", today.isoformat(), (today + timedelta(days=5)).isoformat(), "none"))
        fridge.add_item(FridgeItem("milk", 0.2, "l", today.isoformat(), (today + timedelta(days=6)).isoformat(), "none"))

        assert len(fridge.get_items()) == 2
        record = fridge.consume("milk", 0.3, "l", 7, "none")
        assert fridge.get_items() == []
        assert record.quantity == pytest.approx(0.3)
        assert record.validate() is True

    # Test 56 - Preserve the unconsumed portion of a batch.
    # Expected: Consuming 0.3 litres from one litre leaves 0.7 litres.
    def test_partial_consumption(self):
        fridge = Fridge()
        today = date.today()
        fridge.add_item(FridgeItem("milk", 1, "l", today.isoformat(), (today + timedelta(days=5)).isoformat(), "none"))

        record = fridge.consume("milk", 0.3, "l", 7, "none")
        assert fridge.get_item_total("milk", include_expired=True) == pytest.approx(0.7)
        assert record.quantity == pytest.approx(0.3)

    # Test 57 - Advance past unrelated items when locating stock to consume.
    # Expected: Consumption finishes and unrelated stock remains unchanged.
    def test_consumption_skips_unrelated_items(self):
        # A separate process prevents a returning infinite-loop bug from freezing pytest.
        script = """
from datetime import date, timedelta
from modules.core.Fridge import Fridge
from modules.core.FridgeItem import FridgeItem
fridge = Fridge()
today = date.today()
expiry = (today + timedelta(days=5)).isoformat()
fridge.add_item(FridgeItem("eggs", 2, "pcs", today.isoformat(), expiry, "none"))
fridge.add_item(FridgeItem("milk", 1, "l", today.isoformat(), expiry, "none"))
record = fridge.consume("milk", 1, "l", 7, "none")
assert record.quantity == 1
assert fridge.get_item_total("milk", include_expired=True) == 0
assert fridge.get_item_total("eggs", include_expired=True) == 2
"""
        try:
            result = subprocess.run([sys.executable, "-B", "-c", script], cwd=AppPaths.PROJECT_ROOT, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            pytest.fail("Fridge.consume() did not advance past an unrelated item.")
        assert result.returncode == 0, result.stderr
# endregion

# =========================================================
# 5. STORAGE PATH AND LOGGER TESTS
# Input: Shared application paths and temporary log files.
# Expected: Stable storage configuration and preserved logs.
# =========================================================
# region Storage Paths And Logging
class TestStoragePathsAndLogger:
    # Test 58 - Anchor application storage paths to the project directory.
    # Expected: Changing the working directory does not change the configured paths.
    def test_paths_are_project_relative(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_root = Path(__file__).resolve().parent
        assert AppPaths.PROJECT_ROOT == project_root
        assert AppPaths.DATABASE_DIR == project_root / "app_data" / "database"
        assert AppPaths.LOGS_DIR == project_root / "app_data" / "logs"
        assert AppPaths.OFFLINE_MARKER == AppPaths.DATABASE_DIR / ".offline_changes"

    # Test 59 - Append log messages without overwriting earlier messages.
    # Expected: Both messages remain in the selected temporary log file.
    def test_logger_preserves_messages(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger = Logger(logs_dir=log_dir)
        logger.send_log("First message")
        logger.send_log("Second message")
        assert log_dir.is_dir()
        assert Path(logger.filename).read_text(encoding="utf-8").splitlines() == ["First message", "Second message"]
# endregion

# =========================================================
# 6. APPLICATION ENTRY POINT TESTS
# Input: Simulated imports and unavailable dependencies.
# Expected: Safe imports and clear startup error messages.
# =========================================================
# region Application Entry Point Tests
class TestApplicationEntryPoint:
    # Test 60 - Import the entry point without starting the interactive workflow.
    # Expected: Import-style execution does not run the application or request input.
    def test_main_import_does_not_start_application(self):
        with patch("Application.Application") as application_class:
            with patch("builtins.input", side_effect=AssertionError("Unexpected input")) as user_input:
                runpy.run_path(str(AppPaths.PROJECT_ROOT / "main.py"), run_name="test_import")

        application_class.assert_not_called()
        user_input.assert_not_called()

    # Test 61 - Simulate a missing dependency during application startup.
    # Expected: Display a useful error and exit without starting the application.
    def test_startup_reports_missing_module(self):
        original_import = __import__

        # Simulate an AI dependency error propagating through the application import.
        def simulate_missing_module(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "Application":
                raise ModuleNotFoundError("No module named 'openai'", name="openai")
            return original_import(name, globals, locals, fromlist, level)

        # Execute the actual entry point without starting the application.
        with patch("builtins.__import__", side_effect=simulate_missing_module):
            with pytest.raises(SystemExit) as captured:
                runpy.run_path(str(AppPaths.PROJECT_ROOT / "main.py"), run_name="__main__")

        # Verify the handler identifies the missing package and explains the next step.
        message = str(captured.value)
        assert "required module 'openai' was not found" in message
        assert "python_dependencies.txt" in message
        print(f"\nSimulated missing AI dependency:\n{message}")

    # Test 62 - Simulate an unavailable AIManager class during application startup.
    # Expected: Report the AI import problem and exit without starting the workflow.
    def test_startup_reports_invalid_import(self):
        original_import = __import__

        # Simulate AI_manager loading without the AIManager name expected by Application.
        def simulate_invalid_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "Application":
                raise ImportError("cannot import name 'AIManager' from 'modules.ai.AI_manager'")
            return original_import(name, globals, locals, fromlist, level)

        # Execute the actual entry point with the simulated import failure.
        with patch("builtins.__import__", side_effect=simulate_invalid_import):
            with pytest.raises(SystemExit) as captured:
                runpy.run_path(str(AppPaths.PROJECT_ROOT / "main.py"), run_name="__main__")

        # Verify the message identifies the unavailable class and its module.
        message = str(captured.value)
        assert "Application import failed" in message
        assert "cannot import name 'AIManager'" in message
        assert "modules.ai.AI_manager" in message
        print(f"\nSimulated AI module import failure:\n{message}")
# endregion
# =========================================================
# 7. HOUSEHOLD PERSISTENCE, SYNC AND CONFLICT RECOVERY
# Temporary device storage and a versioned cloud double keep
# these tests independent of Atlas and real household data.
# =========================================================
@pytest.fixture
def household_environment(tmp_path):
    documents = {}
    repository = MagicMock(spec=RepositoryFunctions)

    def create(document):
        assert document['_id'] not in documents
        documents[document['_id']] = copy.deepcopy(document)
        return copy.deepcopy(document)

    def load(household_id):
        return copy.deepcopy(documents[household_id])

    def save(document, version):
        current = documents[document['_id']]
        if current['version'] != version:
            raise SaveConflict('Cloud data changed')
        saved = copy.deepcopy(document)
        saved['version'] = version + 1
        documents[saved['_id']] = saved
        return copy.deepcopy(saved)

    repository.create.side_effect = create
    repository.load.side_effect = load
    repository.save.side_effect = save
    ui = MagicMock(spec=IO_manager)
    data = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: repository)
    data.create_household('Test Space')
    data.remember(data.base)
    repository.reset_mock()
    ui.reset_mock()
    return data, repository, ui, documents

# Use actual domain objects so persistence tests exercise serialization as well as saves.
def add_test_food(data):
    today = date.today()
    data.stores['fridge'].add_item(FridgeItem('Milk', 2, 'l', today.isoformat(),
        (today + timedelta(days=7)).isoformat(), 'none'))
    data.stores['consumption_history'].add_record(ConsumptionRecord('Milk', 1, 'l', 7, 'none'))

class TestHouseholdPersistence:
    # Test 63 - Create a Household Space and save without edits.
    # Expected: The cloud matches local data; no extra write or pending draft is created.
    def test_create_and_unchanged_save(self, household_environment):
        data, repo, ui, documents = household_environment
        assert data.base == documents[data.base['_id']]
        assert data.save() == 'unchanged'
        repo.save.assert_not_called()
        repo.create.assert_not_called()
        assert data.read_cache()['pending'] is None

    # Test 64 - Save food data and reopen the Household Space.
    # Expected: The version increases and fridge and history records survive reopening.
    def test_save_and_reopen_round_trip(self, household_environment):
        data, repo, ui, documents = household_environment
        add_test_food(data)
        original_version = data.base['version']
        assert data.save() == 'saved'
        assert data.base['version'] == original_version + 1
        fresh = DB_manager(ui, database_dir=data.database_dir, mongo_factory=lambda: repo)
        fresh.open_household(data.base['_id'])
        assert fresh.stores['fridge'].to_dicts() == data.stores['fridge'].to_dicts()
        assert fresh.stores['consumption_history'].to_dicts() == data.stores['consumption_history'].to_dicts()
        assert fresh.read_cache()['pending'] is None

    # Test 65 - Restart with pending offline edits and reconnect.
    # Expected: The draft survives restart and syncs without losing fridge data.
    def test_offline_draft_survives_restart_and_sync(self, household_environment):
        data, repo, ui, documents = household_environment
        add_test_food(data)
        data.use_mongo = False
        assert data.save() == 'offline'
        pending = data.read_cache()['pending']
        fresh = DB_manager(ui, database_dir=data.database_dir, mongo_factory=lambda: repo)
        fresh.open_household(data.base['_id'])
        assert fresh.read_cache()['pending'] == pending
        assert fresh.save() == 'saved'
        assert documents[data.base['_id']]['fridge'] == pending['fridge']
        assert fresh.read_cache()['pending'] is None

    # Test 66 - Create offline and register when cloud access returns.
    # Expected: Registration succeeds and pending and unregistered states are cleared.
    def test_offline_creation_registers_on_sync(self, tmp_path):
        repo = MagicMock(spec=RepositoryFunctions)
        repo.create.side_effect = copy.deepcopy
        data = DB_manager(MagicMock(), database_dir=tmp_path, use_mongo=False, mongo_factory=lambda: repo)
        data.create_household('Offline Space')
        assert data.read_cache()['state']['unregistered'] is True
        repo.create.assert_not_called()
        data.use_mongo = True
        assert data.save() == 'saved'
        repo.create.assert_called_once()
        assert data.read_cache()['pending'] is None
        assert data.read_cache()['state']['unregistered'] is False

    # Test 67 - Sync an offline Household Space whose ID already exists in the cloud.
    # Expected: A new ID preserves local data and remembered access without overwriting the existing cloud record.
    def test_offline_id_collision_preserves_local_and_cloud_data(self, tmp_path):
        from pymongo.errors import DuplicateKeyError

        old_id = 'HS-AAAA-BBBB-CCCC'
        new_id = 'HS-DDDD-EEEE-FFFF'
        existing = Doc.new('Existing Cloud Space')
        existing['_id'] = old_id
        existing['created_at'] = '2025-01-01T00:00:00.000Z'
        cloud_documents = {old_id: Doc.to_cloud(existing)}
        original_cloud = copy.deepcopy(cloud_documents[old_id])
        insert_ids = []
        collection = MagicMock()

        # Enforce MongoDB uniqueness and version checks in an isolated collection double.
        def insert(document):
            insert_ids.append(document['_id'])
            if document['_id'] in cloud_documents:
                raise DuplicateKeyError('Duplicate household ID')
            cloud_documents[document['_id']] = copy.deepcopy(document)

        def update(query, changes, **kwargs):
            current = cloud_documents[query['_id']]
            assert current['version'] == query['version']
            assert kwargs['upsert'] is False
            current.update(copy.deepcopy(changes['$set']))
            current['version'] += changes['$inc']['version']
            return copy.deepcopy(current)

        collection.insert_one.side_effect = insert
        collection.find_one.side_effect = lambda query: copy.deepcopy(cloud_documents.get(query['_id']))
        collection.find_one_and_update.side_effect = update
        repository = MongoDBRepository(collection=collection)
        ui = MagicMock(spec=IO_manager)
        data = DB_manager(ui, database_dir=tmp_path, use_mongo=False, mongo_factory=lambda: repository)
        with patch.object(Doc, 'generate_id', return_value=old_id):
            data.create_household('Offline Space')
        data.stores['household'].add_member(Person(1, 'Zi', 22, 'Male', 'none'))
        add_test_food(data)
        data.remember(data.base)
        assert data.save() == 'offline'
        draft = copy.deepcopy(data.read_cache()['pending'])
        collection.insert_one.assert_not_called()

        # Restart with the saved offline draft, then reconnect and collide on registration.
        fresh = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: repository)
        fresh.open_household(old_id)
        with patch.object(Doc, 'generate_id', return_value=new_id) as generate_id:
            assert fresh.save() == 'saved'
        generate_id.assert_called_once()
        assert insert_ids == [old_id, new_id]
        assert cloud_documents[old_id] == original_cloud
        assert set(cloud_documents) == {old_id, new_id}
        assert Doc.editable(Doc.from_cloud(cloud_documents[new_id])) == Doc.editable(draft)
        assert Doc.editable(fresh.base) == Doc.editable(draft)
        assert fresh.base['_id'] == new_id
        assert fresh.stores['household'].household_id == new_id
        assert fresh.read_preferences()['last_household_id'] == new_id
        cache = fresh.read_cache()
        assert cache['snapshot'] == fresh.base
        assert cache['pending'] is None
        assert cache['state']['unregistered'] is False
        assert collection.find_one_and_update.call_args.args[0]['_id'] == new_id
        ui.send_message.assert_any_call(f'Household ID collision: your new ID is {new_id}.')

    # Test 68 - Switch to a different Household Space.
    # Expected: Only the selected ID is loaded and the previous cloud record is unchanged.
    def test_switch_loads_only_selected_household(self, household_environment):
        data, repo, ui, documents = household_environment
        old = copy.deepcopy(data.base)
        other = Doc.new('Other Space')
        documents[other['_id']] = other
        data.open_household(other['_id'])
        repo.load.assert_called_once_with(other['_id'])
        assert data.read_cache()['snapshot']['_id'] == other['_id']
        assert documents[old['_id']] == old

    # Test 69 - Select another space while the current space has pending edits.
    # Expected: Switching is blocked and subsequent saving updates only the draft owner.
    def test_pending_draft_cannot_be_saved_to_another_household(self, household_environment):
        data, repo, ui, documents = household_environment
        owner = data.base['_id']
        add_test_food(data)
        data.use_mongo = False
        data.save()
        pending = data.read_cache()['pending']
        other = Doc.new('Other Space')
        documents[other['_id']] = copy.deepcopy(other)
        data.remember(other)
        with pytest.raises(SaveConflict):
            data.open_household(other['_id'])
        data.use_mongo = True
        assert data.save() == 'saved'
        assert documents[owner]['fridge'] == pending['fridge']
        assert documents[other['_id']] == other

    # Test 70 - Save from a stale session after another session updates the cache.
    # Expected: LocalConflict prevents the stale session from overwriting cloud data.
    def test_stale_device_session_cannot_overwrite_cache(self, household_environment):
        data, repo, ui, documents = household_environment
        fresh = DB_manager(ui, database_dir=data.database_dir, mongo_factory=lambda: repo)
        fresh.open_household(data.base['_id'])
        add_test_food(data)
        data.save()
        add_test_food(fresh)
        before = copy.deepcopy(documents)
        with pytest.raises(LocalConflict):
            fresh.save()
        assert documents == before

    # Test 71 - Attempt a MongoDB save with an unmatched version.
    # Expected: The update filters by ID and version, disables upsert and raises SaveConflict.
    def test_mongodb_update_is_atomic_and_scoped(self):
        document = Doc.new('Atomic Save')
        collection = MagicMock()
        collection.find_one_and_update.return_value = None
        repository = MongoDBRepository(collection=collection)
        with pytest.raises(SaveConflict):
            repository.save(document, document['version'])
        args, kwargs = collection.find_one_and_update.call_args
        assert args[0] == {'_id': document['_id'], 'version': document['version']}
        assert args[1]['$inc'] == {'version': 1}
        assert kwargs['upsert'] is False

class TestHouseholdConflictRecovery:
    # Create a real stale draft with different food contents on each side.
    @staticmethod
    def prepare(environment):
        data, repo, ui, documents = environment
        add_test_food(data)
        cloud = documents[data.base['_id']]
        cloud['version'] += 1
        cloud['name'] = 'Cloud Display Name'
        with pytest.raises(SaveConflict):
            data.save()
        return copy.deepcopy(cloud), copy.deepcopy(data.read_cache()['pending'])

    # Test 72 - Resolve a conflict using local or cloud data.
    # Expected: The selected contents are applied safely; the table appears only on explicit review.
    @pytest.mark.parametrize('source', ['local', 'cloud'])
    def test_replacement_contents_and_no_automatic_table(self, household_environment, source):
        data, repo, ui, documents = household_environment
        cloud, draft = self.prepare(household_environment)
        repo.reset_mock()
        ui.reset_mock()
        ui.confirm_food_replacement.return_value = True
        assert data.session().resolve_food_conflict(source)
        ui.show_conflict_review.assert_not_called()
        ui.show_exit.assert_not_called()
        assert data.read_cache()['pending'] is None
        if source == 'local':
            assert data.base['fridge'] == draft['fridge']
            assert data.base['consumption_history'] == draft['consumption_history']
            assert data.base['name'] == cloud['name']
            assert data.base['version'] == cloud['version'] + 1
            assert documents[cloud['_id']] == data.base
        else:
            assert data.base == cloud
            assert documents[cloud['_id']] == cloud
            repo.save.assert_not_called()
        data.session().review()
        ui.show_conflict_review.assert_called_once()

    # Test 73 - Cancel confirmation of cloud replacement.
    # Expected: The pending draft and cloud contents remain unchanged.
    def test_cancel_preserves_draft(self, household_environment):
        data, repo, ui, documents = household_environment
        cloud, draft = self.prepare(household_environment)
        ui.confirm_food_replacement.return_value = False
        assert data.session().resolve_food_conflict('cloud') is False
        assert data.read_cache()['pending'] == draft
        assert documents[cloud['_id']] == cloud

    # Test 74 - Change the cloud version during replacement confirmation.
    # Expected: Both replacement choices reject the stale proposal and preserve food data.
    @pytest.mark.parametrize('source', ['local', 'cloud'])
    def test_concurrent_cloud_write_during_confirmation_is_rejected(self, household_environment, source):
        data, repo, ui, documents = household_environment
        cloud, draft = self.prepare(household_environment)
        def confirm(*args):
            documents[cloud['_id']]['version'] += 1
            return True
        ui.confirm_food_replacement.side_effect = confirm
        ui.reset_mock()
        with pytest.raises(SaveConflict):
            data.session().resolve_food_conflict(source)
        assert documents[cloud['_id']]['fridge'] == cloud['fridge']
        assert data.read_cache()['pending']['fridge'] == draft['fridge']
        ui.send_message.assert_not_called()

    # Test 75 - Choose cloud data through save recovery.
    # Expected: The session returns CLOUD_ADOPTED rather than treating the local draft as saved.
    def test_cloud_selection_returns_distinct_outcome(self, household_environment):
        data, repo, ui, documents = household_environment
        self.prepare(household_environment)
        ui.ask_save_recovery.return_value = 'cloud'
        ui.confirm_food_replacement.return_value = True
        assert data.session().save_outcome() == SaveOutcome.CLOUD_ADOPTED

    # Test 76 - Display the conflict comparison.
    # Expected: Only the fridge table appears, with no consumption history or separator rules.
    def test_review_shows_only_fridge(self, household_environment, capsys):
        data, repo, ui, documents = household_environment
        cloud, draft = self.prepare(household_environment)
        IO_manager().show_conflict_review(data.base, draft, cloud)
        output = capsys.readouterr().out
        assert output.startswith('\nFridge Data Differences\n')
        assert 'Milk' in output and 'Your amount' in output and 'Cloud expiry' in output
        assert 'Consumption History' not in output and '----+' not in output

# =========================================================
# 8. HOUSEHOLD SPACE NAVIGATION AND RECOVERY PROMPTS
# =========================================================
class TestHouseholdSpaceNavigation:
    # Test 77 - Select each Household Space access option.
    # Expected: Numbered choices map to enter, create and exit actions.
    @pytest.mark.parametrize('answer,action', [('1', 'enter'), ('2', 'create'), ('3', 'exit')])
    def test_access_menu(self, answer, action, capsys):
        with patch('builtins.input', return_value=answer):
            assert IO_manager().ask_household_access() == action
        output = capsys.readouterr().out
        assert '1. Enter Household Space ID' in output
        assert '2. Create Household Space' in output
        assert '3. Exit the program' in output

    # Test 78 - Choose Back while switching Household Spaces.
    # Expected: The selection menu reappears without loading or activating a space.
    def test_back_returns_to_selection_without_login(self, household_environment, capsys):
        data, repo, ui, documents = household_environment
        fresh = DB_manager(IO_manager(), database_dir=data.database_dir, mongo_factory=lambda: repo)
        with patch('builtins.input', side_effect=['2', '3', '4']):
            assert fresh.session().start() is None
        repo.load.assert_not_called()
        assert fresh.base is None
        assert capsys.readouterr().out.count('Continue with Test Space') == 2

    # Test 79 - Enter a valid Household Space ID.
    # Expected: The ID is remembered automatically without a remember prompt.
    def test_enter_remembers_without_prompt(self, household_environment, capsys):
        data, repo, ui, documents = household_environment
        data.remember()
        fresh = DB_manager(IO_manager(), database_dir=data.database_dir, mongo_factory=lambda: repo)
        with patch('builtins.input', side_effect=['1', data.base['_id']]):
            fresh.session().start()
        assert fresh.read_preferences()['last_household_id'] == data.base['_id']
        assert 'Remember this' not in capsys.readouterr().out

    # Test 80 - Forget a space with pending food edits while online.
    # Expected: Edits sync and remembered access clears while cache and cloud data remain.
    def test_forget_syncs_then_keeps_cache_and_cloud(self, household_environment):
        data, repo, ui, documents = household_environment
        add_test_food(data)
        household_id = data.base['_id']
        assert data.session().forget_household() is True
        assert not data.read_preferences()
        assert data.base is None
        assert data.read_cache()['snapshot']['_id'] == household_id
        assert data.read_cache()['pending'] is None
        assert documents[household_id]['fridge']

    # Test 81 - Attempt to forget a space with offline edits.
    # Expected: Forgetting is refused and remembered access and pending data remain.
    def test_forget_does_not_drop_offline_edits(self, household_environment):
        data, repo, ui, documents = household_environment
        add_test_food(data)
        data.use_mongo = False
        assert data.session().forget_household() is False
        assert data.read_preferences()
        assert data.read_cache()['pending'] is not None

    # Test 82 - Continue a saved space and exit without food edits.
    # Expected: The welcome appears, the farewell appears once and no cloud update occurs.
    def test_application_save_exit_farewell(self, household_environment, capsys):
        data, repo, ui, documents = household_environment
        data.stores['household'].add_member(Person(1, 'Zi', 22, 'Male', 'none'))
        data.save()
        actual_ui = IO_manager()
        fresh = DB_manager(actual_ui, database_dir=data.database_dir, mongo_factory=lambda: repo)
        repo.reset_mock()
        with patch('builtins.input', side_effect=['1', '3']):
            Application(actual_ui, fresh, MagicMock(), MagicMock()).run()
        output = capsys.readouterr().out
        assert f'\nWelcome back to the Test Space household!\nHousehold Space ID: {data.base["_id"]}' in output
        assert 'Welcome back to the Zi household!' not in output
        assert output.count('Thank you for using QuantiFresh!') == 1
        repo.save.assert_not_called()

    # Test 83 - Enter removed recovery options before a valid choice.
    # Expected: Invalid choices are rejected and only supported recovery actions are displayed.
    def test_recovery_menu_rejects_removed_choices(self, capsys):
        with patch('builtins.input', side_effect=['4', '5', 'retry', 'keep', '1']):
            assert IO_manager().ask_save_recovery() == 'review'
        output = capsys.readouterr().out
        assert 'How would you like to resolve the data conflict?' in output
        assert 'Retry save' not in output and 'Keep editing' not in output

    # Test 84 - Request confirmation for local and cloud replacements.
    # Expected: Each choice displays its exact replacement and data-loss prompt.
    @pytest.mark.parametrize('source,prompt', [
        ('local', 'Replace cloud data with your local data?\nCloud data will be replaced. (yes/no): '),
        ('cloud', 'Replace your local data with the latest cloud data?\nLocal data will be replaced. (yes/no): '),
    ])
    def test_confirmation_wording(self, source, prompt):
        with patch('builtins.input', return_value='yes') as input_mock:
            assert IO_manager().confirm_food_replacement(source, 11)
        input_mock.assert_called_once_with(prompt)

# Exercise real repository construction failures without accessing Atlas or changing network settings.
@pytest.fixture
def unavailable_mongo_dns(monkeypatch):
    from dns.exception import Timeout
    from pymongo.errors import ConfigurationError

    monkeypatch.setenv('MONGODB_URI', 'mongodb+srv://offline.example.test/')
    monkeypatch.setenv('MONGODB_DATABASE', 'OfflineTest')

    def fail_lookup(*args, **kwargs):
        try:
            raise Timeout('DNS lookup timed out')
        except Timeout as error:
            raise ConfigurationError('DNS lookup timed out') from error

    with patch('modules.repositories.MongoDBRepository.MongoClient', side_effect=fail_lookup) as client:
        yield client


class TestOfflineConnectionStartup:
    # Test 85 - Continue a remembered space when MongoDB DNS lookup fails.
    # Expected: Cached data opens locally without mutation or an unhandled exception.
    def test_continue_cached_space_after_dns_failure(self, household_environment, unavailable_mongo_dns, capsys):
        data, repo, ui, documents = household_environment
        before = data.read_cache()
        fresh = DB_manager(IO_manager(), database_dir=data.database_dir)
        with patch('builtins.input', return_value='1'):
            assert fresh.session().start() is not None
        assert fresh.is_local
        assert fresh.base['_id'] == data.base['_id']
        assert fresh.read_cache() == before
        assert 'Opening only this household' in capsys.readouterr().out
        unavailable_mongo_dns.assert_called_once()

    # Test 86 - Create a Household Space during a MongoDB DNS failure.
    # Expected: The space is remembered locally with pending registration and an offline message.
    def test_create_space_keeps_pending_registration(self, tmp_path, unavailable_mongo_dns, capsys):
        data = DB_manager(IO_manager(), database_dir=tmp_path)
        with patch('builtins.input', side_effect=['2', 'Offline Space']):
            assert data.session().start() is not None
        bundle = data.read_cache()
        assert bundle['state']['unregistered']
        assert bundle['pending']['name'] == 'Offline Space'
        assert data.read_preferences()['last_household_id'] == bundle['snapshot']['_id']
        assert data.is_local
        assert 'saved on this device' in capsys.readouterr().out
        unavailable_mongo_dns.assert_called_once()

    # Test 87 - Enter an uncached ID while MongoDB DNS is unavailable.
    # Expected: The menu reappears with an offline explanation and no space is activated or remembered.
    def test_enter_uncached_id_returns_to_menu(self, tmp_path, unavailable_mongo_dns, capsys):
        data = DB_manager(IO_manager(), database_dir=tmp_path)
        with patch('builtins.input', side_effect=['1', 'HS-ABCD-EFGH-JKLM', '3']):
            assert data.session().start() is None
        assert data.base is None
        assert data.read_cache()['snapshot'] is None
        assert not data.read_preferences()
        output = capsys.readouterr().out
        assert 'Cannot switch offline' in output
        assert output.count('1. Enter Household Space ID') == 2
        unavailable_mongo_dns.assert_called_once()

    # Test 88 - Enter the cached ID after forgetting remembered access while offline.
    # Expected: The existing local space opens with its data preserved.
    def test_enter_cached_id_opens_local_data(self, household_environment, unavailable_mongo_dns):
        data, repo, ui, documents = household_environment
        data.remember()
        fresh = DB_manager(IO_manager(), database_dir=data.database_dir)
        with patch('builtins.input', side_effect=['1', data.base['_id']]):
            assert fresh.session().start() is not None
        assert fresh.is_local
        assert fresh.base == data.base
        unavailable_mongo_dns.assert_called_once()

    # Test 89 - Construct the repository with invalid connection settings.
    # Expected: CloudOperationError reports invalid configuration instead of ordinary offline status.
    def test_invalid_configuration_is_not_reported_as_offline(self, monkeypatch):
        from pymongo.errors import ConfigurationError
        from modules.repositories.StorageErrors import CloudOperationError

        monkeypatch.setenv('MONGODB_URI', 'invalid-uri')
        monkeypatch.setenv('MONGODB_DATABASE', 'OfflineTest')
        with patch('modules.repositories.MongoDBRepository.MongoClient', side_effect=ConfigurationError('Invalid URI')):
            with pytest.raises(CloudOperationError, match='configuration is invalid'):
                MongoDBRepository()

    # Test 90 - Fail the connection during client construction or ping.
    # Expected: CloudUnavailable is raised and an existing client is closed safely.
    @pytest.mark.parametrize('during_construction', [True, False])
    def test_connection_failure_at_construction_or_ping(self, monkeypatch, during_construction):
        from pymongo.errors import ConnectionFailure
        from modules.repositories.StorageErrors import CloudUnavailable

        monkeypatch.setenv('MONGODB_URI', 'mongodb://offline.example.test/')
        monkeypatch.setenv('MONGODB_DATABASE', 'OfflineTest')
        with patch('modules.repositories.MongoDBRepository.MongoClient') as factory:
            client = factory.return_value
            if during_construction:
                factory.side_effect = ConnectionFailure('Offline')
            else:
                client.admin.command.side_effect = ConnectionFailure('Offline')
            with pytest.raises(CloudUnavailable):
                MongoDBRepository()
            if not during_construction:
                client.close.assert_called_once()
