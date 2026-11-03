from DB_manager import send_log, KCAL_TABLE, BONUS_KEYWORDS_FULL_PTS, BONUS_KEYWORDS_HALF_PTS
from Analyzer import Analyzer
from Finding import Finding


class CaloriesSurplusAnalyzer(Analyzer):
    def __init__(self, analyzer_name, kcal_table, family):
        super().__init__(analyzer_name)
        self.__kcal_table = kcal_table
        self.__family = family
        
        
    def __get_age_from_KCAL(self, age: int):
        if age >= 60:
            return 60
        if age >= 30:
            return 30
        if age >= 19:
            return 19
        return age
    
    # get each calorie from each family member
    def __calculate_family_kcal(self, family_member, days_until_next_visit):
        daily_total = 0
        for person in family_member:
            age = self.__get_age_from_KCAL(person["Age"])
            gender = person["Gender"]
            daily_total += self.__kcal_table[age][gender] #male + female calorie
        return daily_total * days_until_next_visit
    
    # calculating calories surplus
    def analyze(self, total_estimated_calories, days_until_next_visit):   
    
        #extract name, gender from household info from db.json
        family_members = self.__family
        family_calorie_until_next_visit = self.__calculate_family_kcal(family_members, days_until_next_visit, KCAL_TABLE)

        send_log(f"[LOGIC] Total family calories until next visit: {family_calorie_until_next_visit}")
        
        # if total calories (AI output)  > total calories that family needs (User in put) and returns true, else false
        exceed_calorie = total_estimated_calories - family_calorie_until_next_visit
        if total_estimated_calories > family_calorie_until_next_visit:
            send_log(f"[LOGIC] Calories surplus is: True") 
            result = True
            message = (f"Grocery cart exceeds recommended calories values for {days_until_next_visit} days by {exceed_calorie}kcal")
            
        else:
            send_log(f"[LOGIC] Calories surplus is: False")
            result = False
            message = (f"Short of {abs(exceed_calorie)}kcal to hit recommended calories for {days_until_next_visit} days")
            
        return Finding(
            analyzer_name= self.__analyzer_name,
            result=result,
            message=message
        )

