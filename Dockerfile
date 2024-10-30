ARG TARGET_NAME

# Use a base image with Python 3
FROM python:3.8-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install the required Python libraries
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Set the working directory
WORKDIR /

# Copy the Python script and config file into the container
COPY $TARGET_NAME/* /

# Set the environment variable for the script
ENV PYTHONUNBUFFERED=1

# Run the script when the container starts
CMD ["python3", "/$TARGET_NAME.py"]
