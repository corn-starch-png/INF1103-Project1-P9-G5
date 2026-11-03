from ItemFunctions import ItemFunctions



class AIRecData(ItemFunctions):
    """AI recommendation together with the user's original item."""

    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 100.0

    def __init__(self, recommended_qty: float, consumption_rate: float,
                 est_expiry_date: str):

        self.__recommended_qty = recommended_qty
        self.__consumption_rate = consumption_rate
        self.__est_expiry_date = est_expiry_date
        self.__confidence_score = 0.0
        
    #--- Getters -----------------------------------------------------
    @property
    def recommended_qty(self) -> float:
        return self.__recommended_qty

    @property
    def consumption_rate(self) -> float:
        return self.__consumption_rate

    @property
    def est_expiry_date(self) -> str:
        return self.__est_expiry_date

    @property
    def confidence_score(self) -> float:
        return self.__confidence_score


    def set_confidence_score(self, score: float) -> None:
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise TypeError("Confidence score must be a number.")
        if not self.MIN_CONFIDENCE <= score <= self.MAX_CONFIDENCE:
            raise ValueError("Confidence score must be between 0 and 100.")
        self.__confidence_score = float(score)


