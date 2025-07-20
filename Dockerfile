# Use a lightweight Python base image
FROM python:3.10-slim

# Install system dependencies including Poppler
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your project files into the image
COPY . .

# Set default port
ENV PORT=8000

# Expose the port your app runs on
EXPOSE $PORT


# Start the FastAPI app using Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
