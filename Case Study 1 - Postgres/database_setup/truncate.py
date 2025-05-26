import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv # <<< HIER

# --- Explicitly load .env from one directory up ---
# Get the directory of the current script
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file in the parent directory
dotenv_path = os.path.join(current_script_dir, '..', '.env')
# Load the .env file from the specified path
load_dotenv(dotenv_path=dotenv_path)
# --- End of explicit loading ---

# Database connection information
DATABASE_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def check_db_config():
    missing = [k for k, v in DATABASE_CONFIG.items() if not v]
    if missing:
        print(f"Error: Missing database configuration values in .env or environment: {', '.join(missing)}")
        print("Please ensure DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT are set in your .env file.")
        return False
    return True

def truncate_all_tables():
    if not check_db_config():
        return

    conn = None
    cursor = None
    # Order for TRUNCATE ... CASCADE doesn't strictly matter for listed tables,
    # but good to be mindful if there were more complex, non-cascading dependencies.
    tables_to_truncate = ['reservations', 'customers', 'tables']

    try:
        print(f"Connecting to database: {DATABASE_CONFIG['dbname']} on {DATABASE_CONFIG['host']}...")
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # Build the TRUNCATE SQL command dynamically
        # Using sql.SQL and sql.Identifier for safe SQL construction
        truncate_query = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE;").format(
            sql.SQL(', ').join(map(sql.Identifier, tables_to_truncate))
        )
        
        print(f"Executing: {truncate_query.as_string(conn)} on database {DATABASE_CONFIG['dbname']}")
        cursor.execute(truncate_query)
        conn.commit()
        print(f"Tables ({', '.join(tables_to_truncate)}) successfully cleared and identities restarted.")

    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}")
        print("Please check your database server and connection settings in .env.")
    except psycopg2.Error as e: # Catch other psycopg2 specific errors
        print(f"Database error during truncation: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"General error clearing tables: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    print("Attempting to truncate all tables...")
    truncate_all_tables()