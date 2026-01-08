FROM python:3.14.2-slim

WORKDIR /Projet-UE2-3

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
