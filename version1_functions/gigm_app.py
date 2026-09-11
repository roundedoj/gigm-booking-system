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
    
