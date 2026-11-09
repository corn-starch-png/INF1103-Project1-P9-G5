from datetime import date
from modules.core.Cart import Cart
from modules.core.Household import Household
from modules.core.Fridge import Fridge
from modules.core.ConsumptionHistory import ConsumptionHistory
from .Finding import Finding


class AnalysisContext():
    def __init__(self, 
                 cart: Cart, 
                 household: Household, 
                 fridge: Fridge, 
                 history: ConsumptionHistory,
                 total_est_calories: int,
                 next_purchase_date: int,
                ):
        self.cart = cart 
        self.household = household
        self.fridge = fridge
        self.history = history
        self.total_est_calories = total_est_calories
        self.next_purchase_date = next_purchase_date
        self.findings = []

    def update_findings(self, new_findings: list) -> None:
            if not isinstance(new_findings, list) or any(type(item) is not Finding for item in new_findings):
                raise TypeError("findings must be a list of findings.")
            self.findings.extend(new_findings)

    # Return usable fridge stock + matching cart quantities, including fridge only items.
    def get_total_items(self, item_name: str) -> float:
        # Exclude expired fridge batches from the available stock.
        fridge_amt = self.fridge.get_item_total(item_name, include_expired=False)
        # Match names consistently and use zero when no cart item matches.
        cart_amt = sum(item.quantity for item in self.cart.get_items() if item.name.strip().casefold() == item_name.strip().casefold())
        # Return the combined quantity, which can include fractional units.
        return fridge_amt + cart_amt



            