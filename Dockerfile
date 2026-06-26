# Step 1: Use the official AWS Lambda Python base image instead of slim-linux
FROM public.ecr.aws/lambda/python:3.12

# Step 2: Inject the official AWS Lambda Web Adapter binary
COPY --from=public.ecr.aws/awsguru/aws-lambda-web-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Step 3: Set system environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# AWS Lambda base images use /var/task as the default working directory
WORKDIR /var/task

# Step 4: Install system dependencies (needed for compilation/GIS tools if using Shapely)
# Note: Lambda base images use 'dnf' (Amazon Linux 2023) instead of 'apt-get'
RUN dnf update -y && dnf install -y \
    gcc \
    gcc-c++ \
    postgresql-devel \
    && dnf clean all

# Step 5: Copy only the requirements file first to leverage Docker's caching layer
COPY requirements.txt .

# Step 6: Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Copy the rest of your local application code into the container
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Step 8: Set the port environment variable that Lambda Web Adapter listens to
ENV PORT=8080
EXPOSE 8080

# Step 9: The command to run your app inside Lambda via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]