from datetime import date, timedelta
from typing import List, Dict, Any

from ConfidenceCalculator import ConfidenceCalculator #calculate_confidence_score
from RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer #analyze_risk_of_expiry
from CaloriesSurplusAnalyzer import CaloriesSurplusAnalyzer #analyze_calories_surplus
from UnderBuyAnalyzer import UnderbuyAnalyzer #analyze_underbuy, should_evaluate
from core.Cart import Cart
from core.Household import Household
from core.Fridge import Fridge

confidence_calc = ConfidenceCalculator()
risk_of_expiry = RiskOfExpiryAnalyzer()
calories_surplus = CaloriesSurplusAnalyzer()
underbuy = UnderbuyAnalyzer()

 # Help check if underbuy is true
def evaluate_item(extra_cal: bool, expires_soon: bool) -> bool:
    return underbuy.should_evaluate(extra_cal, expires_soon)

def process_recommendations(
    #Calorie Surplus
    cart_items: Cart, 
    family_data: Household, 
    days_until_next_purchase: int
            ):
        
    all_findings = []
    
    total_estimated_calories = None  # Replace with AI output of total estimated calories
    cal_finding = calories_surplus.analyze(
        family=family_data, 
        total_est_calories=total_estimated_calories, 
        days_until_next_visit=days_until_next_purchase
    )
    
    if cal_finding:
        all_findings.append(cal_finding)
    extra_cal = cal_finding.get("result", False) if cal_finding else False


    for item in cart_items:
        
        # Expiry Analysis
        roe_finding = risk_of_expiry.analyze(item=item, total_amt=item.quantity)
        if roe_finding:
            all_findings.append(roe_finding)
            
        expires_soon = roe_finding.get("result", False) if roe_finding else False

        # Underbuy Analysis
        if evaluate_item(extra_cal, expires_soon):
            next_date = (date.today() + timedelta(days=days_until_next_purchase)).strftime("%Y-%m-%d")
            
            ub_finding = underbuy.analyze(
                item=item, 
                next_purchase_date=next_date, 
                total_amt=item.quantity
            )
            if ub_finding:
                all_findings.append(ub_finding)

        # Confidence Score
        score = confidence_calc.calculate_confidence_score(
            item_name=item.name,
            recommended_amt=item.quantity,
            fridge_amt=0, #need change
            days_until_next_visit=days_until_next_purchase,
            remarks="none" #need change
        )
        
    return all_findings