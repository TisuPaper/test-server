FROM python:3.11-slim

WORKDIR /app

RUN pip install requests Flask

COPY client.py .

EXPOSE 5000

CMD ["python", "client.py"]