# Step 1: Use an official lightweight Python runtime as a parent image
FROM python:3.12-slim

# Step 2: Set system environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Step 3: Set the working directory inside the container
WORKDIR /app

# Step 4: Install system dependencies (needed for compilation/GIS tools if using Shapely)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 5: Copy only the requirements file first to leverage Docker's caching layer
COPY requirements.txt /app/

# Step 6: Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Copy the rest of your local application code into the container
COPY . /app/

# Step 8: Expose the port your FastAPI app runs on (Fargate reads this)
EXPOSE 8000

# Step 9: The command to run your app inside the Fargate task container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
