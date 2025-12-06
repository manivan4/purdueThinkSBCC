# Use a small Python 3.11 image as the base
FROM python:3.11-slim

# Install system dependencies we need (Tesseract + Poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy only requirements first for better build caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your code
COPY . .

# Start the FastAPI app using uvicorn
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
