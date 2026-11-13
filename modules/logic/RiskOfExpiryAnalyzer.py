from .ItemAnalyzer import ItemAnalyzer
from .Finding import Finding
from modules.core.CartItem import CartItem
from datetime import datetime,date,timedelta
from logger import app_logger


class RiskOfExpiryAnalyzer(ItemAnalyzer):
    ANALYZER_NAME = "RiskOfExpiry"
    def analyze(self, item: CartItem, ctx):
        item_name = item.name
        item_quantity= item.quantity
        item_unit = item.unit
        ai_data = item.get_ai_data # getting ai data instance
        estimated_consumption_rate = ai_data.consumption_rate
        estimated_expiry_date = ai_data.est_expiry_date
        
        if estimated_consumption_rate > 0:
            today = date.today()
            # calculation of daily consumption rate per day
            # Retain calculation precision to prevent very small positive rates from rounding to zero
            daily_consumption_rate = estimated_consumption_rate / 7
            # daily_consumption_rate = round(estimated_consumption_rate/7 , 2)
    
            # Detect expiry risk by comparing stock with consumption possible before expiry.
            # Calculate the number of days available under the existing expiry day convention.
            item_expiry_date = datetime.strptime(estimated_expiry_date, "%Y-%m-%d").date()
            days_until_expiry = (item_expiry_date - today).days
            # Calculate consumption capacity without rounding a duration or adding it to a date.
            consumable_before_expiry = daily_consumption_rate * days_until_expiry
            # Flag a risk when total stock exceeds that consumption capacity.
            if ctx.get_total_items(item_name) > consumable_before_expiry:
                app_logger.send_log(f"[LOGIC] Risk of expiry is True for {item_name}")
                result = True
                message = f"{item_quantity}{item_unit} of {item_name} --> estimated expiry: {item_expiry_date}. (avg consumption: {estimated_consumption_rate} {item_unit} a week)"
            else:
                result = False
                app_logger.send_log(f"[LOGIC] Risk of expiry is False for {item_name}")
                message = None
                
            # Associate the calculated expiry result with the exact cart item.
            return Finding(analyzer_name=self.ANALYZER_NAME, result=result, message=message, item_name=item_name)
        else:
            # estimated_consumption_rate <= 0:
            app_logger.send_log(f"[LOGIC] Risk of expiry cannot be determined (estimated_consumption_rate <= 0) for {item_name}")
            # Preserve the item identity when the consumption rate prevents expiry analysis.
            return Finding(analyzer_name=self.ANALYZER_NAME, result=False, message=None, item_name=item_name)