from abc import abstractmethod, ABC
from modules.core.CartItem import CartItem
from .AnalysisContext import AnalysisContext

class ItemAnalyzer(ABC):
    @abstractmethod    
    def analyze(self, item: CartItem, ctx: AnalysisContext):
        pass