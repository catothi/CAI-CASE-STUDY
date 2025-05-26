from flask import Flask, request, jsonify, make_response
import psycopg2
from psycopg2 import sql, IntegrityError, extras
import os
from dotenv import load_dotenv  # Import load_dotenv
from datetime import datetime, timedelta

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Database connection
def get_db_connection():
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')

    if not all([db_name, db_user, db_password, db_host, db_port]):
        missing_vars = [var for var, val in {
            "DB_NAME": db_name, "DB_USER": db_user, "DB_PASSWORD": db_password,
            "DB_HOST": db_host, "DB_PORT": db_port
        }.items() if not val]
        raise ValueError(f"Missing database configuration in .env or environment: {', '.join(missing_vars)}")

    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    return conn

@app.errorhandler(400)
def bad_request_error(error):
    return make_response(jsonify({"message": "Bad Request", "details": str(error.description if hasattr(error, 'description') else error)}), 400)

@app.errorhandler(404)
def not_found_error(error):
    return make_response(jsonify({"message": "Not Found", "details": str(error.description if hasattr(error, 'description') else error)}), 404)

@app.errorhandler(409)
def conflict_error(error):
    return make_response(jsonify({"message": "Conflict", "details": str(error.description if hasattr(error, 'description') else error)}), 409)

