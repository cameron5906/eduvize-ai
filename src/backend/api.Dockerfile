# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Update system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    python3-dev \
    poppler-utils

# Harden apt lists and remove unnecessary packages
RUN apt clean && apt autoremove -y && apt autoclean -y
RUN rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining files
COPY . .

ENV PORT=80

# Make port 80 available to the world outside this container
EXPOSE 80

USER 1000

# Run app.py when the container launches
CMD ["python", "run.py"]
