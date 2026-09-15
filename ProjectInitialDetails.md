https://github.com/corn-starch-png/LAB-P9-Team-5/
1. Problem Statement and Target Users
Problem Statement:
About a quarter of Singapore consumers admit to buying more food than they need while doing their groceries. Families do not have an efficient tool to cross-reference what they intend to buy, what they are currently eating, and what they already have at home, leading to wastage and spending on food they will not use, says study. Our application can help make purchase decisions ahead of time at checkout based on consumption patterns, inventory and food shelf life. Source


2. User Inputs
What information or data will users provide to the system?
    Item Name
    Quantity
    Unit
    Date ^
    Household Profile (size and possible dietary restrictions)*
    Consumption History since last interaction
    Manually changing estimated shelf life ^
    Barcode number(potential upgrade)
*  -> one time input at the start
^  -> optional


3. Use of AI
How will AI be utilized within the application?
    Estimate recommended amount of groceries to buy for a certain time period
    Estimate calories of groceries bought
    Categorize items (perishable or non perishable)
    Provide confidence score (Allows user to make better decisions on when to use AI suggested instructions) 

What outputs, insights, or recommendations will the AI generate from the
user inputs?
    AI will suggest or replace certain products according to health needs
    Wastage risk score (How much waste based on their original amount)
    Tips on how to manage food wastage effectively Eg. Proper storage/ Responsible disposal methods?
    Recommended quantity range for the household
    Estimated Shelf life for an item 


4. Business Rules
What business rules, validations, or decision-making logic will be applied
to the AI-generated outputs?

IF Waste risk is high AND  planned amount  > AI recommended amt AND high confidence score THEN prompt overbuy 
IF Waste risk is low AND planned amount  < AI recommended amt AND high confidence score  THEN prompt underbuy
Advice and explanation will be given and warn the user if they are overbuying/underbuying a certain product
Calculate accuracy based on AI recommended amt vs past usage/ avg calories consumed per day nutritional source
Low confidence -> manual review (feedback in case of special events like large gatherings)
Check Categorisation of items purchased (perishable vs non) -> diff logic
Calculate how much food needed based on calories consumption needed (will split between age group and gender) (technically AI accuracy check)

Current priority is to make an AI software to recommend how much groceries the user’s family needs, this recommended amount is based on calories consumption. The purpose is to prevent over/under purchase of groceries. Add features: Include more Macros (i.e vitamins, sugar, protein)  account for prices and brand preferences 