# User Story 1: Create tables (Restaurant Tables)
@app.route('/api/v1/tables', methods=['POST'])
def create_restaurant_table():
    data = request.json
    if not data or 'capacity' not in data or 'table_number' not in data:
        return bad_request_error("'capacity' and 'table_number' are required fields")

    capacity_val = data['capacity']
    table_number_str = data['table_number']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tables (capacity, table_number) VALUES (%s, %s) RETURNING tid",
            (capacity_val, table_number_str))
        table_id = cursor.fetchone()[0]  # This is tid
        conn.commit()
    except IntegrityError as e:
        if conn: conn.rollback()
        if "tables_table_number_key" in str(e).lower():
             return conflict_error(f"Table with number '{table_number_str}' already exists.")
        return conflict_error(f"Database integrity error: {e}")
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error creating table: {e}", exc_info=True)  # Log the full error
        return bad_request_error(f"Error creating table: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return jsonify({'tid': table_id, 'message': 'Table created successfully'}), 201

# User Story 2: Add new reservation
@app.route('/api/v1/reservations', methods=['POST'])
def add_reservation():
    data = request.json
    required_fields = ['tid', 'number_of_people', 'reservation_date', 'reservation_time', 'last_name', 'first_name', 'phone']
    if not all(field in data for field in required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        return bad_request_error(f"Missing required fields: {', '.join(missing_fields)}")

    table_id_val = data['tid']
    num_people = data['number_of_people']
    res_date = data['reservation_date']
    res_time = data['reservation_time']
    last_name_str = data['last_name']
    first_name_str = data['first_name']
    phone_str = data['phone']
    comment_str = data.get('comment', '')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("SELECT tid FROM tables WHERE tid = %s", (table_id_val,))
        if cursor.fetchone() is None:
            return bad_request_error(f"Table with TID {table_id_val} does not exist.")

        cursor.execute("SELECT cid FROM customers WHERE phone = %s", (phone_str,))  # Use phone as unique customer identifier for lookup
        customer_row = cursor.fetchone()

        if customer_row:
            customer_id_val = customer_row[0]  # This is cid
        else:
            cursor.execute(
                "INSERT INTO customers (last_name, first_name, phone) VALUES (%s, %s, %s) RETURNING cid",
                (last_name_str, first_name_str, phone_str)
            )
            customer_id_val = cursor.fetchone()[0]  # This is cid

        cursor.execute(
            """
            INSERT INTO reservations (tid, cid, status, comment, number_of_people, reservation_date, reservation_time)
            VALUES (%s, %s, 'active', %s, %s, %s, %s) RETURNING rid
            """,
            (table_id_val, customer_id_val, comment_str, num_people, res_date, res_time)
        )
        reservation_id_val = cursor.fetchone()[0]  # This is rid
        conn.commit()
    except IntegrityError as e:
        if conn: conn.rollback()
        if "customers_phone_key" in str(e).lower():
            return conflict_error(f"Customer with phone number '{phone_str}' already exists with different details or a general conflict occurred.")
        app.logger.error(f"Database integrity error: {e}", exc_info=True)
        return conflict_error(f"Database integrity error: {e}")
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error adding reservation: {e}", exc_info=True)
        return bad_request_error(f"Error adding reservation: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    response_data = {
        'rid': reservation_id_val,
        'cid': customer_id_val,
        'tid': table_id_val,
        'reservation_date': res_date,
        'reservation_time': res_time,
        'number_of_people': num_people,
        'message': 'Reservation created successfully'
    }
    return jsonify(response_data), 201

# User Story 3: Cancel reservation
@app.route('/api/v1/reservations/<int:rid>', methods=['DELETE'])
def cancel_reservation(rid):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reservations WHERE rid = %s", (rid,))
        if cursor.rowcount == 0:
            conn.rollback()
            return not_found_error(f"Reservation with RID {rid} not found or already cancelled.")
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error cancelling reservation: {e}", exc_info=True)
        return bad_request_error(f"Error cancelling reservation: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return jsonify({'message': f'Reservation {rid} cancelled successfully'}), 200

# User Story 4: Modify reservation (Fixed with manual serialization)
@app.route('/api/v1/reservations/<int:rid>', methods=['PUT'])
def modify_reservation(rid):
    data = request.json
    allowed_fields_to_update = {'tid', 'status', 'comment', 'number_of_people', 'reservation_date', 'reservation_time'}
    
    if not data or not any(field in data for field in allowed_fields_to_update):
        return bad_request_error(f"At least one of the following fields is required for update: {', '.join(allowed_fields_to_update)}")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        cursor.execute("SELECT * FROM reservations WHERE rid = %s", (rid,))
        current_reservation = cursor.fetchone()
        if not current_reservation:
            return not_found_error(f"Reservation with RID {rid} not found.")

        update_fields_sql_parts = []
        update_values = []

        for field_key in allowed_fields_to_update:
            if field_key in data:
                update_fields_sql_parts.append(sql.SQL("{} = %s").format(sql.Identifier(field_key)))
                update_values.append(data[field_key])
        
        if not update_fields_sql_parts:
            return bad_request_error("No valid fields provided for update.")

        query = sql.SQL("UPDATE reservations SET {} WHERE rid = %s RETURNING *").format(
            sql.SQL(', ').join(update_fields_sql_parts)
        )
        update_values.append(rid)

        cursor.execute(query, tuple(update_values))
        updated_res = cursor.fetchone()

        if not updated_res:
            conn.rollback()
            return jsonify({'message': f'Reservation {rid} not modified'}), 400
        
        conn.commit()
    except IntegrityError as e:
        if conn: conn.rollback()
        app.logger.error(f"Integrity error: {e}", exc_info=True)
        return conflict_error(f"Database error: {e}. Check if table exists.")
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error modifying reservation: {e}", exc_info=True)
        return bad_request_error(f"Error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # Manually convert non-serializable objects to strings
    response_data = {
        'rid': updated_res['rid'],
        'tid': updated_res['tid'],
        'cid': updated_res['cid'],
        'status': updated_res['status'],
        'comment': updated_res['comment'],
        'number_of_people': updated_res['number_of_people'],
        'reservation_date': str(updated_res['reservation_date']) if updated_res['reservation_date'] else None,
        'reservation_time': str(updated_res['reservation_time']) if updated_res['reservation_time'] else None,
        'created_at': str(updated_res['created_at']) if updated_res['created_at'] else None,
        'updated_at': str(updated_res['updated_at']) if updated_res['updated_at'] else None
    }
    
    return jsonify({
        'message': f'Reservation {rid} modified successfully',
        'reservation': response_data
    }), 200

# User Story 5: Display occupancy for the next 7 days
@app.route('/api/v1/occupancy_next_7_days', methods=['GET'])
def get_occupancy_next_7_days():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT
                reservation_date,
                COALESCE(SUM(number_of_people), 0) AS people_on_day
            FROM
                reservations
            WHERE
                status = 'active'
                AND reservation_date BETWEEN CURRENT_DATE AND CURRENT_DATE + interval '6 days'
            GROUP BY reservation_date
            ORDER BY reservation_date;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        occupancy_data = {}
        today = datetime.date(datetime.now())
        for i in range(7):
            current_date = today + timedelta(days=i)
            occupancy_data[current_date.strftime('%Y-%m-%d')] = 0

        for row in results:
            occupancy_data[row[0].strftime('%Y-%m-%d')] = row[1]

    except Exception as e:
        app.logger.error(f"Error fetching occupancy: {e}", exc_info=True)
        return bad_request_error(f"Error fetching occupancy: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return jsonify({'occupancy_by_day': occupancy_data}), 200

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Starting Flask application...")
    app.run(debug=True)