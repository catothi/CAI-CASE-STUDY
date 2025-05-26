from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
# from bson.son import SON # SON was imported but not used, removed

app = Flask(__name__)

# Database connection
def get_db_connection():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['reservation_db'] # Changed from 'reservierung_db'
    return db

# Error handler for 400 Bad Request
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({"message": "Bad Request", "details": str(error)}), 400)

# Error handler for 409 Conflict
@app.errorhandler(409)
def conflict(error):
    return make_response(jsonify({"message": "Conflict", "details": str(error)}), 409)

# User Story 1: Create tables
@app.route('/api/v1/tables', methods=['POST']) # Changed endpoint from '/api/v1/tische'
def create_table():
    data = request.json

    if not data or 'capacity' not in data or 'table_number' not in data: # Changed fields from 'kapazitaet', 'tischnummer'
        return bad_request("capacity and table_number are required fields") # Changed message

    capacity = data['capacity'] # Changed from 'kapazitaet'
    table_number = data['table_number'] # Changed from 'tischnummer'

    db = get_db_connection()
    tables_collection = db.tables # Changed collection name from 'tische'

    if tables_collection.find_one({"table_number": table_number}): # Changed field from 'tischnummer'
        return conflict("This table already exists") # Changed message

    table_id = tables_collection.insert_one({
        "capacity": capacity,         # Changed from 'kapazitaet'
        "table_number": table_number  # Changed from 'tischnummer'
    }).inserted_id

    return jsonify({'table_id': str(table_id)}), 201 # Changed response key

# User Story 2: Add new reservation
@app.route('/api/v1/reservations', methods=['POST']) # Changed endpoint from '/api/v1/reservierungen'
def add_reservation():
    data = request.json

    required_fields = [
        'tables',             # Changed from 'tische'
        'number_of_people',   # Changed from 'personenzahl'
        'reservation_date',   # Changed from 'reservierungsdatum'
        'reservation_time',   # Changed from 'reservierungsuhrzeit'
        'last_name',          # Changed from 'nachname'
        'first_name',         # Changed from 'vorname'
        'phone'               # Changed from 'telefon'
    ]

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return bad_request(f"Required fields are missing: {', '.join(missing_fields)}")

    tables_input_list = data['tables'] # Changed from 'tische' (for the list itself)
    comment_text = data.get('comment', '') # Changed from 'kommentar'
    num_people = data['number_of_people'] # Changed from 'personenzahl'
    reservation_date_str = data['reservation_date'] # Changed from 'reservierungsdatum'
    reservation_time_str = data['reservation_time'] # Changed from 'reservierungsuhrzeit'

    customer_details = { # Changed variable name from 'kunde'
        "last_name": data['last_name'],   # Changed from 'nachname'
        "first_name": data['first_name'], # Changed from 'vorname'
        "phone": data['phone']            # Changed from 'telefon'
    }

    db = get_db_connection()
    tables_db_collection = db.tables # Changed variable name and collection from 'tische_col', 'db.tische'

    processed_tables_for_reservation = []
    if not isinstance(tables_input_list, list):
        return bad_request("'tables' field must be a list of table objects.")
        
    for table_spec_from_input in tables_input_list:
        if not isinstance(table_spec_from_input, dict):
            return bad_request("Each item in 'tables' list must be an object.")
        table_number_from_input = table_spec_from_input.get('table_number') # Changed from 'tischnummer'
        
        if not table_number_from_input:
            return bad_request("Each table object in the 'tables' list must have a 'table_number' field.")

        table_document = tables_db_collection.find_one({"table_number": table_number_from_input}) # Changed field from 'tischnummer'
        if not table_document:
            return bad_request(f"Table with number {table_number_from_input} does not exist") # Changed message
        
        processed_tables_for_reservation.append({
            "table_number": table_number_from_input # Changed field from 'tischnummer'
        })

    reservation_document = {
        "status": "active",
        "comment": comment_text,                   # Changed from 'kommentar'
        "number_of_people": num_people,            # Changed from 'personenzahl'
        "reservation_date": reservation_date_str,  # Changed from 'reservierungsdatum'
        "reservation_time": reservation_time_str,  # Changed from 'reservierungsuhrzeit'
        "customer": customer_details,              # Changed from 'kunde'
        "tables": processed_tables_for_reservation # Changed from 'tische' (for the list within the reservation)
    }

    reservations_collection = db.reservations # Changed collection name from 'reservierungen'
    reservation_id_obj = reservations_collection.insert_one(reservation_document).inserted_id

    response_data = {
        'reservation_id': str(reservation_id_obj), # Changed key from 'RID'
        'reservation_time': reservation_time_str   # Changed field from 'reservierungsuhrzeit'
    }

    return jsonify(response_data), 201

# User Story 5: Display occupancy for the next 7 days
@app.route('/api/v1/occupancy_next_7_days', methods=['GET']) # Changed endpoint from '/api/v1/auslastung_7_tage'
def get_occupancy_next_7_days(): # Changed function name from 'auslastung_7_tage'
    db = get_db_connection()
    reservations_collection = db.reservations # Changed collection name from 'reservierungen'

    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=7) 

    pipeline = [
        {
            '$match': {
                'status': 'active',
                '$expr': {
                    '$and': [
                        {
                            '$gte': [
                                {'$dateFromString': {'dateString': '$reservation_date', 'format': '%Y-%m-%d'}}, # Changed field from '$reservierungsdatum'
                                start_date  # Direct use of start_date (comment translated)
                            ]
                        },
                        {
                            '$lte': [
                                {'$dateFromString': {'dateString': '$reservation_date', 'format': '%Y-%m-%d'}}, # Changed field from '$reservierungsdatum'
                                end_date  # Direct use of end_date (comment translated)
                            ]
                        }
                    ]
                }
            }
        },
        {
            '$group': {
                '_id': None,
                'total_people': {'$sum': '$number_of_people'} # Changed field from '$personenzahl'
            }
        }
    ]

    aggregation_result = list(reservations_collection.aggregate(pipeline))
    # print(result[0]) # Original print statement, commented out
    total_people_count = aggregation_result[0]['total_people'] if aggregation_result else 0

    return jsonify({'total_people': total_people_count}), 200

if __name__ == '__main__':
    app.run(debug=True)