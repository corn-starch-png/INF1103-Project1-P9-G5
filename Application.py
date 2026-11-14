import os
from dotenv import load_dotenv
from modules.ai.AI_manager import AIManager
from modules.ai.OpenRouterProvider import OpenRouterProvider
from modules.core.Cart import Cart
from modules.io.IO_manager import IO_manager
from modules.logic.CartRecommender import CartRecommender
from modules.logic.AnalysisContext import AnalysisContext
from modules.logic.Logic_manager import Logic_manager
from modules.repositories.DB_manager import DB_manager

# Coordinate the user workflow while allowing tests to replace external dependencies.
class Application:
    def __init__(self, ui=None, data_manager=None, ai_manager=None, logic_manager=None):
        self.ui = ui if ui is not None else IO_manager()
        self.data_manager = data_manager
        self.ai_manager = ai_manager if ai_manager is not None else AIManager(OpenRouterProvider())
        self.logic_manager = logic_manager if logic_manager is not None else Logic_manager()

    # Select a household first and rebind its stores after switches or conflict reloads.
    def run(self):
        # Load configuration only when the application is explicitly started.
        load_dotenv()

        if self.data_manager is None:
            self.data_manager = DB_manager(self.ui, use_mongo=os.getenv("USE_MONGO", "1") == "1")

        self.ui.show_welcome()
        # The session controller owns startup and recovery menus; the data manager owns storage.
        self.session = self.data_manager.session()
        stores = self.session.start()
        while stores is not None:
            fridge = stores["fridge"]
            household = stores["household"]
            history = stores["consumption_history"]
            if not household.get_members():
                self.ui.send_message(f"Complete setup for {household.name} ({household.household_id}).")
                self.ui.initialize_household(household)
                self.ui.show_profile(household)
                self.ui.initialize_fridge(fridge)
                self.ui.display_fridge(fridge)
                # Let the session report setup completion according to the actual save outcome.
                self.session.save_setup()
                stores = self.data_manager.stores
                continue
            self.ui.show_welcome_back(household)
            choice = self.ui.ask_main_menu_choice()
            if choice == "1":
                days = self.ui.ask_last_use_days()
                remarks = self.ui.get_consumption_remarks()
                self.ui.get_consumption(fridge, history, days, remarks)
                if self._plan_groceries(fridge, household, history):
                    self.ui.show_exit()
                    return
            elif choice == "2":
                self.ui.update_fridge(fridge)
            elif choice == "3":
                if self.session.save_interactive():
                    self.ui.show_exit()
                    return
            stores = self.data_manager.stores

    # Grocery logic receives only the selected household's objects.
    def _plan_groceries(self, fridge, household, history):
        # Offer the initial history based cart before collecting planned purchases.
        days_until_next = self.ui.ask_days_until_next()
        cart = Cart()
        recommended_cart = CartRecommender(fridge, history).generate_recommendation()

        if recommended_cart.get_items():
            if self.ui.ask_use_recommended_cart(recommended_cart):
                cart = recommended_cart
        else:
            self.ui.show_no_recommendations()

        self.ui.enter_grocery_list(cart, fridge, history)
        cart.set_remarks(self.ui.get_cart_remarks())

        # Obtain and validate AI recommendations before running business rules.
        self.ui.send_message("Getting AI recommendations... This can take a while.")
        result, error = self.ai_manager.get_ai_recommendations(household_info=household, consumption_history=history, fridge_stock=fridge, purchase_stock=cart, remarks=cart.get_remarks(), days_until_next=days_until_next, notify=self.ui.send_message)

        if error or result is None:
            # Preserve completed edits but do not check out the unconfirmed cart.
            # Offer recovery before exiting so a failed save cannot silently lose edits.
            if not self.session.save_interactive():
                return False
            raise RuntimeError(f"AI recommendation failed: {error or 'No response returned.'}")

        cart.set_ai_enhanced(True)
        context = AnalysisContext(cart=cart, household=household, fridge=fridge, history=history, total_est_calories=result["Total_Planned_Estimated_Calories"], next_purchase_date=days_until_next)

        # Calculate confidence and evaluate calorie, expiry and under-buy findings.
        self.logic_manager.add_confidence_score(ctx=context)
        self.logic_manager.process_recommendations(ctx=context)

        calorie_messages = self.logic_manager.get_recommedations("CaloriesSurplus", False)
        if not calorie_messages:
            calorie_messages = self.logic_manager.get_recommedations("CaloriesSurplus", True)

        expiry_messages = self.logic_manager.get_recommedations("RiskOfExpiry", True)
        underbuy_messages = self.logic_manager.get_recommedations("UnderBuy", True)
        self.ui.output_recommendations(calorie_messages, expiry_messages, underbuy_messages)

        # Add only the user's confirmed cart to the fridge, then persist the result.
        self.ui.shopping_cart_conclusion(cart)
        # A rejected checkout leaves stock intact and returns the user to cart editing.
        while True:
            try:
                cart.checkout(fridge)
                break
            except ValueError as error:
                self.ui.send_message(f"Checkout not completed: {error}")
                if not self.ui.ask_retry_checkout():
                    return False
                self.ui.shopping_cart_conclusion(cart)
        # Return to the main menu when a draft needs review instead of claiming success.
        return self.session.save_interactive()
