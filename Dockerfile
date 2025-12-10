# Start from the Python image (using Python 3.9)
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Update pip and install dependencies from chatbot_flask_requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r chatbot_flask_requirements.txt

# Expose the port that Flask will run on
EXPOSE 5000

# Run your Flask app
CMD ["python", "app.py"]
