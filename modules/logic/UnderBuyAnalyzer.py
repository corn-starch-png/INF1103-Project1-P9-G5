from .ItemAnalyzer import ItemAnalyzer
from .AnalysisContext import AnalysisContext
from .Finding import Finding
from modules.core.CartItem import CartItem
from logger import app_logger

class UnderBuyAnalyzer(ItemAnalyzer):        
    ANALYZER_NAME = "UnderBuy"
    def analyze(self, item: CartItem, ctx: AnalysisContext):
            if self.__should_analyze(item, ctx) == False:
                return Finding(
                        analyzer_name= self.ANALYZER_NAME,
                        result=False,
                        message=None
                        ) 
            
            item_name = item.name
            item_quantity= item.quantity
            item_unit = item.unit
            ai_data = item.get_ai_data #getting ai data instance from CartItem(ItemRecord)
            estimated_consumption_rate = ai_data.consumption_rate
            
        # processing dates and calculating new variable with them
            if estimated_consumption_rate > 0: 
                daily_consumption_rate = estimated_consumption_rate / 7
                quantity_needed = daily_consumption_rate * ctx.next_purchase_date
                amount_to_topup = round (quantity_needed - ctx.get_total_items(item_name), 2)
        
                if amount_to_topup > 0:
                    result = True
                    message = f"{item_quantity}{item_unit} of {item_name} is predicted to finish before your next grocery run, recommended to buy more"
        
                elif amount_to_topup <=0:
                    result = False
                    message = None
                    app_logger.send_log(f"[LOGIC] underbuy: additional {item_name} is not needed")
                    
                return Finding(
                        analyzer_name= self.ANALYZER_NAME,
                        result=result,
                        message=message
                        ) 
        
            else:
                app_logger.send_log(f"[LOGIC] underbuy cannot be determined (estimated_consumption_rate <= 0) for {item_name}")
                return Finding(
                        analyzer_name= self.ANALYZER_NAME,
                        result=False,
                        message=None
                        ) 

    def __should_analyze(self, item: CartItem, ctx: AnalysisContext) -> bool:
        """Checking if CalorieSurplus and RiskOfExpiry is false here instead of Cart Evaluator to adhere to LSP"""
        findings = ctx.findings
        for finding in findings:
            if finding.analyzer_name == "CaloriesSurplus":
                cal_result = finding.result
            # Skip under buy analysis only when this exact item has an expiry warning.
            if finding.analyzer_name == "RiskOfExpiry" and finding.result is True and finding.item_name == item.name:
                return False
        if cal_result == False:
            return True
        return False

    