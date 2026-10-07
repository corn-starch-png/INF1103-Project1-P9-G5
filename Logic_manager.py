import json 
import statistics
import csv
from datetime import datetime,date,timedelta

def get_user_input(): #simulate I/O layer
    item = input("Item: ")
    unit = input("Unit: ")

    while True:
        try:
            planned_quantity = round(float(input("Planned quantity: ")), 2) #round input off to 2d.p
            if planned_quantity < 0:
                print("Quantity cannot be negative.")
                continue
            else:
                break
        except ValueError:
            print("Please enter a valid number.")

    return { # return a dictionary = passing data between functions easy
        "item": item,
        "unit": unit,
        "planned_quantity": planned_quantity
    }    

#check_over_under, first logic function 
def check_over_under(planned_quantity, recommended_quantity):
    
    if planned_quantity > recommended_quantity:
        return "over"
   
    elif planned_quantity < recommended_quantity:
        return "under"
   
    else:
        return "good"


# calculation for shelf life of item
# def shelf_life(item_name, json_path="sample_database/stock.json"):
    # Expiry date - Purchase Date
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Strip whitespace around column keys and values
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            
            if clean_row["Item_Name"].lower() == item_name.strip().lower():
                purchaseDate = datetime.strptime(clean_row["Purchase_Date"], "%Y-%m-%d")
                expiryDate = datetime.strptime(clean_row["Expiry_Date"], "%Y-%m-%d")
                
                # Total shelf life (from purchase to expiry)
                total_shelf_life = (expiryDate - purchaseDate).days
                return total_shelf_life
    #if item not found         
    return None      
                

# calculating expiry risk to determine if food waste is high/medium/low
def calculate_expiry_risk(item_name, planned_quantity, recommended_quantity, shelf_life, json_path="sample_database/stock.json"):
    # checking status of planned quantity and recommended quantity
    status = check_over_under(planned_quantity, recommended_quantity)
    if status == "over":
        #to prevent division errors while handling zero consumption rate
        if dailyConsumptionRate <= 0:
            return "High Food Waste"
        
        # retrieve quantity of item from db
        current_quantity = 0.0
        with open(json_path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            for item in data.get("stock", []):
                if item["Item_Name"].strip().lower() == item_name.strip().lower():
                    current_quantity = float(item["Quantity"])
                    break

        # 2. Calculation of time required to consume the total amount
        time_to_consume = (
            current_quantity + planned_quantity
        ) / "Ai output consumption rate"
        
        # evaluating risk of food expiry
        if time_to_consume > shelf_life:
            return "High Food Waste"
        else:
            return "Medium Food Waste"
        
    else:
        # if check_over_under is "under" and "good"
        return "Low Food Waste"
    

#second logic funciton 
def give_recommendation(user_input, ai_data):

    result = check_over_under(
        user_input["planned_quantity"],
        ai_data["recommended_quantity"]
    )

    waste_risk = calculate_expiry_risk(
        user_input["planned_quantity"],
        ai_data["recommended_quantity"],
        "current_quanity",#to be added
        "dailyConsumptionRate", # to be calculated
        "shelfLife" #to be calculated
    )
    
    return {
        "result": result,
        "advice": ai_data["reason"],
        "waste_risk": None, #To be added 
        "confidence_score": None #to be added 
    }

#first confidence score function, some funky math going on here
def calculate_historical_data_completeness(data, item_name):
    purchase_count = 0 #int value

    for row in data: 
        if row["Item_Name"].lower() == item_name.lower(): #each seperate time user goes to NTUC to buy, CS increases
            purchase_count += 1

    k = 8 #arbitary value i smoked out to control how fast completeness is given
    # K is inverse to the rate CS grows 

    completeness_score = purchase_count / (purchase_count + k) #keeping score <=1.0
    return completeness_score


#second confidence score function taking into account S/D
def calculate_historical_data_consistency(item_name): #calculate for each item 
    fridge_file = open("db.json" , "r")
    database = json.load(fridge_file)
    consumption_history = database["consumption_history"]
    fridge = database["fridge"]
    quantities = [] #list to feed into stats funciton later
    for row in consumption_history: #iterate through CSV file, searchingin Item_name column to find the find item user enterd "item_name"
        if row["Item_name"].lower() == item_name.lower() and row["Remarks"] == "None " : #find item, omit if remarks is ticked
            quantities.append(float(row["Quantity"])) #everything theres a match in item name, go to column quantity and take the value

    sd = statistics.stdev(quantities) # once list of quantities is made, calculate s/d

    if len(quantities) < 2: #can't calculate s/d with one value
        return 0.0 
   
    mean = statistics.mean(quantities)  

    if mean == 0: #so our program dont commit suicide by dividing with zero
        return 1.0

    cv = sd / mean #calculating relative standard deviation 

    consistency_score = 1 / (1 + cv) #keeping score <=1.0

    return consistency_score

def calculate_confidence_score(completeness_score,consistency_score):
    confidence_score = completeness_score * consistency_score #will add more scores if needed
    return round(confidence_score, 3) #round off to 3 d.p in case of irrational number


#under_buy will pull from basket
def under_buy(item_name, item_quantity, item_expiry_date, next_purchase_date, estimated_consumption_rate):
    today = date.today()
    # processing dates and calculating new variable with them
    if daily_consumption_rate >0: #no consumption rate how uw me calculate? just ignore. 

        daily_consumption_rate = round(estimated_consumption_rate/7 , 2)
        estimated_day_to_consume = round(item_quantity / daily_consumption_rate)
    
        item_expiry_date = datetime.strptime(item_expiry_date, "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
        day_item_is_eaten = today + timedelta(day = estimated_day_to_consume)

        #calculating Nth amount needed to not run out of food
        next_purchase_date = datetime.striptime(next_purchase_date, "%Y-%m-%d").date()
        days_to_next_purchase = next_purchase_date - today 
        quantity_needed = daily_consumption_rate * days_to_next_purchase
        amount_to_topup = quantity_needed - item_quantity

        if day_item_is_eaten < item_expiry_date:
            print(f"You will finish consuming {item_name} in {estimated_day_to_consume}.",
                  f"You should buy {amount_to_topup}more to last till your next grocery run")

        else:
            return None

    elif daily_consumption_rate <=0:
        print("Consumption rate is 0, not enough to calculate underbuy!")


# ---------------V V V  execution code  V V V ---------------  













# ---------------V V V  Deprecated code  V V V ---------------  

#getting user input (for testing purpose, I/O layer exists!)
# while True:
#     user_input = get_user_input()

#     ai_data = None

#     for recommendation in data["recommendations"]:
#         if (    #checking if Ai recommendation exist for user input (in case AI omits)
#             recommendation["item"].lower() == user_input["item"].lower()
#             and 
#             recommendation ["unit"].lower() == user_input["unit"].lower()
#         ):
#             ai_data = recommendation
#             break

#     if ai_data is None:
#         print("No AI recommendation found for this item")
#     else:
#         result = give_recommendation(user_input, ai_data)

#         print("\n--- Recommendation ---")
#         print(f"Result: {result['result']}")
#         print(f"Advice: {result['advice']}")
#         print(f"Waste risk: {result['waste_risk']}")
#         print(f"Confidence score: {result['confidence_score']}")

