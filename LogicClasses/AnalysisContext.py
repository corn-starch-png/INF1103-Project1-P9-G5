from datetime import date

from core.Cart import Cart
from core.Household import Household
from core.Fridge import Fridge
from core.ConsumptionHistory import ConsumptionHistory
from LogicClasses.Finding import Finding


class AnalysisContext():
    def __init__(self, 
                 cart: Cart, 
                 household: Household, 
                 fridge: Fridge, 
                 history: ConsumptionHistory,
                 total_est_calories: int,
                 today: date,
                 next_purchase_date: int,
                 remarks: str,
                 total_item: int
                ):
        self.cart = cart 
        self.household = household
        self.fridge = fridge
        self.history = history
        self.total_est_calories = total_est_calories
        self.today = today
        self.next_purchase_date = next_purchase_date
        self.remarks = remarks
        self.total_item = total_item
        self.findings = []

    def update_findings(self, new_findings: list) -> None:
            if not isinstance(new_findings, list) or any(type(item) is not Finding for item in new_findings):
                raise TypeError("findings must be a list of findings.")
            self.findings.extend(new_findings)



            