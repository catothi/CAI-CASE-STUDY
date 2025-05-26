import pytest
import requests
from datetime import date, datetime, timedelta # Use datetime.date for date objects
import uuid
import os # For loading .env if needed by app.py or for test-specific DB connection

# Attempt to load .env if your app.py doesn't do it or if tests need direct DB access later
# from dotenv import load_dotenv
# dotenv_path = os.path.join(os.path.dirname(__file__), '../.env') # Adjust path if needed
# load_dotenv(dotenv_path=dotenv_path)


BASE_URL = 'http://localhost:5000/api/v1' # Ensure your Flask app runs on this port

# --- Module Setup/Teardown (User's API-based approach) ---
def setup_module(module):
    """
    Setup: Attempt to ensure a clean state by deleting test data via API.
    NOTE: This relies on GET /tables and GET /reservations (listing all)
          and DELETE /tables/{tid} and DELETE /reservations/{rid} endpoints
          being implemented and working correctly in your app.py.
          It also assumes specific JSON response structures.
    """
    print("\n--- Module Setup: Attempting API-based cleanup ---")

    # Clean up test reservations
    # This assumes GET /reservations returns a list under 'reservations',
    # and each reservation object has 'rid' and 'comment' or 'customer_details'
    try:
        response = requests.get(f'{BASE_URL}/reservations') # This endpoint might not exist in your app
        if response.status_code == 200:
            reservations_data = response.json()
            # Adjust the key if your API returns the list differently
            for res in reservations_data.get('reservations', []):
                # Example: Identify test reservations by a specific comment or customer name pattern
                is_test_reservation = False
                if 'TestReservation' in res.get('comment', ''):
                    is_test_reservation = True
                # If customer details are nested, you'd need to access them.
                # For example, if res has {'customer': {'last_name': 'TestLastName'}}
                # if 'customer' in res and 'TestLastName' in res['customer'].get('last_name', ''):
                #    is_test_reservation = True

                if is_test_reservation and 'rid' in res:
                    print(f"Setup: Deleting test reservation RID: {res['rid']}")
                    del_response = requests.delete(f"{BASE_URL}/reservations/{res['rid']}")
                    if del_response.status_code != 200 and del_response.status_code != 204:
                        print(f"Warning: Failed to delete reservation {res['rid']} during setup: {del_response.status_code}")
        elif response.status_code != 404: # 404 is okay if endpoint doesn't exist
             print(f"Warning: Could not get reservations for cleanup: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Warning: API request failed during reservation cleanup: {str(e)}")
    except KeyError:
        print("Warning: Unexpected JSON structure from GET /reservations during cleanup.")


    # Clean up test tables
    # This assumes GET /tables returns a list under 'tables',
    # and each table object has 'tid' and 'table_number'.
    # It also assumes DELETE /tables/{tid} exists.
    try:
        response = requests.get(f'{BASE_URL}/tables') # This endpoint might not exist in your app
        if response.status_code == 200:
            tables_data = response.json()
            # Adjust the key if your API returns the list differently
            for table in tables_data.get('tables', []):
                if table.get('table_number', '').startswith('TestTable-') and 'tid' in table:
                    print(f"Setup: Deleting test table TID: {table['tid']}")
                    # NOTE: Your app.py did not have a DELETE /tables/{tid} endpoint.
                    # This part will fail if that endpoint is not implemented.
                    del_response = requests.delete(f"{BASE_URL}/tables/{table['tid']}")
                    if del_response.status_code != 200 and del_response.status_code != 204:
                         print(f"Warning: Failed to delete table {table['tid']} during setup: {del_response.status_code}")
        elif response.status_code != 404:
             print(f"Warning: Could not get tables for cleanup: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Warning: API request failed during table cleanup: {str(e)}")
    except KeyError:
        print("Warning: Unexpected JSON structure from GET /tables during cleanup.")

def teardown_module(module):
    """Teardown: Additional cleanup if needed (e.g., reversing setup actions)"""
    print("\n--- Module Teardown ---")
    # If setup created global resources, teardown could clean them.
    # For this test structure, most cleanup is aimed for in setup_module or per-test.

