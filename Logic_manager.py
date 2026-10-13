import statistics
from datetime import datetime,date,timedelta
from DB_manager import send_log

KCAL_TABLE={1: {'Male': 880, 'Female': 810}, 2: {'Male': 1080, 'Female': 1000}, 3: {'Male': 1160, 'Female': 1070}, 4: {'Male': 1310, 'Female': 1190}, 5: {'Male': 1440, 'Female': 1320}, 6: {'Male': 1550, 'Female': 1420}, 7: {'Male': 1600, 'Female': 1500}, 8: {'Male': 1740, 'Female': 1620}, 9: {'Male': 1940, 'Female': 1760}, 10: {'Male': 2110, 'Female': 1910}, 11: {'Male': 2280, 'Female': 2070}, 12: {'Male': 2530, 'Female': 2230}, 13: {'Male': 2740, 'Female': 2310}, 14: {'Male': 2920, 'Female': 2360}, 15: {'Male': 3030, 'Female': 2390}, 16: {'Male': 3120, 'Female': 2400}, 17: {'Male': 3180, 'Female': 2400}, 18: {'Male': 3230, 'Female': 2410}, 19: {'Male': 2700, 'Female': 2070}, 30: {'Male': 2590, 'Female': 2035}, 60: {'Male': 2235, 'Female': 1865}}
BONUS_KEYWORDS_FULL_PTS = [
    "holiday",
    "event",
    "guests",
    "visitors",
    "party",
    "cooking",
    "travel",
    "going away",
    "stock up",
    "diet",
    "meal prep",
    "sale"
]
BONUS_KEYWORDS_HALF_PTS = [
    "less than usual",
    "more than usual",
    "eating out",
    "reduce",
    "increase",
    "sharing",
    "special occasion"
]


#CALORIE SURPLUS LOGIC --------------------   
# eg. if user age is 20, will fall under 19 years old calorie intake
def get_age_from_KCAL(age: int):
    if age >= 60:
        return 60
    if age >= 30:
        return 30
    if age >= 19:
        return 19
    return age

# get each calorie from each family member
def calculate_family_kcal(family_member, days_until_next_visit, KCAL_TABLE):
    daily_total = 0
    for person in family_member:
        age = get_age_from_KCAL(person["Age"])
        gender = person["Gender"]
        daily_total += KCAL_TABLE[age][gender] #male + female calorie
    return daily_total * days_until_next_visit   

# calculating calories surplus
def calories_surplus(database, total_estimated_calories, days_until_next_visit):   
    
    #extract name, gender from household info from db.json
    family_members = database.get("household_info", [])
    family_calorie_until_next_visit = calculate_family_kcal(family_members, days_until_next_visit, KCAL_TABLE)

    send_log(f"[LOGIC] Total family calories until next visit: {family_calorie_until_next_visit}")
    exceed_calorie = total_estimated_calories - family_calorie_until_next_visit

    # if total calories (AI output)  > total calories that family needs (User in put) and returns true, else false
    if total_estimated_calories > family_calorie_until_next_visit: 
        send_log(f"[LOGIC] Calories surplus is: True")
        return True, f"Grocery cart exceeds recommended calories values for {days_until_next_visit} days by {exceed_calorie}kcal"
    else:
        send_log(f"[LOGIC] Calories surplus is: False")
        return False, f"Short of {abs(exceed_calorie)}kcal to hit recommended calories for {days_until_next_visit} days"


    
# RISK OF EXPIRY LOGIC------------------------
# calculating risk of expiry
def risk_of_expiry(item, total_amt_of_items):
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
            return True, f"{item["Planned_Quantity"]} {item["Unit"]} of {item["Item_Name"]} --> estimated expiry: {item_expiry_date}. (avg consumption: {item["Estimated_Consumption_Rate"]} {item["Unit"]} a week)"
        else:
            send_log(f"[LOGIC] Risk of expiry is False for {item["Item_Name"]}")
            return False, None 
    else:
        # estimated_consumption_rate <= 0:
        send_log(f"[LOGIC] Risk of expiry cannot be determined (estimated_consumption_rate <= 0) for {item["Item_Name"]}")
        return False, None 



# UNDERBUY LOGIC------------------------
def under_buy(item, next_purchase_date, total_amt):
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
            return True, f"{item["Planned_Quantity"]} {item["Unit"]} of {item["Item_Name"]} is predicted to finish before your next grocery run, recommended to buy more"

        elif amount_to_topup <=0:
            send_log(f"[LOGIC] underbuy: additional {item["Item_Name"]} is not needed")
            return False, None

    elif item["Estimated_Consumption_Rate"] <=0:
        send_log(f"[LOGIC] underbuy cannot be determined (estimated_consumption_rate <= 0) for {item["Item_Name"]}")
        return False, None

def should_evaluate_underbuy(calorie_surplus, expiry_risk):
    return calorie_surplus is False and expiry_risk is False



