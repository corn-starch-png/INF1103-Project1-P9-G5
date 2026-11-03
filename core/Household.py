from Person import Person
from CanBeStored import CanBeStored


class Household(CanBeStored):
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

    def to_dicts(self) -> list:
        return [person.to_dict() for person in self.__members]
 
    def load_dicts(self, rows: list) -> list:
        errors = []
        for row in rows:
            try:
                self.add_member(Person.from_dict(row))
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"Skipped invalid household row {row!r}: {error!r}")
        return errors
