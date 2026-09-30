import sqlite3

DATABASE = "resumeiq.db"

def get_connection():
    connection = sqlite3.connect(
        DATABASE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection

def init_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            free_credits INTEGER DEFAULT 5,
            paid_balance REAL DEFAULT 0,
            total_analyses INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()

def create_user(name, email, password):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users
        (name, email, password, free_credits, paid_balance)
        VALUES (?, ?, ?, 5, 0)
        """,
        (name, email, password)
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id

def get_user_by_email(email):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()

    connection.close()

    return user

def get_user_by_id(user_id):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    connection.close()

    return user

def consume_analysis(user_id):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "SELECT free_credits, paid_balance FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        connection.close()
        return {
            "allowed": False,
            "reason": "User not found"
        }

    free_credits = user["free_credits"]
    paid_balance = user["paid_balance"]

    if free_credits > 0:

        cursor.execute(
            """
            UPDATE users
            SET free_credits = free_credits - 1,
                total_analyses = total_analyses + 1
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()
        connection.close()

        return {
            "allowed": True,
            "charged": 0,
            "free_used": True,
            "remaining_free": free_credits - 1
        }

    if paid_balance >= 10:

        cursor.execute(
            """
            UPDATE users
            SET paid_balance = paid_balance - 10,
                total_analyses = total_analyses + 1
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()
        connection.close()

        return {
            "allowed": True,
            "charged": 10,
            "free_used": False,
            "remaining_balance": paid_balance - 10
        }

    connection.close()

    return {
        "allowed": False,
        "charged": 10,
        "reason": "Payment required"
    }