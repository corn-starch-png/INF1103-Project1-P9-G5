from abc import abstractmethod, ABC
from logicclasses.AnalysisContext import AnalysisContext

class CartAnalyzer(ABC):
    @abstractmethod    
    def analyze(self, ctx: AnalysisContext):
        pass