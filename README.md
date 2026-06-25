# ewast-backend

This repository included the code for the backend service used by EWAST, our entry for the AWS Innovation Cup - Mindanao 2026 hackathon.

## How to setup database

You need to modify your DATABASE_URL environment variable to match the format of the examples in `.env.template`

If you do not have an `.env` file yet, create one and copy and fill up the contents from `.env.template`.

If your PostgreSQL server does not have the `ewast_db` database yet, please refer the sqldump file in the Discord server.

The details for the values of the `.env` file variables are also in the Discord server. 

## How to run locally

Before proceeding, it is recommended to first create a virtual environment using the `venv` Python module.

- Install the required packages via `pip install -r requirements`
- Start the backend locally using `uvicorn app.main:app --reload`

## Handling database migrations

If you are using an external databse and have made modifications to the data schemas of this project, specifically the ones to be stored in the database (inherits `SQLModel` and has `table=True`), here's how to handle the migrations:

- Make sure that the schema class is imported along with the other classes in `alembic/env.py`
- Generate a new migration script using the command `alembic revision --autogenerate -m "your message"`
- Run the migration with `alembic upgrade head`

## Data attribution

- **Davao City Barangay Boundaries** - © Christian Blanquera, geoph. Source: https://github.com/OSSPhilippines/geoph