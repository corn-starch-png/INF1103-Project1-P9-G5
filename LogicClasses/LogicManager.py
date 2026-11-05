from datetime import date, timedelta
from typing import List, Dict, Any

from LogicClasses.ConfidenceCalculator import ConfidenceCalculator
from LogicClasses.RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer
from LogicClasses.CaloriesSurplusAnalyzer import CaloriesSurplusAnalyzer
from LogicClasses.UnderBuyAnalyzer import UnderbuyAnalyzer

from core.Cart import Cart
from core.Household import Household
from core.Fridge import Fridge


def process_recommendations(
    cart_items: Cart, 
    family_data: Household, 
    days_until_next_purchase: int
):
    # Initialize Analyzers inside the function
    confidence_calc = ConfidenceCalculator()
    risk_of_expiry = RiskOfExpiryAnalyzer(analyzer_name="RiskOfExpiryAnalyzer")
    calories_surplus = CaloriesSurplusAnalyzer(analyzer_name="CaloriesSurplusAnalyzer", family=family_data)
    underbuy = UnderbuyAnalyzer(analyzer_name="UnderbuyAnalyzer")
        
    all_findings = []
    
    total_estimated_calories = 5000 # TODO: Replace with actual AI output of total estimated calories
    
    cal_finding = calories_surplus.analyze(
        total_estimated_calories=total_estimated_calories, 
        days_until_next_visit=days_until_next_purchase
    )
    
    if cal_finding:
        all_findings.append(cal_finding)
        
    # Extract the boolean result directly from the Finding object properties
    extra_cal = cal_finding.result if cal_finding else False

    for item in cart_items:
        
        # Expiry Analysis
        roe_finding = risk_of_expiry.analyze(
            item=item, 
            total_amt_of_items=item.quantity
        )
        if roe_finding:
            all_findings.append(roe_finding)
            
        expires_soon = roe_finding.result if roe_finding else False

        # Underbuy Analysis
        if UnderbuyAnalyzer.should_evaluate(extra_cal, expires_soon):
            next_date = (date.today() + timedelta(days=days_until_next_purchase)).strftime("%Y-%m-%d")
            
            ub_finding = underbuy.analyze(
                item=item, 
                next_purchase_date=next_date, 
                total_amt=item.quantity
            )
            if ub_finding:
                all_findings.append(ub_finding)

        # Confidence Score Calculation
        score = confidence_calc.calculate_confidence_score(
            item_name=item.name,
            recommended_amt=item.quantity,
            fridge_amt=0,  # TODO: Replace with dynamic fridge quantity if available
            days_until_next_visit=days_until_next_purchase,
            remarks="none" # TODO: Map to actual item remarks if available
        )
        
    return all_findings