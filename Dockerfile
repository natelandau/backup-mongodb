# Use the official Python base image
FROM python:3.11

# Install MongoDB Tools
RUN apt-get update && apt-get install -y wget gnupg software-properties-common
RUN wget -qO mongodb-database-tools.deb https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-x86_64-100.9.0.deb
RUN dpkg -i mongodb-database-tools.deb && apt-get install -f
RUN rm mongodb-database-tools.deb

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Poetry
RUN pip install poetry

# Install dependencies and script
RUN poetry install --without dev,test

# Set the entrypoint to run the script
CMD ["poetry", "run", "backup-mongodb"]
