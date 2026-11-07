from core.CartItem import CartItem
from logicclasses.Finding import Finding
from logicclasses.CaloriesSurplusAnalyzer import CaloriesSurplusAnalyzer
from logicclasses.RiskOfExpiryAnalyzer import RiskOfExpiryAnalyzer
from logicclasses.UnderBuyAnalyzer import UnderBuyAnalyzer
from logicclasses.AnalysisContext import AnalysisContext

class CartEvaluator():
    def __init__(self):
        self.__cart_analyzers = [CaloriesSurplusAnalyzer()]
        self.__item_analyzers = [RiskOfExpiryAnalyzer(), UnderBuyAnalyzer()]

    def evaluate(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []

        items = ctx.cart.get_items()
        #run CartAnalyzers
        for analyzer in self.__cart_analyzers:
            result = analyzer.analyze(ctx)
            findings.append(result)
        print(f"fingier{findings}")
        ctx.update_findings(findings)
        
        
        for item in items:
            findings.extend(self._evaluate_item(item, ctx))
        return findings

    def _evaluate_item(self, item: CartItem, ctx: AnalysisContext):
        findings = []
        for analyzer in self.__item_analyzers:
                    result = analyzer.analyze(item, ctx)
                    findings.append(result)
                    print(f"fgfdgdf{result}")
                    ctx.update_findings([result])
        return findings
