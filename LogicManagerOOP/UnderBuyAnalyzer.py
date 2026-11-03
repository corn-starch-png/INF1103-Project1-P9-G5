from Analyzer import Analyzer
from DB_manager import send_log
from datetime import datetime,date,timedelta
from Finding import Finding

class UnderbuyAnalyzer(Analyzer):
    def __init__(self, analyzer_name):
        super().__init__(analyzer_name)
        
    # evaluate if calories_surplus and risk_of_expiry is both true or false
    def should_evaluate(extra_cal, expires_soon):
        return extra_cal is False and expires_soon is False
    
    def analyze(self, item, next_purchase_date, total_amt):
        # processing dates and calculating new variable with them
            if item["Estimated_Consumption_Rate"] >0: #no consumption rate how uw me calculate? just ignore. 
                today = date.today()
                #prevents small positive consumption rates from being rounded down to zero before division.
                daily_consumption_rate = item["Estimated_Consumption_Rate"] / 7
                item_expiry_date = datetime.strptime(item["Estimated_Expiry_Date"], "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
                
                #calculating Nth amount needed to not run out of food
                next_purchase_date = datetime.strptime(next_purchase_date, "%Y-%m-%d").date()
                days_to_next_purchase = (next_purchase_date - today).days  #extra n from datetime.timedelta(days=n)
                quantity_needed = daily_consumption_rate * days_to_next_purchase
                amount_to_topup = round (quantity_needed - total_amt, 2)
        
                if amount_to_topup > 0:
                    result = True
                    message = f"{item["Planned_Quantity"]} {item["Unit"]} of {item["Item_Name"]} is predicted to finish before your next grocery run, recommended to buy more"
        
                elif amount_to_topup <=0:
                    result = False
                    message = None
                    send_log(f"[LOGIC] underbuy: additional {item["Item_Name"]} is not needed")
                    
                return Finding(
                        analyzer_name= self.__analyzer_name,
                        result=result,
                        message=message
                        ) 
        
            elif item["Estimated_Consumption_Rate"] <=0:
                send_log(f"[LOGIC] underbuy cannot be determined (estimated_consumption_rate <= 0) for {item["Item_Name"]}")
                return False, None
            else:
                return None
        
    