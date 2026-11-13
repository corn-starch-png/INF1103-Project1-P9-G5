#region Imports
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
from modules.repositories.JsonRepository import JsonRepository
from modules.repositories.MongoDBRepository import MongoDBRepository
#endregion

#region Test Data
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
#endregion

# =========================================================
# SHARED FIXTURES
# Input: Temporary paths, mocked services and domain objects.
# Expected: Repeatable tests without changing real user data.
# =========================================================
#region Shared Fixtures
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
# Populate a temporary JSON repository using real domain objects.
@pytest.fixture
def populated_json_repository(tmp_path, make_context):
    _, ctx = make_context()
    folder = tmp_path / "database"
    repository = JsonRepository(folder=folder)
    errors, stores = repository.load()
    assert errors == []
    stores.update({"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history})
    expected = {name: store.to_dicts() for name, store in stores.items()}
    return repository, folder, expected
# Construct MongoDBRepository only after replacing its client with a mock.
@pytest.fixture
def mongo_repository(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://test.invalid")
    monkeypatch.setenv("MONGODB_DATABASE", "test_database")
    with patch("modules.repositories.MongoDBRepository.MongoClient") as client_class:
        client = client_class.return_value
        database = client.__getitem__.return_value
        collections = {name: MagicMock() for name in ("fridge", "household", "consumption_history")}
        database.__getitem__.side_effect = collections.__getitem__
        for collection in collections.values():
            collection.find.return_value = []
        repository = MongoDBRepository()
        yield repository, client, collections
# Create a fake cloud repository with real domain objects and a shared store dictionary.
@pytest.fixture
def recovery_cloud(make_context):
    _, ctx = make_context(quantity=3, fridge_quantity=1)
    stores = {"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history}
    repository = MagicMock()
    repository.load.return_value = ([], stores)
    return repository, stores
# Create a complete pending local dataset that differs from the cloud dataset.
@pytest.fixture
def pending_local_changes(tmp_path, make_context):
    _, ctx = make_context(quantity=3, fridge_quantity=2)
    repository = JsonRepository(folder=tmp_path)
    errors, stores = repository.load()
    assert errors == []
    stores.update({"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history})
    repository.save()

    marker = tmp_path / ".offline_changes"
    marker.touch()
    expected = {name: store.to_dicts() for name, store in stores.items()}
    return marker, expected
#endregion

# =========================================================
# 1. AI TESTS
# Input: Raw responses, mocked providers and domain objects.
# Expected: Validate responses, handle failures and attach
# AI data before business-rule evaluation.
# =========================================================
#region AI Tests

#region AI Response Validation
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
#endregion

#region AI Provider
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
#endregion

#region AI Manager
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
#endregion

#region AI Pipeline Integration
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
#endregion
#endregion

# =========================================================
# 2. BUSINESS LOGIC TESTS
# Input: Enhanced cart items, household data and history.
# Expected: Correct totals, calories, expiry, under-buy,
# confidence scoring and coordinated analysis.
# =========================================================
#region Business Logic Tests
#region Analysis Context
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
#endregion

#region Calories Surplus
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
#endregion

#region Risk Of Expiry
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
#endregion

#region Under Buy
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
#endregion

#region Confidence
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
#endregion

#region Logic Integration
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
            expected_message = f"3l of milk --> estimated expiry: {item.ai_data.est_expiry_date}. (avg consumption: 7 l a week)"
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
#endregion
#endregion

# =========================================================
# 3. CART RECOMMENDATION TESTS
# Input: Historical consumption and current fridge stock.
# Expected: Recommend shortages using the current historical
# shopping-period calculation without changing source data.
# =========================================================
#region Cart Recommendation Tests
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
#endregion

# =========================================================
# 4. FRIDGE CONSUMPTION TESTS
# Input: Decimal batches and mixed-item inventory.
# Expected: Correct stock reduction without rounding errors
# or loops that fail to advance.
# =========================================================
#region Fridge Consumption Tests
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
#endregion

# =========================================================
# 5. PERSISTENCE TESTS
# Input: Temporary JSON storage and a mocked MongoDB client.
# Expected: Data survives saves and loads, failures are
# reported and real user storage remains untouched.
# =========================================================
#region Persistence Tests
#region JSON Repository
class TestJsonRepository:
    # Test 58 - Initialize storage when the directory and files are missing.
    # Expected: Empty stores load without errors and the directory is created.
    def test_missing_directory_and_files(self, tmp_path):
        folder = tmp_path / "nested" / "database"
        errors, stores = JsonRepository(folder=folder).load()
        assert errors == []
        assert folder.is_dir()
        assert set(stores) == {"fridge", "household", "consumption_history"}
        assert all(store.to_dicts() == [] for store in stores.values())

    # Test 59 - Reload saved data using a fresh repository instance.
    # Expected: Household, fridge and history records survive a round trip.
    def test_save_load_round_trip(self, populated_json_repository):
        repository, folder, expected = populated_json_repository
        repository.save()
        errors, loaded = JsonRepository(folder=folder).load()
        assert errors == []
        assert {name: store.to_dicts() for name, store in loaded.items()} == expected

    # Test 60 - Report malformed JSON and incorrect top-level structures.
    # Expected: A damaged file does not prevent the other stores from loading.
    @pytest.mark.parametrize("content", ["{invalid json}", "{}"])
    def test_bad_file_does_not_block_other_stores(self, populated_json_repository, content):
        repository, folder, expected = populated_json_repository
        repository.save()
        (folder / "fridge.json").write_text(content, encoding="utf-8")

        errors, stores = JsonRepository(folder=folder).load()
        assert any("fridge" in error for error in errors)
        assert stores["fridge"].to_dicts() == []
        assert stores["household"].to_dicts() == expected["household"]
        assert stores["consumption_history"].to_dicts() == expected["consumption_history"]

    # Test 61 - Skip invalid rows without discarding valid records.
    # Expected: The valid fridge record loads and the invalid row produces an error.
    def test_invalid_row_preserves_valid_rows(self, populated_json_repository):
        repository, folder, expected = populated_json_repository
        repository.save()
        (folder / "fridge.json").write_text(json.dumps(expected["fridge"] + [{}]), encoding="utf-8")

        errors, stores = JsonRepository(folder=folder).load()
        assert len(errors) == 1
        assert stores["fridge"].to_dicts() == expected["fridge"]

    # Test 62 - Save valid JSON for empty stores.
    # Expected: Each storage file contains an empty list.
    def test_save_empty_stores(self, tmp_path):
        JsonRepository(folder=tmp_path).save()
        for name in ("fridge", "household", "consumption_history"):
            assert json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8")) == []

    # Test 63 - Preserve the destination file when replacement fails.
    # Expected: A pending update cannot overwrite the original file after an error.
    def test_failed_replace_preserves_existing_file(self, populated_json_repository):
        repository, folder, _ = populated_json_repository
        repository.save()

        # Make the old destination differ from the populated data about to be saved.
        destination = folder / "fridge.json"
        destination.write_text("[]", encoding="utf-8")
        original = destination.read_bytes()

        with patch("modules.repositories.JsonRepository.os.replace", side_effect=OSError("replacement failed")) as replace:
            with pytest.raises(OSError, match="replacement failed") as captured:
                repository.save()
            print(f"Expected error: {captured.value}")
            replace.assert_called_once()

        assert destination.read_bytes() == original

    # Test 64 - Respect an explicitly supplied storage directory.
    # Expected: Changing the working directory does not redirect the selected storage.
    def test_custom_directory_after_working_directory_change(self, tmp_path, monkeypatch):
        folder = tmp_path / "chosen_database"
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        JsonRepository(folder=folder).save()
        assert (folder / "fridge.json").is_file()
        assert not (elsewhere / "database").exists()
        assert not (elsewhere / "app_data").exists()
#endregion

#region MongoDB Repository
class TestMongoDBRepository:
    # Test 65 - Reject missing MongoDB configuration before connecting.
    # Expected: The missing setting is identified and no client is constructed.
    @pytest.mark.parametrize("missing_variable", ["MONGODB_URI", "MONGODB_DATABASE"])
    def test_missing_configuration(self, monkeypatch, missing_variable):
        monkeypatch.setenv("MONGODB_URI", "mongodb://test.invalid")
        monkeypatch.setenv("MONGODB_DATABASE", "test_database")
        monkeypatch.delenv(missing_variable, raising=False)

        with patch("modules.repositories.MongoDBRepository.MongoClient") as client_class:
            with pytest.raises(ValueError, match=missing_variable) as captured:
                MongoDBRepository()
            print(f"Expected error: {captured.value}")
            client_class.assert_not_called()

    # Test 66 - Surface connection failures for application-level fallback.
    # Expected: A failed ping raises an error rather than reporting success.
    def test_ping_failure_is_reported(self, monkeypatch):
        monkeypatch.setenv("MONGODB_URI", "mongodb://test.invalid")
        monkeypatch.setenv("MONGODB_DATABASE", "test_database")

        with patch("modules.repositories.MongoDBRepository.MongoClient") as client_class:
            client_class.return_value.admin.command.side_effect = OSError("database unavailable")
            with pytest.raises(OSError, match="database unavailable") as captured:
                MongoDBRepository()
            print(f"Expected error: {captured.value}")

    # Test 67 - Convert loaded records into domain objects and report invalid rows.
    # Expected: Valid data is retained and each collection is queried correctly.
    def test_load_valid_and_invalid_records(self, mongo_repository, make_context):
        repository, client, collections = mongo_repository
        _, ctx = make_context()
        collections["fridge"].find.return_value = ctx.fridge.to_dicts() + [{}]
        collections["household"].find.return_value = ctx.household.to_dicts()
        collections["consumption_history"].find.return_value = ctx.history.to_dicts()

        errors, stores = repository.load()
        assert len(errors) == 1
        assert stores["fridge"].to_dicts() == ctx.fridge.to_dicts()
        assert stores["household"].to_dicts() == ctx.household.to_dicts()
        assert stores["consumption_history"].to_dicts() == ctx.history.to_dicts()
        client.admin.command.assert_called_once_with("ping")
        for collection in collections.values():
            collection.find.assert_called_once_with({}, {"_id": 0})

    # Test 68 - Save populated domain stores into their matching collections.
    # Expected: Each collection receives the correct serialized records.
    def test_save_populated_stores(self, mongo_repository, make_context):
        repository, _, collections = mongo_repository
        _, ctx = make_context()
        _, stores = repository.load()
        stores.update({"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history})

        repository.save()
        for name, collection in collections.items():
            collection.delete_many.assert_called_once_with({})
            collection.insert_many.assert_called_once_with(stores[name].to_dicts())

    # Test 69 - Reflect quantity changes and deletions in saved records.
    # Expected: Updated quantities are sent and deleted items are not reinserted.
    def test_updates_and_deletions_are_saved(self, mongo_repository, make_context):
        repository, _, collections = mongo_repository
        _, ctx = make_context()
        _, stores = repository.load()
        stores["fridge"] = ctx.fridge
        item = ctx.fridge.get_items()[0]

        item.set_quantity(2)
        repository.save()
        assert collections["fridge"].insert_many.call_args.args[0][0]["Quantity"] == 2

        for collection in collections.values():
            collection.reset_mock()
        ctx.fridge.remove_item(item)
        repository.save()
        collections["fridge"].delete_many.assert_called_once_with({})
        collections["fridge"].insert_many.assert_not_called()

    # Test 70 - Save empty stores without inserting an empty document list.
    # Expected: Collections are cleared and insert_many is not called.
    def test_save_empty_stores(self, mongo_repository):
        repository, _, collections = mongo_repository
        repository.save()
        for collection in collections.values():
            collection.delete_many.assert_called_once_with({})
            collection.insert_many.assert_not_called()

    # Test 71 - Release the database client through the repository.
    # Expected: Closing the repository closes its client.
    def test_close_client(self, mongo_repository):
        repository, client, _ = mongo_repository
        repository.close()
        client.close.assert_called_once_with()
#endregion
#endregion

# =========================================================
# 6. STORAGE PATH AND LOGGER TESTS
# Input: Shared application paths and temporary log files.
# Expected: Stable storage configuration and preserved logs.
# =========================================================
#region Storage Paths And Logging
class TestStoragePathsAndLogger:
    # Test 72 - Anchor application storage paths to the project directory.
    # Expected: Changing the working directory does not change the configured paths.
    def test_paths_are_project_relative(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_root = Path(__file__).resolve().parent
        assert AppPaths.PROJECT_ROOT == project_root
        assert AppPaths.DATABASE_DIR == project_root / "app_data" / "database"
        assert AppPaths.LOGS_DIR == project_root / "app_data" / "logs"
        assert AppPaths.OFFLINE_MARKER == AppPaths.DATABASE_DIR / ".offline_changes"

    # Test 73 - Append log messages without overwriting earlier messages.
    # Expected: Both messages remain in the selected temporary log file.
    def test_logger_preserves_messages(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger = Logger(logs_dir=log_dir)
        logger.send_log("First message")
        logger.send_log("Second message")
        assert log_dir.is_dir()
        assert Path(logger.filename).read_text(encoding="utf-8").splitlines() == ["First message", "Second message"]
#endregion

# =========================================================
# 7. APPLICATION STARTUP AND SAVE RECOVERY TESTS
# Input: Mocked cloud failures, temporary local storage,
# simulated user choices and an unavailable AI provider.
# Expected: Safe startup, preserved changes and accurate
# success/failure reporting without live services.
# =========================================================
#region Application Startup And Save Recovery Tests
class TestApplicationStartupAndRecovery:
    # Test 74 - Select local JSON when cloud startup fails.
    # Expected: Existing local records load and the user is informed of the fallback.
    def test_cloud_startup_failure_uses_json(self, tmp_path, pending_local_changes):
        _, expected = pending_local_changes
        ui = MagicMock()
        ui.send_message.side_effect = print
        cloud_factory = MagicMock(side_effect=OSError("Cloud unavailable"))
        manager = DB_manager(ui, database_dir=tmp_path, use_mongo=True, mongo_factory=cloud_factory)

        stores = manager.start()

        cloud_factory.assert_called_once_with()
        assert manager.is_local is True
        assert isinstance(manager.repository, JsonRepository)
        assert {name: store.to_dicts() for name, store in stores.items()} == expected
        assert manager.offline_marker.exists()
        assert any("Using local JSON" in call.args[0] for call in ui.send_message.call_args_list)
        ui.ask_upload_offline_changes.assert_not_called()

    # Test 75 - Save the latest objects locally when a cloud save fails.
    # Expected: Local data reflects the latest edits and a pending-upload marker is created.
    def test_cloud_save_failure_preserves_latest_data(self, tmp_path, recovery_cloud):
        cloud, stores = recovery_cloud
        ui = MagicMock()
        ui.send_message.side_effect = print
        manager = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: cloud)
        manager.start()

        # Change data after startup so the test verifies the latest state is saved.
        stores["fridge"].get_items()[0].set_quantity(4)
        cloud.save.side_effect = OSError("Connection lost")
        manager.save()

        errors, local = JsonRepository(folder=tmp_path).load()
        assert errors == []
        assert local["fridge"].get_item_total("milk", include_expired=True) == pytest.approx(4)
        assert local["household"].to_dicts() == stores["household"].to_dicts()
        assert local["consumption_history"].to_dicts() == stores["consumption_history"].to_dicts()
        assert manager.offline_marker.exists()
        assert any("Changes saved locally" in call.args[0] for call in ui.send_message.call_args_list)

    # Test 76 - Report failure when both cloud and local fallback saving fail.
    # Expected: No success message or new upload marker is produced.
    def test_local_fallback_failure_is_reported(self, tmp_path, recovery_cloud):
        cloud, _ = recovery_cloud
        ui = MagicMock()
        ui.send_message.side_effect = print
        manager = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: cloud)
        manager.start()
        ui.reset_mock()

        # Simulate failure of both cloud saving and the local JSON fallback.
        cloud.save.side_effect = OSError("Cloud save failed")
        with patch.object(JsonRepository, "save", side_effect=OSError("Disk unavailable")) as local_save:
            # Verify the application reports that neither destination could save.
            with pytest.raises(RuntimeError, match="Could not save the local fallback") as captured:
                manager.save()
            # Confirm the local fallback was actually attempted.
            local_save.assert_called_once_with()

        print(f"Expected error: {captured.value}")

        assert not manager.offline_marker.exists()
        assert not any("Changes saved locally" in call.args[0] for call in ui.send_message.call_args_list)

    # Test 77 - Preserve the marker and local files when offline upload fails.
    # Expected: Pending changes remain available and startup does not overwrite them.
    def test_failed_offline_upload_preserves_pending_changes(self, tmp_path, recovery_cloud, pending_local_changes):
        cloud, cloud_stores = recovery_cloud
        marker, expected_local = pending_local_changes
        original_cloud_fridge = cloud_stores["fridge"]
        original_files = {name: (tmp_path / f"{name}.json").read_bytes() for name in expected_local}
        ui = MagicMock()
        ui.send_message.side_effect = print
        ui.ask_upload_offline_changes.return_value = True
        cloud.save.side_effect = OSError("Upload interrupted")
        manager = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: cloud)

        with pytest.raises(RuntimeError, match="Offline upload failed") as captured:
            manager.start()
        print(f"Expected error: {captured.value}")

        assert marker.exists()
        assert cloud_stores["fridge"] is original_cloud_fridge
        for name, content in original_files.items():
            assert (tmp_path / f"{name}.json").read_bytes() == content
        assert not any("Offline changes uploaded" in call.args[0] for call in ui.send_message.call_args_list)

    # Test 78 - Remove the pending marker only after a successful upload.
    # Expected: The cloud repository receives local data while the marker still exists.
    def test_successful_offline_upload_removes_marker_after_save(self, tmp_path, recovery_cloud, pending_local_changes):
        cloud, cloud_stores = recovery_cloud
        marker, expected_local = pending_local_changes
        ui = MagicMock()
        ui.send_message.side_effect = print
        ui.ask_upload_offline_changes.return_value = True

        # Inspect the state at the exact moment cloud saving is attempted.
        def verify_upload():
            assert marker.exists()
            assert {name: store.to_dicts() for name, store in cloud_stores.items()} == expected_local

        cloud.save.side_effect = verify_upload
        manager = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: cloud)
        manager.start()

        cloud.save.assert_called_once_with()
        assert not marker.exists()
        assert any("Offline changes uploaded" in call.args[0] for call in ui.send_message.call_args_list)

    # Test 79 - Prevent incomplete pending data from replacing cloud records.
    # Expected: Missing local files stop the upload and preserve the marker.
    def test_missing_pending_file_stops_upload(self, tmp_path, recovery_cloud, pending_local_changes):
        cloud, _ = recovery_cloud
        marker, _ = pending_local_changes
        (tmp_path / "household.json").unlink()
        ui = MagicMock()
        ui.send_message.side_effect = print
        ui.ask_upload_offline_changes.return_value = True
        manager = DB_manager(ui, database_dir=tmp_path, mongo_factory=lambda: cloud)

        with pytest.raises(RuntimeError, match="local database file is missing") as captured:
            manager.start()
        print(f"Expected error: {captured.value}")

        cloud.save.assert_not_called()
        assert marker.exists()

    # Test 80 - Save completed consumption edits when AI generation fails.
    # Expected: Consumption is persisted without checking out the planned cart.
    def test_ai_failure_saves_edits_without_checkout(self, tmp_path, make_context):
        _, ctx = make_context(fridge_quantity=2, history_quantities=())
        repository = JsonRepository(folder=tmp_path)
        _, stores = repository.load()
        stores.update({"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history})
        repository.save()

        ui = MagicMock()
        ui.send_message.side_effect = print
        ui.ask_main_menu_choice.return_value = "1"
        ui.ask_last_use_days.return_value = 7
        ui.get_consumption_remarks.return_value = "none"
        ui.ask_days_until_next.return_value = 7
        ui.ask_use_recommended_cart.return_value = False
        ui.get_cart_remarks.return_value = "none"

        # Simulate a real consumption update through the existing domain methods.
        def record_consumption(fridge, history, days, remarks):
            history.add_record(fridge.consume("milk", 1, "l", days, remarks))

        ui.get_consumption.side_effect = record_consumption

        # Simulate a planned purchase that must not enter the fridge after AI failure.
        def enter_cart(cart, fridge, history):
            cart.add_item(CartItem("milk", 3, "l"))

        ui.enter_grocery_list.side_effect = enter_cart
        ai_manager = MagicMock()
        ai_manager.get_ai_recommendations.return_value = (None, "AI unavailable")
        logic_manager = MagicMock()
        data_manager = DB_manager(ui, database_dir=tmp_path, use_mongo=False)
        application = Application(ui=ui, data_manager=data_manager, ai_manager=ai_manager, logic_manager=logic_manager)

        with patch.object(Cart, "checkout") as checkout:
            with pytest.raises(RuntimeError, match="AI recommendation failed: AI unavailable") as captured:
                application.run()
            print(f"Expected error: {captured.value}")
            checkout.assert_not_called()

        errors, saved = JsonRepository(folder=tmp_path).load()
        assert errors == []
        assert saved["fridge"].get_item_total("milk", include_expired=True) == pytest.approx(1)
        records = saved["consumption_history"].to_dicts()
        assert len(records) == 1
        assert records[0]["Quantity"] == 1
        assert data_manager.offline_marker.exists()
        logic_manager.process_recommendations.assert_not_called()
        ui.shopping_cart_conclusion.assert_not_called()
        ui.show_exit.assert_not_called()

    # Test 81 - Import the entry point without starting the interactive workflow.
    # Expected: Import-style execution does not run the application or request input.
    def test_main_import_does_not_start_application(self):
        with patch("Application.Application") as application_class:
            with patch("builtins.input", side_effect=AssertionError("Unexpected input")) as user_input:
                runpy.run_path(str(AppPaths.PROJECT_ROOT / "main.py"), run_name="test_import")

        application_class.assert_not_called()
        user_input.assert_not_called()

    # Test 82 - Start and exit through the returning-user menu.
    # Expected: The application loads data, saves on exit and does not request AI output.
    def test_startup_and_save_exit(self, make_context):
        _, ctx = make_context()
        ui = MagicMock()
        ui.send_message.side_effect = print
        ui.ask_main_menu_choice.return_value = "3"
        data_manager = MagicMock()
        data_manager.start.return_value = {"fridge": ctx.fridge, "household": ctx.household, "consumption_history": ctx.history}
        ai_manager = MagicMock()
        application = Application(ui=ui, data_manager=data_manager, ai_manager=ai_manager, logic_manager=MagicMock())

        application.run()

        data_manager.start.assert_called_once_with()
        ui.show_welcome.assert_called_once_with()
        ui.show_welcome_back.assert_called_once_with(ctx.household)
        data_manager.save.assert_called_once_with()
        ui.show_exit.assert_called_once_with()
        ai_manager.get_ai_recommendations.assert_not_called()

    # Test 83 - Simulate a missing dependency during application startup.
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

    # Test 84 - Simulate an unavailable AIManager class during application startup.
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
#endregion