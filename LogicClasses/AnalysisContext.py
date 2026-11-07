from datetime import date

from core.Cart import Cart
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory
from logicclasses.Finding import Finding


class AnalysisContext():
    def __init__(self, 
                 cart: Cart, 
                 household: Household, 
                 fridge: Fridge, 
                 history: ConsumptionHistory,
                 total_est_calories: int,
                 next_purchase_date: int,
                 remarks: str,
                ):
        self.cart = cart 
        self.household = household
        self.fridge = fridge
        self.history = history
        self.total_est_calories = total_est_calories
        self.next_purchase_date = next_purchase_date
        self.remarks = remarks
        self.findings = []

    def update_findings(self, new_findings: list) -> None:
            if not isinstance(new_findings, list) or any(type(item) is not Finding for item in new_findings):
                raise TypeError("findings must be a list of findings.")
            self.findings.extend(new_findings)

    def get_total_items(self, item_name: str) -> int:
        fridge_amt = self.fridge.get_total_quantity(item_name, include_expired=True)
        cart_item = self.cart.search_item(item_name)
        if cart_item == None:
             cart_amt = 0
        else:
            cart_amt = cart_item.quantity
        return fridge_amt + cart_amt



            