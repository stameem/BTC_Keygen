# Use Python as base image
FROM python:3.11-slim

# Install system dependencies for Pillow and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg-dev zlib1g-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir nicegui pillow qrcode requests reportlab bitcoin mysql-connector-python

# Set working directory
WORKDIR /app

# Copy your app code
COPY app.py /app/app.py

# Expose NiceGUI port
EXPOSE 8080

# Run the app
CMD ["python", "app.py"]
