from Analyzer import Analyzer
from Finding import Finding
from datetime import datetime,date,timedelta
from DB_manager import send_log

class RiskOfExpiryAnalyzer(Analyzer):
    def __init__(self, analyzer_name):
        super().__init__(analyzer_name)
        self.__analyzer_name = analyzer_name
        
        
    def analyze(self, item, total_amt_of_items):
        if item["Estimated_Consumption_Rate"] > 0:
            today = date.today()
             # calculation of daily consumption rate per day
            # Retain calculation precision to prevent very small positive rates from rounding to zero
            daily_consumption_rate = item["Estimated_Consumption_Rate"] / 7
            # daily_consumption_rate = round(estimated_consumption_rate/7 , 2)
    
            # days taken to finish consuming the item
            estimated_days_to_consume = round(total_amt_of_items / daily_consumption_rate)
                        
            item_expiry_date = datetime.strptime(item["Estimated_Expiry_Date"], "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
            #if the days taken to consume an item is greater than days to expire
            if today + timedelta(days=estimated_days_to_consume) > item_expiry_date:
                send_log(f"[LOGIC] Risk of expiry is True for {item["Item_Name"]}")
                result = True
                message = f"{item["Planned_Quantity"]} {item["Unit"]} of {item["Item_Name"]} --> estimated expiry: {item_expiry_date}. (avg consumption: {item["Estimated_Consumption_Rate"]} {item["Unit"]} a week)"
            else:
                result = False
                send_log(f"[LOGIC] Risk of expiry is False for {item["Item_Name"]}")
                
            return Finding(
                analyzer_name= self.__analyzer_name,
                result=result,
                message=message
            )
        else:
            # estimated_consumption_rate <= 0:
            send_log(f"[LOGIC] Risk of expiry cannot be determined (estimated_consumption_rate <= 0) for {item["Item_Name"]}")
            return False, None    