FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY sqlite-server.py .
RUN chmod +x sqlite-server.py

EXPOSE 8000

CMD ["python", "sqlite-server.py"]