# --- Helper Functions ---
def create_table_api(capacity, table_number_prefix="TestTable-"):
    """Helper to create a table with a unique number via API."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        'capacity': capacity,
        'table_number': f"{table_number_prefix}{unique_suffix}"
    }
    response = requests.post(f'{BASE_URL}/tables', json=payload)
    if response.status_code != 201:
        pytest.fail(
            f"Failed to create table: {response.status_code} - {response.text}\n"
            f"Payload: {payload}"
        )
    # Assuming the response JSON directly contains 'tid'
    return response.json()['tid']

def add_reservation_api(tid, num_people, res_date_str, res_time_str,
                        last_name_prefix="TestCustLast-", first_name="TestFirst",
                        phone_prefix="099", comment=None):
    """Helper to add a reservation via API with unique elements."""
    unique_suffix = uuid.uuid4().hex[:6]
    payload = {
        'tid': tid,
        'number_of_people': num_people,
        'reservation_date': res_date_str,  # Expects 'YYYY-MM-DD'
        'reservation_time': res_time_str,  # Expects 'HH:MM:SS'
        'last_name': f"{last_name_prefix}{unique_suffix}",
        'first_name': first_name,
        # Generate a somewhat unique phone number to avoid conflicts on customer creation
        'phone': f"{phone_prefix}{str(uuid.uuid4().int)[:7]}"[-10:] # Last 10 digits of a number
    }
    if comment:
        payload['comment'] = comment

    response = requests.post(f'{BASE_URL}/reservations', json=payload)
    if response.status_code != 201:
        pytest.fail(
            f"Failed to add reservation: {response.status_code} - {response.text}\n"
            f"Payload: {payload}"
        )
    # Assuming the response JSON directly contains 'rid' and other details
    return response.json()


# --- Test Cases ---
def test_create_table():
    """Test creating multiple tables with unique numbers."""
    print("\nRunning test_create_table")
    created_tids = []
    for i in range(3): # Create 3 tables
        try:
            tid = create_table_api(capacity=2 + i)
            assert isinstance(tid, int), "Table ID should be an integer."
            created_tids.append(tid)
            print(f"Created table TID: {tid} with table_number containing 'TestTable-'")
        except Exception as e: # Catch assertion failures from helper
            pytest.fail(f"Error during table creation in loop: {str(e)}")
    assert len(created_tids) == 3, "Should have created 3 tables."

def test_add_reservations_next_7_days():
    """Test adding reservations for the next 7 days for a new table."""
    print("\nRunning test_add_reservations_next_7_days")
    try:
        tid_for_reservations = create_table_api(capacity=4)
        print(f"Created table TID for 7-day reservations: {tid_for_reservations}")
    except Exception as e:
        pytest.fail(f"Failed to create table for 7-day reservation test: {str(e)}")
        return # Stop test if table creation fails

    # Use datetime.date for date calculations, then format to string for API
    today_date = date.today()
    created_rids = []

    for i in range(7):
        res_date_obj = today_date + timedelta(days=i)
        res_date_str = res_date_obj.strftime('%Y-%m-%d')
        try:
            reservation_details = add_reservation_api(
                tid=tid_for_reservations,
                num_people=2,
                res_date_str=res_date_str,
                res_time_str='18:00:00',
                comment=f"TestReservation for day {i+1}"
            )
            assert 'rid' in reservation_details, f"Reservation creation failed for day {i+1}, RID missing."
            created_rids.append(reservation_details['rid'])
            print(f"Added reservation RID: {reservation_details['rid']} for date: {res_date_str}")
        except Exception as e:
            pytest.fail(f"Error adding reservation for day {i+1} ({res_date_str}): {str(e)}")

    assert len(created_rids) == 7, "Should have created 7 reservations."

def test_modify_reservation():
    """Test modifying an existing reservation (e.g., time and comment)."""
    print("\nRunning test_modify_reservation")
    try:
        initial_tid = create_table_api(capacity=4, table_number_prefix="ModInitialTestTable-")
        new_tid_for_update = create_table_api(capacity=2, table_number_prefix="ModNewTestTable-")
        print(f"Created tables for modify test: InitialTID={initial_tid}, NewTID={new_tid_for_update}")
    except Exception as e:
        pytest.fail(f"Failed to create tables for modify reservation test: {str(e)}")
        return

    res_date_obj = date.today() + timedelta(days=2)
    res_date_str = res_date_obj.strftime('%Y-%m-%d')
    initial_time_str = '19:30:00'
    updated_time_str = '20:15:00' # Different from original

    try:
        initial_reservation = add_reservation_api(
            tid=initial_tid,
            num_people=3,
            res_date_str=res_date_str,
            res_time_str=initial_time_str,
            comment="TestReservation: Initial booking for modify test"
        )
        initial_rid = initial_reservation['rid']
        print(f"Created initial reservation RID: {initial_rid} for date {res_date_str} at {initial_time_str}")
    except Exception as e:
        pytest.fail(f"Failed to add initial reservation for modify test: {str(e)}")
        return

    update_payload = {
        'tid': new_tid_for_update, # Change the table
        'number_of_people': 2,     # Change number of people
        'reservation_time': updated_time_str,
        'comment': 'TestReservation: Updated booking details'
    }
    response = requests.put(f'{BASE_URL}/reservations/{initial_rid}', json=update_payload)

    assert response.status_code == 200, \
        f"Failed to modify reservation: {response.status_code} - {response.text}\nPayload: {update_payload}"

    modified_res_data = response.json()
    assert 'reservation' in modified_res_data, "Response JSON should contain 'reservation' details."
    updated_details = modified_res_data['reservation']

    print(f"Modified reservation details: {updated_details}")

    # The CustomJSONProvider in app.py should ensure reservation_time is a string
    assert updated_details.get('reservation_time') == updated_time_str, \
        f"Reservation time was not updated correctly. Expected {updated_time_str}, Got {updated_details.get('reservation_time')}"
    assert updated_details.get('comment') == 'TestReservation: Updated booking details', "Comment not updated."
    assert updated_details.get('tid') == new_tid_for_update, "Table ID (tid) not updated."
    assert updated_details.get('number_of_people') == 2, "Number of people not updated."

def test_cancel_reservation():
    """Test canceling an existing reservation."""
    print("\nRunning test_cancel_reservation")
    try:
        tid_for_cancel = create_table_api(capacity=2, table_number_prefix="CancelTestTable-")
        print(f"Created table TID for cancel test: {tid_for_cancel}")
    except Exception as e:
        pytest.fail(f"Failed to create table for cancel test: {str(e)}")
        return

    res_date_obj = date.today() + timedelta(days=3)
    res_date_str = res_date_obj.strftime('%Y-%m-%d')

    try:
        reservation_to_cancel = add_reservation_api(
            tid=tid_for_cancel,
            num_people=2,
            res_date_str=res_date_str,
            res_time_str='10:00:00',
            comment="TestReservation: To be cancelled"
        )
        rid_to_cancel = reservation_to_cancel['rid']
        print(f"Added reservation RID to cancel: {rid_to_cancel}")
    except Exception as e:
        pytest.fail(f"Failed to add reservation for cancel test: {str(e)}")
        return

    response = requests.delete(f'{BASE_URL}/reservations/{rid_to_cancel}')
    assert response.status_code == 200, \
        f"Failed to cancel reservation: {response.status_code} - {response.text}"
    assert response.json().get('message') == f'Reservation {rid_to_cancel} cancelled successfully'

    # Optionally, verify it's truly gone (e.g., try to GET it and expect 404)
    # get_response = requests.get(f'{BASE_URL}/reservations/{rid_to_cancel}')
    # assert get_response.status_code == 404, "Cancelled reservation should not be found (404)."

def test_display_occupancy_next_7_days():
    """Test displaying occupancy for the next 7 days."""
    print("\nRunning test_display_occupancy_next_7_days")

    # Add some reservations to ensure there's data
    try:
        tid_occupancy = create_table_api(capacity=10, table_number_prefix="OccupancyTestTable-")
        print(f"Created table TID for occupancy test: {tid_occupancy}")

        today_date = date.today()
        # Add a reservation for today and one for 2 days from now
        add_reservation_api(tid_occupancy, 3, today_date.strftime('%Y-%m-%d'), '12:00:00', comment="TestReservation Occupancy Today")
        add_reservation_api(tid_occupancy, 5, (today_date + timedelta(days=2)).strftime('%Y-%m-%d'), '13:00:00', comment="TestReservation Occupancy D+2")
        print("Added reservations for occupancy test.")
    except Exception as e:
        pytest.fail(f"Setup for occupancy test failed: {str(e)}")
        return

    response = requests.get(f'{BASE_URL}/occupancy_next_7_days')
    assert response.status_code == 200, \
        f"Failed to get occupancy: {response.status_code} - {response.text}"

    data = response.json()
    assert 'occupancy_by_day' in data, "Response should contain 'occupancy_by_day'."
    occupancy = data['occupancy_by_day']
    assert len(occupancy) == 7, "Occupancy data should cover 7 days."

    print(f"Occupancy data: {occupancy}")
    # Check if today's date (as string key) exists and has expected people
    # Note: The CustomJSONProvider in app.py handles formatting of date keys in the response.
    today_str = date.today().isoformat() # Key in JSON should be ISO format string
    day_plus_2_str = (date.today() + timedelta(days=2)).isoformat()

    assert occupancy.get(today_str, 0) >= 3, f"Expected at least 3 people for today ({today_str}). Found {occupancy.get(today_str)}"
    assert occupancy.get(day_plus_2_str, 0) >= 5, f"Expected at least 5 people for {day_plus_2_str}. Found {occupancy.get(day_plus_2_str)}"

    # Check that all keys are valid date strings and values are integers
    for day_str, count in occupancy.items():
        try:
            datetime.strptime(day_str, '%Y-%m-%d') # Check if key is a valid date string
        except ValueError:
            pytest.fail(f"Occupancy key '{day_str}' is not a valid YYYY-MM-DD date string.")
        assert isinstance(count, int), f"Occupancy count for '{day_str}' should be an integer, got {type(count)}."