# CONFIDENCE SCORE LOGIC--------------
# utilizes weighted scores of past consumption history's quantity, consistency and alignment of AI's recommened quantity to own estimates
def calculate_confidence_score(item_name, database, recommended_amt, fridge_amt, days_until_next_visit, remarks):
    #normalizes all history values into a single list, each entry represents the consumption rate for 1 day
    def normalize_history(item_name, consumption_history):
            normalized_daily_consumption = []
            for log in consumption_history:
                if log["Item_Name"].lower() == item_name.lower(): #take into account items with remarks as we need it to keep accurate freshness tracking
                    daily_avg_consumption = log["Quantity"]/log["Date_Range"]
                    for i in range(log["Date_Range"]):
                        normalized_daily_consumption.append(daily_avg_consumption)
            send_log(f"[CONFIDENCE SCORE] Normalized list for {item_name}:")
            send_log(f"[CONFIDENCE SCORE] {normalized_daily_consumption}")
            return normalized_daily_consumption


    #completeness score (was calculate_historical_data_completeness)
    #scores how much data is available with a target of 1mth(30 days)
    def data_quantity_score(observation_count, target_observations = 30):
        if observation_count <= 0:
            return 0.0
        k = target_observations / 2
        score = observation_count / (observation_count + k)

        return score

    #consistency score (was calculate_data_standard_deviation)
    #scores how consistent past consumption has been
    def consumption_consistency_score(normalized_daily_consumption):
        if len(normalized_daily_consumption) < 2: return 0.0
        sd = statistics.stdev(normalized_daily_consumption)
        mean = statistics.mean(normalized_daily_consumption)
        # Prevent division by zero when all consumption is zero.
        # Zero mean does not provide a meaningful coefficient of variation.
        if mean == 0: return 0.0
        cv = sd / mean
        return 1 / (1 + cv)

    #agreement score
    #scores how closely AI estimations correlate with own calculations of past data
    def ai_agreement_score(normalized_daily_consumption, recommended_amt, fridge_amt, days_until_next_visit):
        #calculate recommeneded quantity based on past data
        self_avg_consumption_rate = sum(normalized_daily_consumption)/len(normalized_daily_consumption)
        algorithm_quantity = round((self_avg_consumption_rate * days_until_next_visit) - fridge_amt, 2)
        if algorithm_quantity < 0: # no negative recommendations
            algorithm_quantity = 0
        ai_quantity = recommended_amt
        send_log(f"[CONFIDENCE SCORE] calculated qty:{algorithm_quantity} AI qty: {ai_quantity}")

        if algorithm_quantity == 0 and ai_quantity == 0:
            return 1.0

        #compare AI and own calculation values
        largest_quantity = max(algorithm_quantity, ai_quantity)
        difference = abs(algorithm_quantity - ai_quantity)
        

        agreement_score = 1 - (difference / largest_quantity)
        return agreement_score

    #bonus score (MAX 5%)
    #bonus score is given if actionable remarks are provided to give the AI better context and hence estimations
    def calculate_bonus(remarks):
        if not remarks or remarks == "none":
            return 0.0
        remarks = remarks.lower()

        if any(word in remarks for word in BONUS_KEYWORDS_FULL_PTS):
            return 5.0

        if any(word in remarks for word in BONUS_KEYWORDS_HALF_PTS):
            return 2.5

        return 0.0

    normalized_daily_consumption = normalize_history(item_name, database["consumption_history"])
    if normalized_daily_consumption == []:
        return 0.0

    quantity_score = data_quantity_score(len(normalized_daily_consumption))
    consistency_score = consumption_consistency_score(normalized_daily_consumption)
    agreement_score = ai_agreement_score(normalized_daily_consumption, recommended_amt, fridge_amt, days_until_next_visit)
    confidence_score = (
        0.3 * quantity_score
        + 0.3 * consistency_score
        + 0.4 * agreement_score
    ) * 100

    bonus_score = calculate_bonus(remarks)
    
    send_log(f"[CONFIDENCE SCORE] ---CONFIDENCE SCORE FOR {item_name}---")
    send_log(f"[CONFIDENCE SCORE] quantity_score: {quantity_score}")
    send_log(f"[CONFIDENCE SCORE] consistency_score: {consistency_score}")
    send_log(f"[CONFIDENCE SCORE] AI agreement_score: {agreement_score}")
    send_log(f"[CONFIDENCE SCORE] confidence_score: {confidence_score}")
    send_log(f"[CONFIDENCE SCORE] bonus_score: {bonus_score}")
    send_log(f"[CONFIDENCE SCORE] Final score: {round(min(100, confidence_score + bonus_score), 1)}")

    if confidence_score == 0: #do not add bonus if score is 0 
        return 0.0
    return round(min(100, confidence_score + bonus_score), 1)




