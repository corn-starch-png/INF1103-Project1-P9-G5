from .Record import Record


class Person(Record):
    """A member of the household."""

    MAX_NAME_LENGTH = 50
    MAX_DIETARY_LENGTH = 200
    MIN_AGE = 1
    MAX_AGE = 120
    VALID_GENDERS = ("Male", "Female")

    def __init__(self, id: int, name: str, age: int, gender: str, dietary_restriction: str = ""):
        self.__id = id
        self.__name = name
        self.__age = age
        self.__gender = gender
        self.__dietary_restriction = dietary_restriction

    def get_id(self) -> int:
        return self.__id

    def get_name(self) -> str:
        return self.__name

    def get_age(self) -> int:
        return self.__age

    def get_gender(self) -> str:
        return self.__gender

    def get_dietary_restriction(self):
        return self.__dietary_restriction

    def validate(self) -> bool:
        #validate ID
        if not isinstance(self.__id, int) or self.__id <= 0:
            return False
        #validate name
        if not isinstance(self.__name, str) or not self.__name.strip():
            return False
        if len(self.__name) > self.MAX_NAME_LENGTH:
            return False
        #validate age
        if type(self.__age) is not int or not self.MIN_AGE <= self.__age <= self.MAX_AGE:
            return False
        #validate gender
        if self.__gender not in self.VALID_GENDERS:
            return False
        #validate dietary restriction
        if not isinstance(self.__dietary_restriction, str):
            return False
        if len(self.__dietary_restriction) > self.MAX_DIETARY_LENGTH:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "Person_ID": self.__id,
            "Name": self.__name,
            "Age": self.__age,
            "Gender": self.__gender,
            "Dietary_Restriction": self.__dietary_restriction,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Person":
        return cls(
            id=data["Person_ID"],
            name=data["Name"],
            age=data["Age"],
            gender=data["Gender"],
            dietary_restriction=data.get("Dietary_Restriction", ""),
        )

    def get_information(self):
        # Returns a dictionary containing the person's information. used for calorie surplus 
        return {
            "ID": self.__id,
            "Name": self.__name,
            "Age": self.__age,
            "Gender": self.__gender,
            "Dietary_Restriction": self.__dietary_restriction,
        }
