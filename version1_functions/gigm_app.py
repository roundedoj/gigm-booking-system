import os
import random
import string as st
import datetime as dt
import pymysql

# Open a connection to the already set gigm database
def connect():
    PASSWORD = os.environ.get("MYSQLPASSWORD")

    if PASSWORD is None:
        print("\nMySQL Password retrieval unsuccessful.")
        return None
    try:
        db = pymysql.connect(
            user = "root",
            password = PASSWORD,
            host = "localhost",
            port = 3306,
            database = "gigm",
            autocommit = False
        )

        print("\nConnection to GIGM database successful.")
        return db

    except Exception as e:
        print(f"\nConnection to GIGM database unsuccessful: {e}.")
        return None
        
# Helper functions for the program

# Prompt for non-empty text input
def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value == "":
            print("\nThis cannot be empty. Please try again.")
        else:
            return value

# Prompt for an integer within a specified range
def ask_int(prompt, low, high):
    while True:
        value = input(prompt).strip()
        
        try:
            number = int(value)
        except ValueError:
            print("\nPlease enter a whole number.")
            continue
        if low <= number <= high:
            return number
        print(f"\nPlease enter a number between {low} and {high}.")

# Prompt for date in dd/mm/yyyy format
def ask_date(prompt):
    while True:
        value = input(prompt).strip()

        try:
            return dt.datetime.strptime(value, "%d/%m/%Y").date()

        except ValueError:
            print("\nWrong format. Please use dd/mm/yyyy, for example 31/12/2026.")

# Prompt for an 11-digit phone number
def ask_phone(prompt):
    while True:
        value = input(prompt).strip()

        if not value.isdigit():
            print("\nError, phone number must contain digits only.")
            continue

        if len(value) != 11:
            print("\nError, phone number must have 11 digits.")
            continue

        return value

# Prompt for monetary value greater than zero
def ask_money(prompt):
    while True:
        value = input(prompt).strip()

        try:
            amount = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if amount > 0:
            return round(amount, 2)
        
        print(f"\nPlease enter an amount greater than zero.")

# Prompt for time in 24-hour HH:MM format
def ask_time(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return dt.datetime.strptime(value, "%H:%M").time()
        except ValueError:
            print("\nWrong format. Use 24-hour HH:MM, for example 08:30 or 14:00.")

# Utilities for the program

# Generate a randomized alphanumeric ID string
def make_id(prefix, length):
    characters = st.digits + st.ascii_uppercase
    tail = "".join(random.choice(characters) for _ in range(length))
    return prefix + tail

# Pause output until the user presses Enter
def pause():
    input("\nPress enter to return to the menu...")

# Generate a heading rule line
def line(length = 50):
    return "=" * length

# Generate a section divider line
def divider(length = 80):
    return '-' * length

# Registration feature
def register(db, cursor):
    print("\n" + line())
    print("PASSENGER REGISTRATION")
    print(line())

    # Collect passenger details
    full_name = ask_text("Enter your full name: ")
    phone = ask_phone("Enter your phone number (11 digits): ")
    age = ask_int("Enter your age: ", 1, 120)

    # Check if passenger phone already exists
    cursor.execute(
        "select passenger_id, full_name from passengers where phone = %s", (phone,)
    )
    existing = cursor.fetchone()

    if existing is not None:
        print(f"\nThis phone number is already registered to {existing[1]} with the passenger ID {existing[0]}.")
        return

    # Generate unique passenger ID
    while True:
        passenger_id = make_id("GIG", 7)
        cursor.execute(
            "select passenger_id from passengers where passenger_id = %s", (passenger_id,)
        )
        if cursor.fetchone() is None:
            break

    # Input new passenger record to database
    try:
        cursor.execute(
            """insert into passengers(passenger_id, full_name, phone, age)
            values(%s, %s, %s, %s)""",
            (passenger_id, full_name.title(), phone, age)
        )
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"\nRegistration failed: {e}.\nNothing was saved, please try again.")
        return

    # Display confirmation summary
    print("\nRegistration successful.")
    print(f"Your details are as follows: \nName: {full_name.title()}\nPhone: {phone}\nPassenger ID: {passenger_id}")
    print("\nPlease save your passenger ID. You need it to book a seat.")
    
