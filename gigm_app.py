# ============================================================
# gigm_app.py
# GIGM Booking System - command line booking application
# Prerequisite: run setup_database.py once before first use
# Environment variables required: MYSQLPASSWORD, GIGM_ADMIN_PIN
# ============================================================

import os
import random
import string as st
import datetime as dt
import pymysql

# Open a connection to the gigm database
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
            print("\nPlease enter a valid number.")
            continue
        if amount > 0:
            return round(amount, 2)

        print("\nPlease enter an amount greater than zero.")

# Prompt for time in 24-hour HH:MM format
def ask_time(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return dt.datetime.strptime(value, "%H:%M").time()
        except ValueError:
            print("\nWrong format. Use 24-hour HH:MM, for example 08:30 or 14:00.")

# Utilities for the program

# Generate a random alphanumeric ID with a fixed prefix
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

    # Insert the new passenger record
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

    # Print the registration summary
    print("\nRegistration successful.")
    print(f"Your details are as follows: \nName: {full_name.title()}\nPhone: {phone}\nPassenger ID: {passenger_id}")
    print("\nPlease save your passenger ID. You need it to book a seat.")

# Feature for showing upcoming trips with the number of seats still free
def view_trips(cursor):
    print("\n" + line())
    print("AVAILABLE TRIPS")
    print(line())

    # Query upcoming trips, join the terminal cities and compute seats remaining
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

    # Handle the empty schedule case
    if len(rows) == 0:
        print("\nThere are no upcoming trips at the moment.")
        return

    # Print the column headings
    print(f"\n{'ID':<6}{'FROM':<16}{'TO':<16}{'DATE':<14}{'TIME':<10}{'FARE':<12}{'SEATS'}")
    print(divider())

    # Print one line per trip
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

    # Verify the passenger exists
    passenger_id = ask_text("Enter your passenger ID: ").upper()
    cursor.execute(
        "select passenger_id, full_name from passengers where passenger_id = %s", (passenger_id,)
    )
    passenger = cursor.fetchone()
    if passenger is None:
        print("\nNo passenger found with that ID.\nPlease register first.")
        return
    print(f"\nWelcome back, {passenger[1]}.")

    # Show the current schedule
    view_trips(cursor)

    # Verify the trip exists
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

    # Reject trips that have already departed
    if travel_date < dt.date.today():
        print("\nThat trip has already departed. Please pick another.")
        return

    # Collect the seats already taken and check whether the bus is full
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

    # Prompt for a seat, repeating until a free one is chosen
    while True:
        seat_no = ask_int(f"\nChoose your seat (1-{total_seats}): ", 1, total_seats)
        if seat_no in taken:
            print(f"\nSeat {seat_no} is already taken. Please choose another.")
        else:
            break

    # Require explicit confirmation before writing
    print(f"\nYou are booking seat {seat_no} for N{format(fare, ',.2f')}.")
    confirm = ask_text("Type YES to confirm, or NO to cancel: ").upper()

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

    # Insert the new booking record
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

    # Print the booking receipt
    print("\n" + line())
    print("BOOKING CONFIRMED")
    print(line())
    print(f"Booking ID: {booking_id}\nPassenger: {passenger[1]}\nTrip ID: {trip_id}\nDate: {travel_date.strftime('%d %B, %Y')}\nDeparture: {departure_time}\nSeat number: {seat_no}\nAmount paid: N{format(fare, ',.2f')}")
    print(line())
    print("Please arrive at the terminal 30 minutes before departure.")

# Feature for displaying bookings belonging to one passenger
def my_bookings(cursor):
    print("\n" + line())
    print("MY BOOKINGS")
    print(line())

    # Verify the passenger exists
    passenger_id = ask_text("Enter your passenger ID: ").upper()
    cursor.execute(
        "select full_name from passengers where passenger_id = %s", (passenger_id,)
    )
    passenger = cursor.fetchone()
    if passenger is None:
        print("\nNo passenger found with that ID.")
        return

    # Query this passenger's bookings and label each as UPCOMING or COMPLETED
    cursor.execute("""
        select k.booking_id,
            a.city,
            b.city,
            t.travel_date,
            t.departure_time,
            k.seat_no,
            k.amount_paid,
            case
                when t.travel_date >= current_date() then 'UPCOMING'
                else 'COMPLETED'
            end as status
        from bookings as k
        join trips as t on k.trip_id = t.trip_id
        join terminals as a on t.route_from = a.terminal_code
        join terminals as b on t.route_to = b.terminal_code
        where k.passenger_id = %s
        order by t.travel_date desc
    """, (passenger_id,))
    rows = cursor.fetchall()

    if len(rows) == 0:
        print(f"\n{passenger[0]}, you have no bookings yet.")
        return

    # Print the bookings table
    print(f"\nBookings for {passenger[0]}, ({len(rows)} total).")
    print(divider(length = 95))
    print(f"{'BOOKING ID':<14}{'FROM':<14}{'TO':<14}{'DATE':<13}{'TIME':<10}{'SEAT':<7}{'PAID':<13}{'STATUS'}")
    print(divider(length = 95))

    for row in rows:
        booking_id = row[0]
        city_from = row[1]
        city_to = row[2]
        travel_date = row[3]
        departure_time = row[4]
        seat_no = row[5]
        amount_paid = row[6]
        status = row[7]
        print(f"{booking_id:<14}{city_from:<14}{city_to:<14}{travel_date.strftime('%d/%m/%Y'):<13}{str(departure_time):<10}{seat_no:<7}{'N' + format(amount_paid, ',.2f'):<13}{status}")
    print(divider(length = 95))

# Feature for cancelling a booking
def cancel_booking(db, cursor):
    print("\n" + line())
    print("CANCEL A BOOKING")
    print(line())

    # Verify the passenger exists
    passenger_id = ask_text("Enter your passenger ID: ").upper()
    cursor.execute(
        "select full_name from passengers where passenger_id = %s", (passenger_id,)
    )
    passenger = cursor.fetchone()

    if passenger is None:
        print("\nNo passenger found with that ID.")
        return

    # Verify the booking exists and belongs to this passenger
    booking_id = ask_text("\nEnter the booking ID to cancel: ").upper()

    cursor.execute("""
        select k.seat_no, t.travel_date, k.amount_paid
        from bookings as k
        join trips as t on k.trip_id = t.trip_id
        where k.booking_id = %s and k.passenger_id = %s
    """, (booking_id, passenger_id)
    )
    booking = cursor.fetchone()

    if booking is None:
        print("\nNo booking with that ID was found under your passenger ID.")
        return

    seat_no = booking[0]
    travel_date = booking[1]
    amount_paid = booking[2]

    # Reject cancellation if the journey has already taken place
    if travel_date < dt.date.today():
        print("\nThat journey has already taken place and cannot be cancelled.")
        return

    # Require explicit confirmation before writing
    print(f"\nAbout to cancel: seat {seat_no} on {travel_date.strftime('%d %B, %Y')}")
    print(f"Amount paid: N{format(amount_paid, ',.2f')}")
    confirm = ask_text("Type YES to confirm cancellation: ").upper()

    if confirm != "YES":
        print("\nCancellation stopped. Your booking is unchanged.")
        return

    # Delete the booking record
    try:
        cursor.execute(
            "delete from bookings where booking_id = %s and passenger_id = %s", (booking_id, passenger_id)
        )

        if cursor.rowcount != 1:
            db.rollback()
            print("\nNothing was cancelled. Please try again.")
            return
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"\nCancellation failed: {e}")
        print("Your booking is unchanged.")
        return

    print(f"\nBooking {booking_id} has been cancelled.\nSeat {seat_no} is now available for other passengers.")

