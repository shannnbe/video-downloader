FROM python:3.12-slim

# Install ffmpeg (required for video processing)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 botuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for temporary downloads
RUN mkdir -p /app/downloads && chown botuser:botuser /app/downloads

# Switch to non-root user
USER botuser

# Run the bot
CMD ["python", "bot.py"]
