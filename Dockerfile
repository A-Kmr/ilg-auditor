FROM python:3.12-slim

# Install underlying system drivers required for OpenCV and media streaming
# Note: libgl1 replaces the deprecated libgl1-mesa-glx for Debian Trixie architectures
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]