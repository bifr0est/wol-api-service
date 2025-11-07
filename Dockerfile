FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/bifroest/wol-api-service"
LABEL org.opencontainers.image.description="Wake-on-LAN API Service"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
