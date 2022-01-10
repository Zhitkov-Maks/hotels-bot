import sqlite3


def create_tables():
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
       id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
       id_user INTEGER NOT NULL,
       date DATETIME NOT NULL,
       command STRING NOT NULL);
    """)

    cur.execute("""CREATE TABLE IF NOT EXISTS hotels(
           id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
           id_users INTEGER NOT NULL,
           hotel_info STRING NOT NULL);
        """)

    cur.execute("""CREATE TABLE IF NOT EXISTS photos(
           id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
           id_hotels INTEGER NOT NULL,
           photo STRING NOT NULL);
        """)

    conn.commit()


def write_users(user_id: int, date: str, command: str):
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO users (id_user, date, command) VALUES (?, ?, ?)',
                (user_id, command, date))
    conn.commit()


def write_hotels():
    pass
