import os
import pymysql

TERMINALS = [
    ("JIBOWU", "Jibowu Terminal", "Lagos"),
    ("AJAH", "Ajah Terminal", "Lagos"),
    ("UTAKO", "Utako Terminal", "Abuja"),
    ("BENIN", "Benin Terminal", "Benin City"),
    ("ONITSHA", "Onitsha Terminal", "Onitsha"),
    ("PHC", "Port Harcourt Terminal", "Port Harcourt"),
    ("UYO", "Uyo Terminal", "Uyo"),
    ("ASABA", "Asaba Terminal", "Asaba")
]

def main():
    PASSWORD = os.environ.get("MYSQLPASSWORD")

    if PASSWORD is None:
        print("MYSQL Password retrieval unsuccessful.")
        return

    try:
        db = pymysql.connect(
            user = "root",
            password = PASSWORD,
            host = "localhost",
            port = 3306
        )

    except Exception as e:
        print(f"\nMySQL connection failed: {e}")
        return

    cursor = db.cursor()

    try:
        # Creating the database
        cursor.execute("create database if not exists gigm")
        cursor.execute("use gigm")
        print("\nDatabase ready.")

        # Table for terminals
        cursor.execute("""
            create table if not exists terminals(
                terminal_code varchar(10) primary key,
                terminal_name varchar(50) not null,
                city varchar(30) not null
            )
        """)
        print("\nTerminals table ready.")

        # Table for passengers
        cursor.execute("""
            create table if not exists passengers(
                passenger_id varchar(12) primary key,
                full_name varchar(60) not null,
                phone varchar(11) unique not null,
                age int not null,
                date_registered datetime default current_timestamp
            )
        """)
        print("\nPassengers table ready.")

        # Table for trips
        cursor.execute("""
            create table if not exists trips(
                trip_id int primary key auto_increment,
                route_from varchar(10) not null,
                route_to varchar(10) not null,
                travel_date date not null,
                departure_time time not null,
                fare decimal(10, 2) not null,
                total_seats int not null,
                foreign key (route_from) references terminals(terminal_code),
                foreign key (route_to) references terminals(terminal_code),
                unique(route_from, route_to, travel_date, departure_time)
            )
        """)
        print("\nTrips table ready.")

        # Table for bookings
        cursor.execute("""
            create table if not exists bookings(
                booking_id varchar(12) primary key,
                passenger_id varchar(12) not null,
                trip_id int not null,
                seat_no int not null,
                amount_paid decimal(10, 2) not null,
                booked_on datetime default current_timestamp,
                foreign key (passenger_id) references passengers(passenger_id),
                foreign key (trip_id) references trips(trip_id),
                unique(trip_id, seat_no)
            )
        """)
        print("\nBookings table ready.")

        # Adding values into the terminals table
        for row in TERMINALS:
            cursor.execute(
                "insert ignore into terminals(terminal_code, terminal_name, city) values(%s, %s, %s)", row
            )

        db.commit()
        print(f"\n{len(TERMINALS)} terminals added.")

    except Exception as e:
        db.rollback()
        print(f"\nSetup unsuccessful: {e}")

    finally:
        cursor.close()
        db.close()
        print("Connection closed")

if __name__ == "__main__":
    main()