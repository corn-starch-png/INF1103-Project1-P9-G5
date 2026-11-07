from core.Cart import Cart
from logicclasses.CartEvaluator import CartEvaluator
from logicclasses.ConfidenceCalculator import ConfidenceCalculator
from logicclasses.AnalysisContext import AnalysisContext
from logicclasses.Finding import Finding

class Logic_manager():
    def __init__(self):
        self.__cartevaluator = CartEvaluator()
        self.__confidencecalculator = ConfidenceCalculator()
        self.__findings = []

    def process_recommendations(self, ctx: AnalysisContext) -> None:
        result = self.__cartevaluator.evaluate(ctx)
        self.__findings = result

    def get_recommedations(self, analyzer_name: str) -> str:
        msgs = []
        for finding in self.__findings:
            if finding.analyzer_name == analyzer_name and finding.result == True:
                msgs.append((finding.message))
        return msgs

    def add_confidence_score(self, ctx: AnalysisContext) -> Cart:
        for item in ctx.cart.get_items():
            score = self.__confidencecalculator.calculate_confidence_score(item, ctx)
            item.set_confidence_score(score)
        return ctx.cart     
