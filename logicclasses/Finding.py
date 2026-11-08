# returns the outcome of analyzer name, booleaaan and message from each analyzer
class Finding:
    def __init__(self, analyzer_name, result, message):
        self.analyzer_name = analyzer_name
        self.result = result
        self.message = message
        
    def __str__(self):
        return f"[{self.analyzer_name}] Result: {self.result} | Message: {self.message}"
            