# Feature for showing upcoming trips with the number of seats still free
def view_trips(cursor):
    print("\n" + line())
    print("AVAILABLE TRIPS")
    print(line())

    # Query active trips, calculate remaining seats, and join route locations
    cursor.execute("""
        select t.trip_id,
               a.city,
               b.city,
               t.travel_date,
               t.departure_time,
               t.fare,
               t.total_seats - count(k.booking_id) as seats_left
        from trips as t
        join terminals as a on t.route_from = a.terminal_code
        join terminals as b on t.route_to = b.terminal_code
        left join bookings as k on t.trip_id = k.trip_id
        where t.travel_date >= current_date()
        group by t.trip_id, a.city, b.city, t.travel_date,
                 t.departure_time, t.fare, t.total_seats
        order by t.travel_date, t.departure_time
    """)
    rows = cursor.fetchall()

    # Handle empty schedule scenario
    if len(rows) == 0:
        print("\nThere are no upcoming trips at the moment.")
        return

    # Column headings layout
    print(f"\n{'ID':<6}{'FROM':<16}{'TO':<16}{'DATE':<14}{'TIME':<10}{'FARE':<12}{'SEATS'}")
    print(divider())

    # Render trip details row-by-row
    for row in rows:
        trip_id = row[0]
        city_from = row[1]
        city_to = row[2]
        travel_date = row[3]
        departure = row[4]
        fare = row[5]
        seats_left = row[6]

        print(f"{trip_id:<6}{city_from:<16}{city_to:<16}{travel_date.strftime('%d/%m/%Y'):<14}{str(departure):<10}{'N' + format(fare, ',.2f'):<12}{seats_left}")
        print(divider())

# Feature for booking seats
def book_seat(db, cursor):
    print("\n" + line())
    print("BOOK A SEAT")
    print(line())

    # Authenticate passenger by passenger ID
    passenger_id = ask_text("Enter your passenger ID: ").upper()
    cursor.execute(
        "select passenger_id, full_name from passengers where passenger_id = %s", (passenger_id,)
    )
    passenger = cursor.fetchone()
    if passenger is None:
        print("\nNo passenger found with that ID.\nPlease register first.")
        return
    print(f"\nWelcome back, {passenger[1]}.")

    # Display upcoming trips
    view_trips(cursor)

    # Check if trip exists
    trip_id = ask_int("\nEnter the trip ID you want: ", 1, 999999)
    cursor.execute(
        "select travel_date, departure_time, fare, total_seats from trips where trip_id = %s", (trip_id,)
    )
    trip = cursor.fetchone()
    if trip is None:
        print("\nThere is no trip with that ID.")
        return
    travel_date = trip[0]
    departure_time = trip[1]
    fare = trip[2]
    total_seats = trip[3]

    # Check if the bus has already left
    if travel_date < dt.date.today():
        print("\nThat trip has already departed. Please pick another.")
        return

    # Check if bus is full and display the seats that have been taken
    cursor.execute(
        "select seat_no from bookings where trip_id = %s order by seat_no", (trip_id,)
    )
    rows = cursor.fetchall()
    taken = []
    for row in rows:
        taken.append(row[0])
    seats_taken = len(taken)

    if seats_taken >= total_seats:
        print("\nSorry, this trip is fully booked.")
        return
    
    print(f"\nTrip {trip_id} | {travel_date.strftime('%d/%m/%Y')} at {departure_time}")
    print(f"Fare: N{format(fare, ',.2f')}")
    print(f"Seats on this bus: 1 to {total_seats}")

    if len(taken) == 0:
        print("Seats already taken: none, the bus is empty.")
    else:
        print(f"Seats already taken: {taken}")
    print(f"Seats remaining: {total_seats - seats_taken}")

    # Prompt seat selection with interactive retry loop
    while True:
        seat_no = ask_int(f"\nChoose your seat (1-{total_seats}): ", 1, total_seats)
        if seat_no in taken:
            print(f"\nSeat {seat_no} is already taken. Please choose another.")
        else:
            break

    # Get final confirmation from passenger
    print(f"\nYou are booking seat {seat_no} for N{format(fare, ',.2f')}.")
    confirm = ask_text("Type YES to confirm, or anything else to cancel: ").upper()

    if confirm != "YES":
        print("\nBooking cancelled. Nothing was saved.")
        return

    # Generate unique booking ID
    while True:
        booking_id = make_id("BK", 8)
        cursor.execute(
            "select booking_id from bookings where booking_id = %s", (booking_id,)
        )
        if cursor.fetchone() is None:
            break

    # Input new booking record to database
    try:
        cursor.execute(
            """insert into bookings(booking_id, passenger_id, trip_id, seat_no, amount_paid)
                values (%s, %s, %s, %s, %s)""",
            (booking_id, passenger_id, trip_id, seat_no, fare)
        )
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"\nBooking failed: {e}.\nNothing was saved, please try again.")
        return

    # Display booking receipt
    print("\n" + line())
    print("BOOKING CONFIRMED")
    print(line())
    print(f"Booking ID: {booking_id}\nPassenger: {passenger[1]}\nTrip ID: {trip_id}\nDate: {travel_date.strftime('%d %B, %Y')}\nDeparture: {departure_time}\nSeat number: {seat_no}\nAmount paid: N{format(fare, ',.2f')}")
    print(line())
    print("Please arrive at the terminal 30 minutes before departure.")

