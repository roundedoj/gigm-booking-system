import os
import random
import string as st
import datetime as dt
import pymysql

# Open a connection to the already set gigm database
def connect():
    PASSWORD = os.environ.get("MYSQLPASSWORD")

    if PASSWORD is None:
        print("\nMySQL Password retrieval unsuccessful")
        return None
    try:
        db = pymysql.connect(
            user = "Root",
            password = "PASSWORD",
            host = "localhost",
            port = 3306,
            database = "gigm",
            autocommit = False
        )

        print("\nConnection to GIGM database successful")
        return db

    except Exception as e:
        print(f"Connection to GIGM database unsuccessful: {e}")
        return None
        
