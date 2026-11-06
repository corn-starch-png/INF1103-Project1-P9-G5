class BonusCalculator:
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
    
    def __init__(self):
        self.__keywords = {
            "FULL": self.BONUS_KEYWORDS_FULL_PTS,
            "HALF": self.BONUS_KEYWORDS_HALF_PTS
        }
        
    #bonus score (MAX 5%)
    #bonus score is given if actionable remarks are provided to give the AI better context and hence estimations
    def bonus(self, remarks):
        if not remarks or remarks.lower() == "none":
            return 0.0
        remarks = remarks.lower()

        if any(word in remarks for word in self.__keywords["FULL"]):
            return 5.0

        if any(word in remarks for word in self.__keywords["HALF"]):
            return 2.5

        return 0.0