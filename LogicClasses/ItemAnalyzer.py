from abc import abstractmethod, ABC
from core.CartItem import CartItem
from LogicClasses.AnalysisContext import AnalysisContext

class ItemAnalyzer(ABC):
    @abstractmethod    
    def analyze(self, item: CartItem, ctx: AnalysisContext):
        pass