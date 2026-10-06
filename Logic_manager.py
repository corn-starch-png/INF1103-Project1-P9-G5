import json 
import statistics
import csv
from datetime import datetime

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

#calculating consumption rate
def dailyConsumptionRate(item_name, csv_path="sample_database/consumption_history.csv"):
    #daily consumption rate = total quantity consumed / no.of days 
    total_quantity = 0.0
    total_days = 0.0

    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Strip whitespace from keys and values to avoid mismatch issues
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            
            # Match the item name (case-insensitive)
            if clean_row["Item_Name"].lower() == item_name.strip().lower():
                # Parse days: "5d" -> 5.0
                days_str = clean_row["Date_Range"].lower().replace("d", "").strip()
                days = float(days_str)
                
                # Parse quantity: e.g. "1" -> 1.0
                quantity = float(clean_row["Quantity"])
                
                total_quantity += quantity
                total_days += days

    # Prevent division by zero if days is 0 or item not found
    if total_days <= 0:
        return 0.0

    # Daily consumption rate = Total Quantity / Total Days
    return round(total_quantity / total_days, 3)

#calculation for shelf life of item
def shelfLife(item_name, csv_path="sample_database/stock.csv"):
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
                

#calculating expiry risk to determine if food waste is high/medium/low
def calculateExpiryRisk(planned_quantity, recommended_quantity, dailyConsumptionRate, shelfLife):
    # checking status of planned quantity and recommended quantity
    status = check_over_under(planned_quantity, recommended_quantity)
    if status == "over":
        #to prevent division errors while handling zero consumption rate
        if dailyConsumptionRate <= 0:
            return "High Food Waste"
        
        #calculation of time required to consume the total amount
        timeToConsume = (
            ("current_quantity" #take from stock.csv 
            + planned_quantity ) / dailyConsumptionRate
        )
        
        # evaluating risk of food expiry
        if timeToConsume > shelfLife:
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

    waste_risk = calculateExpiryRisk(
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
def calculate_historical_data_consistency(data,item_name):
    fridge_file = open("fridge_history.json" , "r")
    data = json.load(fridge_file)
    quantities = [] #list to feed into stats funciton later
    for row in data: #iterate through CSV file, searchingin Item_name column to find the find item user enterd "item_name"
        if row["Item_name"].lower() == item_name.lower():
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


# ---------------V V V  execution code  V V V ---------------  


#load dummy AI data (subjected to changes)
with open("sampleAioutput.json","r") as file: #open .json with "read" mode as variable file
    data = json.load(file) #json.load converts json to python


#getting user input (for testing purpose, I/O layer exists!)
while True:
    user_input = get_user_input()

    ai_data = None

    for recommendation in data["recommendations"]:
        if (    #checking if Ai recommendation exist for user input (in case AI omits)
            recommendation["item"].lower() == user_input["item"].lower()
            and 
            recommendation ["unit"].lower() == user_input["unit"].lower()
        ):
            ai_data = recommendation
            break

    if ai_data is None:
        print("No AI recommendation found for this item")
    else:
        result = give_recommendation(user_input, ai_data)

        print("\n--- Recommendation ---")
        print(f"Result: {result['result']}")
        print(f"Advice: {result['advice']}")
        print(f"Waste risk: {result['waste_risk']}")
        print(f"Confidence score: {result['confidence_score']}")

