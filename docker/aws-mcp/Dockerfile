FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY aws-server.py .
RUN chmod +x aws-server.py

EXPOSE 8000

CMD ["python", "aws-server.py"]