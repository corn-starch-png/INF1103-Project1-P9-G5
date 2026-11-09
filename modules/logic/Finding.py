# returns the outcome of analyzer name, booleaaan and message from each analyzer
class Finding:
    # Store an analysis result and optionally identify the item it belongs to.
    def __init__(self, analyzer_name, result, message, item_name=None):
        # Store the analyzer outcome and its display message.
        self.analyzer_name = analyzer_name
        self.result = result
        self.message = message
        # Use None for findings that apply to the whole cart.
        self.item_name = item_name
        
    def __str__(self):
        return f"[{self.analyzer_name}] Result: {self.result} | Message: {self.message}"
            