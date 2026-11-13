from modules.core.CartItem import CartItem
from .Finding import Finding
from .CaloriesSurplusAnalyzer import CaloriesSurplusAnalyzer
from .RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer
from .UnderBuyAnalyzer import UnderBuyAnalyzer
from .AnalysisContext import AnalysisContext
from .CartAnalyzer import CartAnalyzer
from .ItemAnalyzer import ItemAnalyzer

class CartEvaluator():
    def __init__(self):
        self.__cart_analyzers: list[CartAnalyzer] = [CaloriesSurplusAnalyzer()]
        self.__item_analyzers: list[ItemAnalyzer] = [RiskOfExpiryAnalyzer(), UnderBuyAnalyzer()]

    def evaluate(self, ctx: AnalysisContext) -> list[Finding]:
        # Start each evaluation with fresh findings for the current cart state.
        # Remove results left by an earlier evaluation of this context.
        ctx.findings.clear()
        # Collect the new results that this evaluation will return.
        findings: list[Finding] = []

        items = ctx.cart.get_items()
        #run CartAnalyzers
        for analyzer in self.__cart_analyzers:
            result = analyzer.analyze(ctx)
            findings.append(result)
        ctx.update_findings(findings)
        
        
        for item in items:
            findings.extend(self._evaluate_item(item, ctx))
        return findings

    def _evaluate_item(self, item: CartItem, ctx: AnalysisContext):
        findings = []
        for analyzer in self.__item_analyzers:
                    result = analyzer.analyze(item, ctx)
                    findings.append(result)
                    ctx.update_findings([result])
        return findings
