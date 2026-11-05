from LogicClasses.ConfidenceMetrics import ConfidenceMetrics
from LogicClasses.BonusCalculator import BonusCalculator
from core.ConsumptionHistory import ConsumptionHistory
from DB_manager import send_log

class ConfidenceCalculator:
    def __init__(self):
      self.__metrics = ConfidenceMetrics()
      self.__history = ConsumptionHistory()
      self.__bonusMetrics = BonusCalculator()
      
    def calculate_confidence_score(self, item_name, recommended_amt, fridge_amt, days_until_next_visit, remarks):
        normalized_daily_consumption = self.__history.get_normalized_records(item_name)
        if normalized_daily_consumption == []:
            return 0.0

        quantity_score = self.__metrics.quality_score(len(normalized_daily_consumption))
        consistency_score = self.__metrics.consistency_score(normalized_daily_consumption)
        agreement_score = self.__metrics.agreement_score(normalized_consumption=normalized_daily_consumption, 
                                                         recAmt=recommended_amt, fridgeAmt=fridge_amt, days_until_next_visit=days_until_next_visit)
        confidence_score = (
            0.3 * quantity_score
            + 0.3 * consistency_score
            + 0.4 * agreement_score
        ) * 100

        bonus_score = self.__bonusMetrics.bonus(remarks)
        
        send_log(f"[CONFIDENCE SCORE] ---CONFIDENCE SCORE FOR {item_name}---")
        send_log(f"[CONFIDENCE SCORE] quantity_score: {quantity_score}")
        send_log(f"[CONFIDENCE SCORE] consistency_score: {consistency_score}")
        send_log(f"[CONFIDENCE SCORE] AI agreement_score: {agreement_score}")
        send_log(f"[CONFIDENCE SCORE] confidence_score: {confidence_score}")
        send_log(f"[CONFIDENCE SCORE] bonus_score: {bonus_score}")
        send_log(f"[CONFIDENCE SCORE] Final score: {round(min(100, confidence_score + bonus_score), 1)}")

        if confidence_score == 0: #do not add bonus if score is 0 
            return 0.0
        return round(min(100, confidence_score + bonus_score), 1)
        