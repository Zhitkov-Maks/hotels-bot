import sqlite3


def create_tables() -> None:
    """Функция для создания таблиц."""
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()

    # Таблица users
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
       id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
       id_user INTEGER NOT NULL,
       date DATETIME NOT NULL,
       command STRING NOT NULL);
    """)

    # Таблица hotels
    cur.execute("""CREATE TABLE IF NOT EXISTS hotels(
           id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
           id_users INTEGER NOT NULL,
           hotel_info STRING NOT NULL,
           id_com int NOT NULL,
           photo STRING NULL);
        """)

    conn.commit()


def write_users(user_id: int, date: str, command: str, ) -> int:
    """"
    Функция для записи пользователей
    user_id: id пользователя телеграм бота
    date: дата
    command: введенная команда
    Возвращает ключ для записи в следующую таблицу, чтобы их можно было соединить.
    """
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO users (id_user, date, command) VALUES (?, ?, ?)',
                (user_id, command, date))
    sql_select_query = """SELECT max(id) FROM users WHERE id_user = ?"""
    cur.execute(sql_select_query, (user_id,))
    result = cur.fetchone()
    conn.commit()
    return result[0]


def write_hotels(user_id: int, info: str, id_com: int, photo: str) -> None:
    """
    Функция для записи в базу истории поиска
    user_id: id пользователя телеграмм бота
    info: информация об отеле
    id_com: ключ для соединения с пользователями
    photo: фотографии
    """
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO hotels (id_users, hotel_info, id_com, photo) VALUES (?, ?, ?, ?)',
                (user_id, info, id_com, photo))
    conn.commit()


def get_date(id_user: int) -> list:
    """
    Функция для получения даты и команды.
    id_user: id пользователя телеграмм бота.
    """
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()

    cur.execute("""SELECT command, date from users WHERE id_user = ? ORDER BY date DESC LIMIT 20""", (id_user,))
    result = cur.fetchall()
    conn.commit()
    return result


def get_info(user_id: int, date: int) -> list:
    """
    Функция для получения данных об отеле.
    user_id: id пользователя телеграмм бота
    date: дата
    """
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()
    cur.execute("""SELECT hotels.hotel_info, hotels.photo FROM users 
    INNER JOIN hotels ON users.id = 
    hotels.id_com WHERE id_users = ? and date = ? ORDER BY users.date""", (user_id, date,))
    result = cur.fetchall()
    conn.commit()
    return result


def clean(user_id: int) -> None:
    """
    Функция для очистки базы данных.
    user_id: id пользователя телеграмм бота
    """
    conn = sqlite3.connect('history_bd.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM hotels WHERE id_users = ?', (user_id,))
    cur.execute('DELETE FROM users WHERE id_user = ?', (user_id,))
    conn.commit()
