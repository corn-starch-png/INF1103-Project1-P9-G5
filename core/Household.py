from Person import Person


class Household:
    """Holds the people who live in the household (aggregation of Person)."""

    def __init__(self):
        self.__members = []

    def add_member(self, person: Person) -> None:
        if not isinstance(person, Person):
            raise TypeError("Only Person objects can be added to a Household.")
        if not person.validate():
            raise ValueError("Cannot add an invalid Person to the Household.")
        self.__members.append(person)

    def get_members(self) -> list:
        """Return a copy of the member list so callers cannot change it directly."""
        return list(self.__members)
