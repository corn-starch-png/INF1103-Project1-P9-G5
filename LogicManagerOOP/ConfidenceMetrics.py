import statistics
from DB_manager import send_log

class ConfidenceMetrics:
    def quality_score(self, data_count):
        target_observations = 30
        if data_count <= 0:
            return 0.0
        
        k = target_observations / 2
        score = data_count / (data_count + k)
        return score
    
    def consistency_score(self, normalized_consumption):
        if len(normalized_consumption) < 2: 
            return 0.0
        sd = statistics.stdev(normalized_consumption)
        mean = statistics.mean(normalized_consumption)
        # Prevent division by zero when all consumption is zero.
        # Zero mean does not provide a meaningful coefficient of variation.
        if mean == 0: return 0.0
        cv = sd / mean
        return 1 / (1 + cv)
    
    def agreement_score(self, normalized_consumption, recAmt, fridgeAmt, days_until_next_visit):
        #calculate recommeneded quantity based on past data
        self_avg_consumption_rate = sum(normalized_consumption)/len(normalized_consumption)
        algorithm_quantity = round((self_avg_consumption_rate * days_until_next_visit) - fridgeAmt, 2)
        if algorithm_quantity < 0: # no negative recommendations
            algorithm_quantity = 0
        ai_quantity = recAmt
        send_log(f"[CONFIDENCE SCORE] calculated qty:{algorithm_quantity} AI qty: {ai_quantity}")

        if algorithm_quantity == 0 and ai_quantity == 0:
            return 1.0

        #compare AI and own calculation values
        largest_quantity = max(algorithm_quantity, ai_quantity)
        difference = abs(algorithm_quantity - ai_quantity)
        

        agreement_score = 1 - (difference / largest_quantity)
        return agreement_score
    