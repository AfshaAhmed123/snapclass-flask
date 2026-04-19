FROM python:3.10-slim
 
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*
 
WORKDIR /app
 
COPY requirements.txt .
 
RUN pip install --no-cache-dir cmake dlib face_recognition
 
RUN pip install --no-cache-dir -r requirements.txt
 
COPY . .
 
EXPOSE 8000
 
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
 