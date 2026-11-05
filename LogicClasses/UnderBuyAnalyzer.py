from LogicClasses.ItemAnalyzer import ItemAnalyzer
from core.CartItem import CartItem
from DB_manager import send_log
from datetime import datetime,date,timedelta
from LogicClasses.Finding import Finding

class UnderbuyAnalyzer(ItemAnalyzer):        
    ANALYZER_NAME = "Underbuy"
    def analyze(self, item: CartItem, next_purchase_date, total_amt):
            item_name = item.name
            item_quantity= item.quantity
            item_unit = item.unit
            ai_data = item.get_ai_data #getting ai data instance from CartItem(ItemRecord)
            estimated_consumption_rate = ai_data.consumption_rate
            
        # processing dates and calculating new variable with them
            if estimated_consumption_rate >0: #no consumption rate how uw me calculate? just ignore. 
                today = date.today()
                #prevents small positive consumption rates from being rounded down to zero before division.
                daily_consumption_rate = estimated_consumption_rate / 7
                #item_expiry_date = datetime.strptime(estimated_expiry_date, "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
                
                #calculating Nth amount needed to not run out of food
                next_purchase_date = datetime.strptime(next_purchase_date, "%Y-%m-%d").date()
                days_to_next_purchase = (next_purchase_date - today).days  #extra n from datetime.timedelta(days=n)
                quantity_needed = daily_consumption_rate * days_to_next_purchase
                amount_to_topup = round (quantity_needed - total_amt, 2)
        
                if amount_to_topup > 0:
                    result = True
                    message = f"{item_quantity}{item_unit} of {item_name} is predicted to finish before your next grocery run, recommended to buy more"
        
                elif amount_to_topup <=0:
                    result = False
                    message = None
                    send_log(f"[LOGIC] underbuy: additional {item_name} is not needed")
                    
                return Finding(
                        analyzer_name= self.ANALYZER_NAME,
                        result=result,
                        message=message
                        ) 
        
            elif estimated_consumption_rate <=0:
                send_log(f"[LOGIC] underbuy cannot be determined (estimated_consumption_rate <= 0) for {item_name}")
                return False, None
            else:
                return None
        
    