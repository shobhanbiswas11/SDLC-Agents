# Use the official Python image from the Alpine variant
FROM python:3.12-alpine AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install dependencies
FROM base AS builder
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copy the requirements file and install dependencies
COPY sample-flask-app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the application code
FROM base AS final
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY sample-flask-app /app

# Expose the port the app runs on
EXPOSE 5000

# Set the entry point for the container
CMD ["flask", "run", "--host=0.0.0.0"]