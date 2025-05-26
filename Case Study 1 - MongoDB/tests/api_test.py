import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api/v1"

def create_table_in_db(table_number, capacity): # Renamed function and parameters
    payload = {
        'capacity': capacity,       # Changed from 'kapazitaet'
        'table_number': table_number # Changed from 'tischnummer'
    }
    response = requests.post(f'{BASE_URL}/tables', json=payload) # Changed endpoint from '/tische'
    assert response.status_code == 201, f"Failed to create table: {response.status_code} {response.text}"
    return response.json()['table_id'] # Changed response key from 'Primary Key in DB'

def add_reservation_to_db(table_number_for_reservation, number_of_people, reservation_date_str, reservation_time_str, last_name, first_name, phone_number): # Renamed function and parameters
    payload = {
        'tables': [{'table_number': table_number_for_reservation}], # Changed 'tische', 'tischnummer'
        'number_of_people': number_of_people,       # Changed from 'personenzahl'
        'reservation_date': reservation_date_str,   # Changed from 'reservierungsdatum'
        'reservation_time': reservation_time_str,   # Changed from 'reservierungsuhrzeit'
        'last_name': last_name,                   # Changed from 'nachname'
        'first_name': first_name,                 # Changed from 'vorname'
        'phone': phone_number                     # Changed from 'telefon'
    }
    response = requests.post(f'{BASE_URL}/reservations', json=payload) # Changed endpoint from '/reservierungen'
    assert response.status_code == 201, f"Failed to add reservation: {response.status_code} {response.text}"
    return response.json()['reservation_id'] # Changed response key from 'RID'

def test_create_table():
    table_num = "1" # Changed variable name
    cap = 4       # Changed variable name
    table_db_id = create_table_in_db(table_num, cap) # Adjusted to new function name and params
    assert table_db_id is not None


def test_add_reservations_for_next_7_days(): # Renamed function for clarity
    test_table_number = "T002" # Changed variable name
    table_capacity = 4       # Changed variable name
    # Create the table first, its DB ID is returned but not directly used by add_reservation_to_db, which needs table_number
    create_table_in_db(test_table_number, table_capacity)

    start_date_obj = datetime.now().date()
    for i in range(8): # Create 8 reservations, cycling through 7 days
        # reservation_date should be the string representation
        current_reservation_date_str = (start_date_obj + timedelta(days=i % 7)).strftime('%Y-%m-%d')
        current_reservation_time_str = '18:00'
        customer_last_name = f'CustomerLN_{i}' # Changed variable name and content
        customer_first_name = 'John'             # Changed variable name and content
        customer_phone = f'012345678{i}'       # Changed variable name

        reservation_db_id = add_reservation_to_db(
            test_table_number, # Pass the table number string
            4,
            current_reservation_date_str,
            current_reservation_time_str,
            customer_last_name,
            customer_first_name,
            customer_phone
        )
        assert reservation_db_id is not None


def test_display_occupancy_for_next_7_days(): # Renamed function for clarity
    response = requests.get(f'{BASE_URL}/occupancy_next_7_days') # Changed endpoint
    assert response.status_code == 200, f"Failed to get occupancy: {response.status_code} {response.text}"
    response_json = response.json()
    assert 'total_people' in response_json
    assert isinstance(response_json['total_people'], int)

# To run these tests, you would typically use a test runner like pytest.
# If you want to run them sequentially as a script:
if __name__ == "__main__":
    print("Running test_create_table...")
    test_create_table()
    print("test_create_table PASSED")

    print("\nRunning test_add_reservations_for_next_7_days...")
    # It might be good to ensure the DB is in a known state or clean up before this test if it's run multiple times
    # For simplicity, this test assumes it can create tables/reservations without conflicting with previous runs
    # or that the occupancy calculation will correctly sum up what's there.
    test_add_reservations_for_next_7_days()
    print("test_add_reservations_for_next_7_days PASSED")

    print("\nRunning test_display_occupancy_for_next_7_days...")
    test_display_occupancy_for_next_7_days()
    print("test_display_occupancy_for_next_7_days PASSED")

    print("\nAll tests executed.")