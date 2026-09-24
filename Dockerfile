FROM python:3.14-slim

WORKDIR /app

COPY python_dependencies.txt .

RUN pip install --no-cache-dir -r python_dependencies.txt

COPY . .

#main application building
#[DEV] Change the second parameter for testing specific file
#CMD ["python", "main.py"]
CMD ["python", "AI_manager.py"]