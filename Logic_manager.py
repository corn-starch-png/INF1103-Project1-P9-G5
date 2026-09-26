import json 

def get_user_input(): #simulate I/O layer
    item = input("Item: ")
    unit = input("Unit: ")

    while True:
        try:
            planned_quantity = round(float(input("Planned quantity: ")), 2) #round input off to 2d.p
            if planned_quantity < 0:
                print("Quantity cannot be negative.")
                continue
            else:
                break
        except ValueError:
            print("Please enter a valid number.")

    return { # return a dictionary = passing data between functions easy
        "item": item,
        "unit": unit,
        "planned_quantity": planned_quantity
    }    

#check_over_under, first logic function 
def check_over_under(planned_quantity, recommended_quantity):

    if planned_quantity > recommended_quantity:
        return "over"

    elif planned_quantity < recommended_quantity:
        return "under"

    else:
        return "good"


#second logic funciton 
def give_recommendation(user_input, ai_data):

    result = check_over_under(
        user_input["planned_quantity"],
        ai_data["recommended_quantity"]
    )

    return {
        "result": result,
        "advice": ai_data["reason"],
        "waste_risk": None, #tTo be added
        "confidence_score": None #to be added 
    }

#execution code


#load dummy data (subjected to changes)
with open("sampleAioutput.json","r") as file:
    data = json.load(file) #load json file into var data


#getting user input (for testing purpose, I/O layer exists!)
while True:
    user_input = get_user_input()

    ai_data = None

    for recommendation in data["recommendations"]:
        if (    #checking if Ai recommendation exist for user input (in case AI omits)
            recommendation["item"].lower() == user_input["item"].lower()
            and 
            recommendation ["unit"].lower() == user_input["unit"].lower()
        ):
            ai_data = recommendation
            break

    if ai_data is None:
        print("No AI recommendation found for this item")
    else:
        result = give_recommendation(user_input, ai_data)

        print("\n--- Recommendation ---")
        print(f"Result: {result['result']}")
        print(f"Advice: {result['advice']}")
        print(f"Waste risk: {result['waste_risk']}")
        print(f"Confidence score: {result['confidence_score']}")

