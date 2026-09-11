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
def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value == "":
            print("\nThis cannot be empty. Please try again.")
        else:
            return value

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

def ask_date(prompt):
    while True:
        value = input(prompt).strip()

        try:
            return dt.datetime.strptime(value, "%d/%m/%Y").date()

        except ValueError:
            print("\nWrong format. Please use dd/mm/yyyy, for example 31/12/2026.")

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

# Utilities for the program
def make_id(prefix, length):
    characters = st.digits + st.ascii_uppercase
    tail = "".join(random.choice(characters) for _ in range(length))
    return prefix + tail

def pause():
    input("\nPress enter to return to the menu...")

def line(length = 50):
    return "=" * length

def divider(length = 80):
    return '-' * length

# Registration feature
def register(db, cursor):
    print("\n" + line())
    print("PASSENGER REGISTRATION")
    print(line())

    full_name = ask_text("Enter your full name: ")
    phone = ask_phone("Enter your phone number (11 digits): ")
    age = ask_int("Enter your age: ", 1, 120)

    cursor.execute(
        "select passenger_id, full_name from passengers where phone = %s", (phone,)
    )
    existing = cursor.fetchone()

    if existing is not None:
        print(f"\nThis phone number is already registered to {existing[1]} with the passenger ID {existing[0]}.")
        return

    passenger_id = make_id("GIG", 7)

    try:
        cursor.execute(
            """insert into passengers(passenger_id, full_name, phone, age)
            values(%s, %s, %s, %s)""",
            (passenger_id, full_name.title(), phone, age)
        )
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"\nRegistration failed: {e}.\n Nothing was saved, please try again.")
        return

    print("\nRegistration successful.")
    print(f"Your details are as follows: \nName: {full_name.title()}\nPhone: {phone}\nPassenger ID: {passenger_id}")
    print("\nPlease save your passenger ID. You need it to book a seat.")
    
# Feature for showing upcoming trips with the number of seats still free
def view_trips(cursor):
    print("\n" + line())
    print("AVAILABLE TRIPS")
    print(line())

    # This query does four jobs:
    #  1. joins terminals TWICE, once for the origin and once for the
    #     destination, using aliases a and b so MySQL can tell them apart
    #  2. LEFT JOIN to bookings so trips with zero bookings still appear
    #     (a plain JOIN would hide any trip nobody has booked yet)
    #  3. counts the bookings per trip and subtracts from total_seats
    #  4. hides trips whose date has already passed
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

    if len(rows) == 0:
        print("\nThere are no upcoming trips at the moment.")
        return

    # Column headings
    print(f"\n{'ID':<6}{'FROM':<16}{'TO':<16}{'DATE':<14}{'TIME':<10}{'FARE':<12}{'SEATS'}")
    print(divider())

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