# Feature for adding a trip (Admin only)
def add_trip(db, cursor):
    print("\n" + line())
    print("ADMIN - ADD A TRIP")
    print(line())

    # Load the admin PIN from the environment
    admin_pin = os.environ.get("GIGM_ADMIN_PIN")

    if admin_pin is None:
        print("GIGM_ADMIN_PIN is not set. Admin access is unavailable.")
        return

    # Allow three attempts, then return to the menu
    allowed = False
    for attempt in range(3):
        pin_input = input("Enter admin PIN: ").strip()
        if pin_input == admin_pin:
            allowed = True
            break
        else:
            print(f"Wrong PIN. {2 - attempt} attempt(s) remaining.")

    if not allowed:
        print("\nAccess denied.")
        return

    print("\nAccess granted.\n")

    # Display the valid terminal codes
    cursor.execute("select terminal_code, terminal_name, city from terminals order by city")
    terminals = cursor.fetchall()

    print("AVAILABLE TERMINALS")
    print(divider(length = 60))
    for t in terminals:
        print(f"{t[0]:<12}{t[1]:<28}{t[2]}")
    print(divider(length = 60))

    # Verify the departure terminal exists
    route_from = ask_text("\nEnter the DEPARTURE terminal code: ").upper()

    cursor.execute("select city from terminals where terminal_code = %s", (route_from,))
    origin = cursor.fetchone()

    if origin is None:
        print("\nThat terminal code does not exist. Use one from the list above.")
        return

    # Verify the destination terminal exists
    route_to = ask_text("Enter the DESTINATION terminal code: ").upper()

    cursor.execute("select city from terminals where terminal_code = %s", (route_to,))
    destination = cursor.fetchone()

    if destination is None:
        print("\nThat terminal code does not exist. Use one from the list above.")
        return

    # Reject a trip that starts and ends at the same terminal
    if route_from == route_to:
        print("A trip cannot start and end at the same terminal.")
        return

    # Collect and validate the remaining trip details
    travel_date = ask_date("Enter the travel date (dd/mm/yyyy): ")
    if travel_date < dt.date.today():
        print("You cannot create a trip for a date that has already passed.")
        return
    departure_time = ask_time("Enter the departure time (HH:MM, 24-hour): ")
    fare = ask_money("Enter the fare in Naira: ")
    total_seats = ask_int("Enter the number of seats on the bus (1-60): ", 1, 60)

    # Check if an identical trip already exists
    cursor.execute("""
        select trip_id from trips
        where route_from = %s and route_to = %s
          and travel_date = %s and departure_time = %s
    """, (route_from, route_to, travel_date, departure_time))

    duplicate = cursor.fetchone()
    if duplicate is not None:
        print(f"\nThe exact trip already exists as trip ID {duplicate[0]}.")
        return

    # Require explicit confirmation before writing
    print("\nABOUT TO CREATE:")
    print(f"Route: {origin[0]} to {destination[0]}\nDate: {travel_date.strftime('%d %B, %Y')}\nTime: {departure_time}\nFare: N{format(fare, ',.2f')}\nCapacity: {total_seats} seats")

    confirm = ask_text("\nType YES to create this trip: ").upper()
    if confirm != "YES":
        print("\nCancelled. Nothing was saved.")
        return

    # Insert the new trip record
    try:
        cursor.execute("""
            insert into trips(route_from, route_to, travel_date,
                              departure_time, fare, total_seats)
            values (%s, %s, %s, %s, %s, %s)
        """, (route_from, route_to, travel_date, departure_time, fare, total_seats))

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"\nCould not create the trip: {e}.\nNothing was saved.")
        return

    print(f"\nTrip created successfully. The new trip ID is {cursor.lastrowid}.")

# Main menu
def main_page():
    db = connect()
    if db is None:
        return
    cursor = db.cursor()

    try:
        while True:

            print("\n" + line())
            print("====== GOD IS GOOD MOTORS - BOOKING TERMINAL ======")
            print(line())
            print("1 >> Register as a passenger")
            print("2 >> View available trips")
            print("3 >> Book a seat")
            print("4 >> View my bookings")
            print("5 >> Cancel a booking")
            print("6 >> Admin: add a trip")
            print("7 >> Exit")

            choice = ask_int("\nChoose an option (1-7): ", 1, 7)

            if choice == 1:
                register(db, cursor)
                pause()

            elif choice == 2:
                view_trips(cursor)
                pause()

            elif choice == 3:
                book_seat(db, cursor)
                pause()

            elif choice == 4:
                my_bookings(cursor)
                pause()

            elif choice == 5:
                cancel_booking(db, cursor)
                pause()

            elif choice == 6:
                add_trip(db, cursor)
                pause()

            elif choice == 7:
                print("\nThank you for travelling with GIGM. Safe journey.")
                break

    finally:
        cursor.close()
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main_page()