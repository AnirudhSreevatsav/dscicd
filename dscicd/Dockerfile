# Use the official Python image from the Docker Hub
FROM python:3.12.5-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to the working directory
COPY . /app/


# Expose the port Flask runs on
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
