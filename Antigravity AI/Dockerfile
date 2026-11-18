FROM python:3.11-slim

WORKDIR /app

# Copy all project files
COPY . /app

# Expose port (default 5000, but Cloud Run passes PORT env)
EXPOSE 5000

ENV PORT=5000

CMD ["python3", "server.py"]
