# Quantifresh AI Food Waste Management System

**INF1103 Programming Fundamentals with DevOps - Project 1 (P9-G5)**

A command-line household grocery planning application that integrates artificially intelligent generated purchase quantity recommendations with procedural calculations in an attempt to assist the user in food purchasing and avoiding food waste.

## Problem statement
Households can purchase more food for the period before it expires, or too little to cover the time before their next grocery shopping. It becomes difficult to manually plan based on what is already present in the household, what has been consumed and temporary changes in dietary needs.

The goal of this project is to assist families in their grocery planning using information about their household, past consumption, present stock in the refrigerator, the groceries that they have to purchase, and the number of days until they go shopping again.

## Objectives
- Recommended purchase quantities for each grocery item on the user's list
- based on recorded consumption history, current fridge stock and optional household remarks, potential food-expiry and underbuy risks,
- Calorie count for the actual consumption compared to the estimated value, and a heuristic measure of confidence generated on the basis of agreement with another calculation method.
- Choice of looking at or changing the shopping cart before saving it.
- Local storage of household, inventory and consumption data between sessions.

## Main features
| Features | Descriptions |
| :---| :--- |
| Household information | Collects the information of the members of the household and their dietary restrictions. |
| Fridge inventory | Tracks inventory within the refrigerator, including quantities, measurement units, expiration dates, and additional notes.|
| Consumption tracking | Tracks inventory and consumption over a given number of days. |
| Grocery recommendation by AI | Predicts the amount according to household information and planning shopping period. |
| Validating the response | Validates the mandatory information, value, total calories and order of grocery items. |
| Risk analysis | Tracks the difference in calorie content, expiration chance and shortage. |
| Confidence index | Tracks the combined score of amount of historical information, consumption predictability and conformity to the rule-based prediction; **not the percent of AI accuracy.** |
| Failover of the model | Retries failed AI requests and may utilize other models. |
| Shopping cart evaluation | Displays the initial and predicted amount and gives users the opportunity to adjust their shopping cart. |
| Data persistence | Persistency of data in JSON format and operations logs. |

## Application workflow

1. Load existing database or create an empty data set for a fresh setup.
2. Create a record of a new family, or update quantity of goods in an existing family.
3. Enter planned purchases, next purchase interval and any additional information.
4. Send above data to the designated AI model.
5. Verify results of the AI execution, including correct item identification, quantity, unit of measure and order.
6. Evaluate calorie comparisons, expiry risk, underbuy conditions and confidence scores.
7. Show recommendations and let the user edit the grocery cart.
8. Save the confirmed purchases and updated database.

## Project structure
```text
.
├── main.py                  # Main application workflow
├── IO_manager.py            # Command-line input, menus and display
├── DB_manager.py            # JSON database operations and logging
├── AI_manager.py            # AI API, prompt, validation and fallback
├── Logic_manager.py         # Calorie, expiry, underbuy and confidence logic
├── python_dependencies.txt  # Python packages
├── Dockerfile               # Container build instructions
├── compose.yaml             # Container settings and persistent volumes
├── .env.example             # Example environment configuration
├── test_script.py           # Automated tests, when included in the repository
├── database/                # Created/used at runtime
│   └── db.json              # Local user data
└── logs/                    # Runtime logs
```

The application was developed using procedural programming that includes functions. This particular application was divided into four unique modules where each module performed a particular task. Some of these tasks included user interface management, data management, the execution of artificial intelligence functionalities, and the processing of business logic. The main.py file is accountable for sequential execution among these modules.

## Requirements
- Docker Desktop with Docker Compose
- Internet access for live AI recommendations.
- A valid Open Router API key and AI model configuration.

## Setup and run with Docker (Recommended)
From the project root directory:
**1. Create local environment file.** Copy `.env.example` and rename to `.env`, then replace the example `API_KEY` with personal API key retrieve from Open Router.
PowerShell:
```powershell
Copy-Item .env.example .env
```
macOS / Linux:
```bash
cp .env.example .env
```
**2. Configure the AI models in `.env`.** The project expects these variables:
```dotenv
API_KEY=your_api_key_here
API_URL=https://openrouter.ai/api/v1
API_CONN_URL=https://openrouter.ai/api/v1/key
AI_MODEL=nvidia/nemotron-3-super-120b-a12b:free
AI_BACKUP_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
MAX_RETRIES=2
```
These models form the recommended configuration deployment, however they remain subject to real-time availability and compatibility constraints. Both models must support the applications requested `json_schema` response format. `MAX_RETRIES=2` allows up to 3 attempts per model.

**3. Build and run the application.**
```bash
docker compose build
docker compose run --rm quantifresh
```
The Compose configuration mounts `./database` and `./logs`, so data and logs remain on host after the container exits, allowing persistent storage. Follow the interactive prompts in the terminal to start using the cli application.

## Run without Docker
After creating and configuring `.env`, please run the following commands:
```bash
python -m pip install -r python_dependencies.txt
python main.py
```
Use the project's Python 3.14 Docker image as the runtime environment.

## Automated tests
The `test_script.py` is included in this project repository, so that tests can be run without making live API calls when they use static AI responses.
Locally:
```bash
python -m pytest test_script.py -v
```
With Docker Compose:
```bash
docker compose run --rm quantifresh python -m pytest test_script.py -v
```
The test suite will need to cover output structure, preservation of grocery list data, calculations, AI misbehaving and edge cases. Passing test suite/CICD success can be added here once verified separately.

## Data, privacy and configuration
- `.env` contains an API credential. **Never commit it to Git.** Commit only the placeholder `.env.example` file.
- `database/db.json` stores household and food-inventory information; log files may also contain household data. Do not commit personal data.
- Ensure `.gitignore` excludes `.env`, runtime database JSON, `logs/`, Python caches and local virtual environments.
- The application stores information locally in a JSON file. It does not provide multi-user authentication or encrypted storage.

## Known limitations
- AI-generated nutrition, consumption and expiration estimates are approximate and should be reviewed by the user.
- An unknown AI expiry estimate may use a **365-day placeholder** in the current implementation. It must not be treated as a manufacturer provided expiry date.
- The AI feature requires network connectivity and a model that supports the configured structured response format.
- AI processing is sequential; response delivery may require a wait time of up to four minutes.

## Troubleshooting
| Problem | What to check |
| :--- | :--- |
| `.env` file not found | Create `.env` in the same directory as `compose.yaml`. |
| API authentication error | Check `API_KEY` and the configured API URLs, is not empty or malform. |
| Model request rejected | Verify the model exists and supports `json_schema`. |
| Slow or failed AI request | Check network connectivity, rate limits, retries and the backup model. |
| Database does not persist | Check the `./database:/app/database` volume mapping. |
| Tests not found | Ensure `test_script.py` is present in the project root folder. |

## Development and DevOps
This repository is intended for collaborative development using Git. Docker provides a consistent runtime, while pytest supports repeatable local testing. 
