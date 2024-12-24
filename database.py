import sqlite3

def create_database():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        age INTEGER,
        telegram_id INTEGER UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    connection.commit()
    connection.close()

def add_user(username, email, age, telegram_id):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO Users (username, email, telegram_id) VALUES (?, ?, ?)
    ''', (username, email, age, telegram_id))

    connection.commit()
    connection.close()

def update_user(telegram_id, username=None, email=None, age=None):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    if username:
        cursor.execute('UPDATE Users SET username = ? WHERE telegram_id = ?', (username, telegram_id))
    if email:
        cursor.execute('UPDATE Users SET email = ? WHERE telegram_id = ?', (email, telegram_id))

    connection.commit()
    connection.close()

def delete_user(telegram_id):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('DELETE FROM Users WHERE telegram_id = ?', (telegram_id,))

    connection.commit()
    connection.close()

def get_all_users():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()

    connection.close()
    return users

def get_user_by_telegram_id(telegram_id):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()

    connection.close()
    return user

# Создаем базу данных и таблицу
create_database()