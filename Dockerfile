FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "numpy<2"

COPY . .

EXPOSE 1210

CMD ["python", "app.py"]