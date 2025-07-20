# Use a lightweight Python base image
FROM python:3.10-slim

# Install system dependencies including Poppler
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy your project files into the image
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your app runs on
EXPOSE 8000

# Start the FastAPI app using Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
