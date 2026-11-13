class UnitValidator:
    """
    Finds the unit an item was entered in before (in the fridge or consumption history) so the same item is always entered in the same unit.
    """

    def __init__(self, fridge=None, history=None):
        self.__fridge = fridge
        self.__history = history

    # Match the same normalized name used by stock and history calculations.
    def find_unit(self, item_name: str, other_items: list = None) -> str:
        """
        Return the unit item_name was entered in before, or "" if it is a new item.
        """
        known_items = []
        if other_items is not None:
            known_items += [(item.name, item.unit) for item in other_items]
        if self.__fridge is not None:
            known_items += [(item.name, item.unit) for item in self.__fridge.get_items()]
        if self.__history is not None:
            known_items += [(record["Item_Name"], record["Unit"]) for record in self.__history.to_dicts()]

        for name, unit in known_items:
            if name.strip().casefold() == item_name.strip().casefold():
                return unit
        return ""
