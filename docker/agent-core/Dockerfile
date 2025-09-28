FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agent-core.py .
RUN chmod +x agent-core.py

EXPOSE 8000

CMD ["python", "agent-core.py"]