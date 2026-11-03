from DB_manager import send_log
from Analyzer import Analyzer
from Finding import Finding
from core.Household import Household

class CaloriesSurplusAnalyzer(Analyzer):
    
    KCAL_TABLE={1: {'Male': 880, 'Female': 810}, 2: {'Male': 1080, 'Female': 1000}, 3: {'Male': 1160, 'Female': 1070}, 4: {'Male': 1310, 'Female': 1190}, 5: {'Male': 1440, 'Female': 1320}, 6: {'Male': 1550, 'Female': 1420}, 7: {'Male': 1600, 'Female': 1500}, 8: {'Male': 1740, 'Female': 1620}, 9: {'Male': 1940, 'Female': 1760}, 10: {'Male': 2110, 'Female': 1910}, 11: {'Male': 2280, 'Female': 2070}, 12: {'Male': 2530, 'Female': 2230}, 13: {'Male': 2740, 'Female': 2310}, 14: {'Male': 2920, 'Female': 2360}, 15: {'Male': 3030, 'Female': 2390}, 16: {'Male': 3120, 'Female': 2400}, 17: {'Male': 3180, 'Female': 2400}, 18: {'Male': 3230, 'Female': 2410}, 19: {'Male': 2700, 'Female': 2070}, 30: {'Male': 2590, 'Female': 2035}, 60: {'Male': 2235, 'Female': 1865}}
    
    def __init__(self, analyzer_name, family:Household):
        super().__init__(analyzer_name)
        self.__kcal_table = self.KCAL_TABLE
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
    def __calculate_family_kcal(self, days_until_next_visit, family:Household):
        daily_total = 0
        for person in family.get_members:
            p_dict = person.to_dict()
            age = self.__get_age_from_KCAL(p_dict["Age"])
            gender = p_dict["Gender"]
            daily_total += self.__kcal_table[age][gender] #male + female calorie
        return daily_total * days_until_next_visit
    
    # calculating calories surplus
    def analyze(self, total_estimated_calories, days_until_next_visit):   
    
        #extract name, gender from household info from Household.py
        family_calorie_until_next_visit = self.__calculate_family_kcal(days_until_next_visit, self.__family)

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
            analyzer_name= self.analyze_name,
            result=result,
            message=message
        )

