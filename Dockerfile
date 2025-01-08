# Use the official Python image
FROM python:3.9

# Set the working directory in the container
WORKDIR /code

# Copy requirements.txt first to leverage Docker's cache
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application code
COPY ./app /code/app
COPY .env /code/.env

# Expose the port that FastAPI will run on
EXPOSE 80

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "192.168.1.99", "--port", "30002"]
