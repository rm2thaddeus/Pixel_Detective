# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set PYTHONPATH to include /app
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Copy the current directory contents into the container at /app
COPY . /app
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
# For now, just FastAPI, Uvicorn, and HTTPX. Qdrant client will be added later.
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8002 available to the world outside this container
EXPOSE 8002

# Run main.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"] 