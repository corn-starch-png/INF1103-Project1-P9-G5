from abc import abstractmethod, ABC
from LogicClasses.AnalysisContext import AnalysisContext

class CartAnalyzer(ABC):
    @abstractmethod    
    def analyze(self, ctx: AnalysisContext):
        pass