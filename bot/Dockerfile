FROM python:3.12-slim-bookworm

WORKDIR /

COPY requirements.txt .

RUN pip install  --no-cache-dir -r requirements.txt && pip install psycopg[binary]

# COPY polling.py .
# COPY handlers/ ./handlers/
# COPY util/ ./util/
COPY . .

RUN ls -la > out.txt


CMD ["python", "-m", "polling"]
