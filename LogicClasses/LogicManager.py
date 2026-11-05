from core.Cart import Cart
from LogicClasses.CartEvaluator import CartEvaluator
from LogicClasses.ConfidenceCalculator import ConfidenceCalculator
from LogicClasses.AnalysisContext import AnalysisContext
from LogicClasses.Finding import Finding

class LogicManager():
    def __init__(self):
        self.__cartevaluator = CartEvaluator()
        self.__confidencecalculator = ConfidenceCalculator()

    def process_recommendations(self, ctx: AnalysisContext) -> None:
        result = self.__cartevaluator.evaluate(ctx)
        return result

    def structure_recommedations(self, findings: list[Finding]) -> str:
        calorie_msg = ""
        roe_msgs = []
        underbuy_msgs = []
        for finding in findings:
            if finding.analyzer_name == "CaloriesSurplus":
                calorie_msg = finding.message
            elif finding.analyzer_name == "RiskOfExpiry" and finding.result == True:
                roe_msgs.append((finding.message))
            elif finding.analyzer_name == "UnderBuy" and finding.result == True:
                underbuy_msgs.append((finding.message))
            else:
                pass

        message = f"{'-'*15}QUANTIFRESH ANALYSIS{'-'*15}\n"
        message += f"{calorie_msg}\n"
        message += f"{'-'*50}\n"
        message += f"Based on your consumption history, the following items are likely to expire:\n"
        for msg in roe_msgs:
            message += f"{msg}\n"
        message += f"Based on your consumption history, you may run out of the following items:\n"
        for msg in underbuy_msgs:
                    message += f"{msg}\n"

        return message

    def add_confidence_score(self, ctx: AnalysisContext) -> Cart:
        for item in ctx.cart.get_items():
            score = self.__confidencecalculator.calculate_confidence_score(item, ctx)
            item.set_confidence_score(score)
        return ctx.cart     
