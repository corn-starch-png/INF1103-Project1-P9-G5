from core.CartItem import CartItem
from core.Fridge import Fridge
from LogicClasses.AnalysisContext import AnalysisContext
from LogicClasses.ConfidenceMetrics import ConfidenceMetrics
from LogicClasses.BonusCalculator import BonusCalculator
from DB_manager import send_log

class ConfidenceCalculator:
    def __init__(self):
      self.__metrics = ConfidenceMetrics()
      self.__bonusMetrics = BonusCalculator()
      
    def calculate_confidence_score(self, item: CartItem, ctx: AnalysisContext) -> float:
        fridge_amt = ctx.fridge.get_total_quantity(item.name, False)
        normalized_daily_consumption = ctx.history.get_normalized_records(item.name)
        #if no previous consumption, no score can be calculated
        if normalized_daily_consumption == []:
            return 0.0

        quantity_score = self.__metrics.quality_score(len(normalized_daily_consumption))
        consistency_score = self.__metrics.consistency_score(normalized_daily_consumption)
        agreement_score = self.__metrics.agreement_score(normalized_consumption=normalized_daily_consumption, 
                                                         recAmt=item.ai_data.recommended_qty, 
                                                         fridgeAmt=fridge_amt, 
                                                         days_until_next_visit=ctx.next_purchase_date)
        confidence_score = (
            0.3 * quantity_score
            + 0.3 * consistency_score
            + 0.4 * agreement_score
        ) * 100

        bonus_score = self.__bonusMetrics.bonus(ctx.remarks)
        
        send_log(f"[CONFIDENCE SCORE] ---CONFIDENCE SCORE FOR {item.name}---")
        send_log(f"[CONFIDENCE SCORE] quantity_score: {quantity_score}")
        send_log(f"[CONFIDENCE SCORE] consistency_score: {consistency_score}")
        send_log(f"[CONFIDENCE SCORE] AI agreement_score: {agreement_score}")
        send_log(f"[CONFIDENCE SCORE] confidence_score: {confidence_score}")
        send_log(f"[CONFIDENCE SCORE] bonus_score: {bonus_score}")
        send_log(f"[CONFIDENCE SCORE] Final score: {round(min(100, confidence_score + bonus_score), 1)}")

        if confidence_score == 0: #do not add bonus if score is 0 
            return 0.0
        return round(min(100, confidence_score + bonus_score), 1)
        