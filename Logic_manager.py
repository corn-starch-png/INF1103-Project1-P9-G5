import json 
import statistics
import csv
from datetime import datetime,date,timedelta
from DB_manager import KCAL_TABLE


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

#CALORIE SURPLUS LOGIC --------------------   
# eg. if user age is 20, will fall under 19 years old calorie intake
def get_age_from_KCAL(age: int):
    if age >= 60:
        return 60
    if age > 30:
        return 30
    if age >= 19:
        return 19
    return age

# get each calorie from each family member
def calculate_family_weekly_kcal(family_member, KCAL_TABLE):
    daily_total = 0
    for person in family_member:
        age = get_age_from_KCAL(person["Age"])
        gender = person["Gender"]
        daily_total += KCAL_TABLE[age][gender] #male + female calorie
    return daily_total * 7    

# calculating calories surplus
def calories_surplus():   
    # get age and gender from db so can match calories from kcal.csv
    with open("sample_database/db.json", "r") as file:
        household_data = json.load(file)
        household_info = household_data.get("household_info", household_data)
    
    #extract name, gender from household info from db.json
    family_member = household_info.get("household_info", [])
    #calculate family weekly calorie
    family_weekly_calorie = calculate_family_weekly_kcal(family_member, KCAL_TABLE)
    print("family weekly calorie:", family_weekly_calorie)
    
    #get total estimated calories from AI output
    with open("sampleAioutput.json", "r") as ai_output:
        ai_calories = json.load(ai_output)
        total_estimated_calories = ai_calories.get("total_estiamted_calories", 0)
    # if total calories (AI output)  > total calories that family needs (User input) and returns true, else false
    if total_estimated_calories > family_weekly_calorie:
        exceed_calorie = total_estimated_calories > family_weekly_calorie    
        print("Exceeded calories values by", exceed_calorie, "kcal")
        return True
    else:
        return False

""" # calculation for shelf life of item
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
        return "Low Food Waste" """
    

#second logic funciton 
def give_recommendation(user_input, ai_data):

    result = check_over_under(
        user_input["planned_quantity"],
        ai_data["recommended_quantity"]
    )

    """ waste_risk = calculate_expiry_risk(
        user_input["planned_quantity"],
        ai_data["recommended_quantity"],
        "current_quanity",#to be added
        "dailyConsumptionRate", # to be calculated
        "shelfLife" #to be calculated
    )
     """
    return {
        "result": result,
        "advice": ai_data["reason"],
        "waste_risk": None, #To be added 
        "confidence_score": None #to be added 
    }

#first confidence score function, some funky math going on here
def calculate_historical_data_completeness(item_name, consumption_history, fridge):
    purchase_count = 0 #count how many times item was bought

    for row in consumption_history:
        if row["Item_Name"].lower() == item_name.lower() and row["Remarks"] == "None ": #each seperate time user goes to NTUC to buy, CS increases
            purchase_count += 1

    for row in fridge:
            if row["Item_Name"].lower() == item_name.lower() and row["Remarks"] == "None ": #each seperate time user goes to NTUC to buy, CS increases
                purchase_count += 1

    k = 8 #arbitary value i smoked out to control how fast completeness is given
    # K is inverse to the rate CS grows 

    completeness_score = purchase_count / (purchase_count + k) #keeping score <=1.0
    return completeness_score


#second confidence score function taking into account S/D
def calculate_data_standard_deviation(item_name,consumption_history,fridge): #calculate for each item 
    
    quantities = [] #list to feed into stats funciton later

    for row in consumption_history: #iterate through list, searchingin Item_Name column to find the find item user enterd "item_name"
        if row["Item_Name"].lower() == item_name.lower() and row["Remarks"] == "None " : #find item, omit if remarks is ticked
            quantities.append(float(row["Quantity"])) #everything theres a match in item name, go to column quantity and take the value

    for row in fridge:
        if row["Item_Name"].lower() == item_name.lower() and row["Remarks"] == "None":
                quantities.append(float(row["Quantity"])) #everything theres a match in item name, go to column quantity and take the value

    sd = statistics.stdev(quantities) # once list of quantities is made, calculate s/d

    if len(quantities) < 2: #can't calculate s/d with one value
        return 0.0 
   
    mean = statistics.mean(quantities)  

    if mean == 0: #so our program dont commit suicide by dividing with zero
        return 1.0

    cv = sd / mean #calculating relative standard deviation 

    standard_deviation = 1 / (1 + cv) #keeping score <=1.0

    return standard_deviation

def calculate_confidence_score(item_name):

    # pull out the 2 list i need to calculate confidence_score 
    fridge_file = open("./sample_database/db.json" , "r")
    database = json.load(fridge_file)
    consumption_history = database["consumption_history"]
    fridge = database["fridge"]

    standard_deviation = calculate_data_standard_deviation(item_name=item_name, consumption_history = consumption_history, fridge = fridge)
    consistency_score = calculate_historical_data_completeness(item_name = item_name ,consumption_history = consumption_history, fridge = fridge)
    confidence_score = standard_deviation * consistency_score #will add more scores if needed
    return standard_deviation, consistency_score, round(confidence_score, 3) #round off to 3 d.p in case of irrational number


#under_buy will pull from basket/grocery_list
def under_buy(item_name, planned_quantity, item_expiry_date, next_purchase_date, estimated_consumption_rate):
    today = date.today()
    # processing dates and calculating new variable with them
    if estimated_consumption_rate >0: #no consumption rate how uw me calculate? just ignore. 

        
        daily_consumption_rate = round(estimated_consumption_rate/7 , 2)
        estimated_day_to_consume = round(planned_quantity / daily_consumption_rate)
    
        item_expiry_date = datetime.strptime(item_expiry_date, "%Y-%m-%d").date() #strptime convert to date, .date() removes hh:00 part of date
        day_item_is_eaten = today + timedelta(days = estimated_day_to_consume)

        #calculating Nth amount needed to not run out of food
        next_purchase_date = datetime.strptime(next_purchase_date, "%Y-%m-%d").date()
        days_to_next_purchase = next_purchase_date - today 
        days_to_next_purchase = days_to_next_purchase.days #extra n from datetime.timedelta(days=n)
        quantity_needed = daily_consumption_rate * days_to_next_purchase
        amount_to_topup = round (quantity_needed - planned_quantity, 2)

        if day_item_is_eaten < item_expiry_date:
            print(f"You will finish consuming {item_name} in {estimated_day_to_consume} days.",
                  f"You should buy {amount_to_topup} more to last till your next grocery run")

        else:
            return None

    elif estimated_consumption_rate <=0:
        print("Consumption rate is 0, not enough to calculate underbuy!")


# ---------------V V V  execution code  V V V ---------------  

# "item": "Milk",  "planned_quantity": 3, "unit": "L", "recommended_quantity": 0.4, "consumption_rate": 1.37, "estimated_calories": 240,

# under_buy(item_name = "Milk", planned_quantity = 4, item_expiry_date = "2026-11-04",
# next_purchase_date = "2026-10-30", estimated_consumption_rate = 1.3)





print(calculate_confidence_score("Milk"))




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

