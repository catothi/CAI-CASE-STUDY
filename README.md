# CAI-CASE-STUDY1: Restaurant Reservation API (Postgres)

A simple Flask-based API for managing restaurant table reservations used during CAI lecture to demonstrate database systems.
Found in folder Case Study 1 - Postgres

## Prerequisites

Before you begin, ensure you have the following installed:
*   Python (3.7 or newer recommended)
*   pip (Python package installer)
*   PostgreSQL (running and accessible)
*   Git (optional, for cloning if this were a repository)

## Setup Instructions

1.  **Clone the Repository (if applicable)**
    If this project were in a Git repository, you would clone it:
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```
    Otherwise, ensure all project files (`app.py`, `test_app.py`, `truncate_db.py`, DDL SQL script, `.env` template) are in a single project directory.

2.  **Create a Virtual Environment (Recommended)**
    Navigate to your project's root directory in the terminal and run:
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    You should see `(venv)` at the beginning of your terminal prompt.

4.  **Install Dependencies**
    With the virtual environment activated, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up PostgreSQL Database**
    *   Ensure your PostgreSQL server is running.
    *   Connect to PostgreSQL (e.g., using `psql -U postgres`).
    *   Create the database that will be used by the application (e.g., `reservations_db`):
        ```sql
        CREATE DATABASE reservations_db;
        ```
    *   Ensure the PostgreSQL user specified in your `.env` file (e.g., `postgres`) has the necessary permissions on this database (typically, the `postgres` superuser will have them).

6.  **Create and Configure `.env` File**
    In the root of your project directory, create a file named `.env`. Copy the following content into it and **replace `your_actual_postgres_password` with your actual PostgreSQL password for the `postgres` user**:
    ```ini
    # .env
    DB_PASSWORD=your_actual_postgres_password
    DB_NAME=reservations_db
    DB_USER=postgres
    DB_HOST=localhost
    DB_PORT=5432
    ```

7.  **Run the Database Schema (DDL)**
    You have a DDL SQL script (the one we've been working with, let's assume it's named `schema.sql`) that creates the necessary tables (`tables`, `customers`, `reservations`). Run this script against your `reservations_db` database.
    Using `psql`:
    ```bash
    psql -U postgres -d reservations_db -f /path/to/your/schema.sql
    ```
    Replace `/path/to/your/schema.sql` with the actual path to your DDL script. You will be prompted for the password for the `postgres` user.

## Running the Application

1.  Make sure your virtual environment is activated.
2.  Navigate to the project directory.
3.  Run the Flask application:
    ```bash
    python app.py
    ```
    The application should start, typically on `http://127.0.0.1:5000/` or `http://localhost:5000/`. The API base URL will be `http://localhost:5000/api/v1`.

## Running Tests

1.  Make sure the Flask application is **running** in a separate terminal.
2.  Ensure your virtual environment is activated in a new terminal.
3.  Navigate to the project directory.
4.  Run pytest:
    ```bash
    pytest -v
    ```

## API Endpoints Overview

*   `POST /api/v1/tables`: Create a new restaurant table.
*   `POST /api/v1/reservations`: Add a new reservation.
*   `DELETE /api/v1/reservations/{rid}`: Cancel a reservation.
*   `PUT /api/v1/reservations/{rid}`: Modify an existing reservation.
*   `GET /api/v1/occupancy_next_7_days`: Display occupancy for the next 7 days.

Refer to the Postman collection for detailed request examples.

## Truncating Database Tables (for development/testing)

A script `truncate_db.py` is provided to clear all data from the tables and reset identity sequences.
**Use with caution, as this will delete all data in the specified tables.**

1.  Make sure your virtual environment is activated.
2.  Navigate to the project directory.
3.  Run the script:
    ```bash
    python truncate_db.py
    ```
