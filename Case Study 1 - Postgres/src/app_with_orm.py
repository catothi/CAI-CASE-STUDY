from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy.sql import func

load_dotenv()

app = Flask(__name__)

# Database setup
db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Models
class Table(Base):
    __tablename__ = 'tables'
    tid = Column(Integer, primary_key=True)
    table_number = Column(String(255), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)

class Customer(Base):
    __tablename__ = 'customers'
    cid = Column(Integer, primary_key=True)
    last_name = Column(String(255), nullable=False)
    first_name = Column(String(255))
    phone = Column(String(50), unique=True, nullable=False)

class Reservation(Base):
    __tablename__ = 'reservations'
    rid = Column(Integer, primary_key=True)
    tid = Column(Integer, nullable=False)
    cid = Column(Integer, nullable=False)
    status = Column(String(50), default='active', nullable=False)
    comment = Column(Text)
    number_of_people = Column(Integer, nullable=False)
    reservation_date = Column(Date, nullable=False)
    reservation_time = Column(String(8), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

# User Story 1: Create table
@app.route('/api/v1/tables', methods=['POST'])
def create_restaurant_table():
    data = request.json
    if not data or 'capacity' not in data or 'table_number' not in data:
        return jsonify({"message": "Missing required fields"}), 400

    session = Session()
    try:
        new_table = Table(capacity=data['capacity'], table_number=data['table_number'])
        session.add(new_table)
        session.flush()
        table_id = new_table.tid
        session.commit()
        return jsonify({'tid': table_id, 'message': 'Table created successfully'}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"message": str(e)}), 400
    finally:
        session.close()

# User Story 2: Add new reservation
@app.route('/api/v1/reservations', methods=['POST'])
def add_reservation():
    data = request.json
    required = ['tid', 'number_of_people', 'reservation_date', 'reservation_time', 'last_name', 'first_name', 'phone']
    if not all(field in data for field in required):
        return jsonify({"message": "Missing required fields"}), 400

    session = Session()
    try:
        table = session.query(Table).filter_by(tid=data['tid']).first()
        if not table:
            return jsonify({"message": f"Table {data['tid']} not found"}), 400

        customer = session.query(Customer).filter_by(phone=data['phone']).first()
        if not customer:
            customer = Customer(last_name=data['last_name'], first_name=data['first_name'], phone=data['phone'])
            session.add(customer)
            session.flush()

        reservation = Reservation(
            tid=data['tid'], cid=customer.cid, status='active',
            comment=data.get('comment', ''), number_of_people=data['number_of_people'],
            reservation_date=data['reservation_date'], reservation_time=data['reservation_time']
        )
        session.add(reservation)
        session.flush()
        reservation_id = reservation.rid
        session.commit()
        return jsonify({
            'rid': reservation_id, 'cid': customer.cid, 'tid': data['tid'],
            'reservation_date': data['reservation_date'], 'reservation_time': data['reservation_time'],
            'number_of_people': data['number_of_people'], 'message': 'Reservation created successfully'
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({"message": str(e)}), 400
    finally:
        session.close()

# User Story 3: Cancel reservation
@app.route('/api/v1/reservations/<int:rid>', methods=['DELETE'])
def cancel_reservation(rid):
    session = Session()
    try:
        reservation = session.query(Reservation).filter_by(rid=rid).first()
        if not reservation:
            return jsonify({"message": f"Reservation {rid} not found"}), 404
        session.delete(reservation)
        session.commit()
        return jsonify({'message': f'Reservation {rid} cancelled successfully'}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"message": str(e)}), 400
    finally:
        session.close()

# User Story 4: Modify reservation
@app.route('/api/v1/reservations/<int:rid>', methods=['PUT'])
def modify_reservation(rid):
    data = request.json
    allowed_fields = {'tid', 'status', 'comment', 'number_of_people', 'reservation_date', 'reservation_time'}
    if not data or not any(field in data for field in allowed_fields):
        return jsonify({"message": "No valid fields provided for update"}), 400

    session = Session()
    try:
        reservation = session.query(Reservation).filter_by(rid=rid).first()
        if not reservation:
            return jsonify({"message": f"Reservation {rid} not found"}), 404
        for field in allowed_fields:
            if field in data:
                setattr(reservation, field, data[field])
        session.commit()
        return jsonify({
            'message': f'Reservation {rid} modified successfully',
            'reservation': {
                'rid': reservation.rid, 'tid': reservation.tid, 'cid': reservation.cid,
                'status': reservation.status, 'comment': reservation.comment,
                'number_of_people': reservation.number_of_people,
                'reservation_date': str(reservation.reservation_date) if reservation.reservation_date else None,
                'reservation_time': reservation.reservation_time,
                'created_at': str(reservation.created_at) if reservation.created_at else None,
                'updated_at': str(reservation.updated_at) if reservation.updated_at else None
            }
        }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"message": str(e)}), 400
    finally:
        session.close()

# User Story 5: Display occupancy for the next 7 days
@app.route('/api/v1/occupancy_next_7_days', methods=['GET'])
def get_occupancy_next_7_days():
    session = Session()
    try:
        today = datetime.now().date()
        end_date = today + timedelta(days=6)
        results = (session.query(Reservation.reservation_date, func.sum(Reservation.number_of_people).label('people_on_day'))
                   .filter(Reservation.status == 'active', Reservation.reservation_date.between(today, end_date))
                   .group_by(Reservation.reservation_date)
                   .order_by(Reservation.reservation_date)
                   .all())

        occupancy_data = { (today + timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7) }
        for row in results:
            occupancy_data[row[0].strftime('%Y-%m-%d')] = row[1]
        return jsonify({'occupancy_by_day': occupancy_data}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 400
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True)