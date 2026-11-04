from LogicManagerOOP.Analyzer import Analyzer
from LogicManagerOOP.Finding import Finding
from core.CartItem import CartItem
from datetime import datetime,date,timedelta
from DB_manager import send_log


class RiskOfExpiryAnalyzer(Analyzer):
    def __init__(self, analyzer_name):
        super().__init__(analyzer_name)
        
        
    def analyze(self, item:CartItem, total_amt_of_items):
        item_name = item.name
        item_quantity= item.quantity
        item_unit = item.unit
        ai_data = item.get_ai_data() #getting ai data instance
        estimated_consumption_rate = ai_data.consumption_rate
        estimated_expiry_date = ai_data.est_expiry_date
        
        if estimated_consumption_rate > 0:
            today = date.today()
            # calculation of daily consumption rate per day
            # Retain calculation precision to prevent very small positive rates from rounding to zero
            daily_consumption_rate = estimated_consumption_rate / 7
            # daily_consumption_rate = round(estimated_consumption_rate/7 , 2)
    
            # days taken to finish consuming the item
            estimated_days_to_consume = round(total_amt_of_items / daily_consumption_rate)
                        
            item_expiry_date = datetime.strptime(estimated_expiry_date, "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
            #if the days taken to consume an item is greater than days to expire
            if today + timedelta(days=estimated_days_to_consume) > item_expiry_date:
                send_log(f"[LOGIC] Risk of expiry is True for {item_name}")
                result = True
                message = f"{item_quantity}{item_unit} of {item_name} --> estimated expiry: {item_expiry_date}. (avg consumption: {estimated_consumption_rate} {item_unit} a week)"
            else:
                result = False
                send_log(f"[LOGIC] Risk of expiry is False for {item_name}")
                message = None
                
            return Finding(
                analyzer_name= self.get_analyzer_name,
                result=result,
                message=message
            )
        else:
            # estimated_consumption_rate <= 0:
            send_log(f"[LOGIC] Risk of expiry cannot be determined (estimated_consumption_rate <= 0) for {item_name}")
            return False, None    