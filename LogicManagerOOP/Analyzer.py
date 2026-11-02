from abc import abstractmethod, ABC

class Analyzer(ABC):
    def __init__(self, analyzer_name):
        self.__analyzer_name = analyzer_name
        
    def analyzer_name(self):
        return self.__analyzer_name    
     
    @abstractmethod    
    def analyze(self):
        pass