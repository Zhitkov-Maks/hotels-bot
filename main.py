import functools
import logging
from datetime import date, datetime
from typing import Callable
import telebot
from decouple import config
from telebot import types
from telebot.types import InputMediaPhoto
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from botrequests import low_higth
from users import User
from botrequests import bestdeal
import sqlite3

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

bot_token = config('TOKEN')
bot = telebot.TeleBot(bot_token)
conn = sqlite3.connect('bd/history.db', check_same_thread=False)
cursor = conn.cursor()


def logger(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except (TypeError, ValueError, AttributeError, IndexError):
            with open('logging.log', 'a') as file:
                file.write(f'\n{datetime.now()}, {func.__name__}')
        return result

    return wrapper


def db_table_val(user_id: int, user_name: str, user_surname: str, user_command: str, user_date: str):
    cursor.execute('INSERT INTO users (user_id, user_name, user_surname, user_command, user_date) '
                   'VALUES (?, ?, ?, ?, ?)',
                   (user_id, user_name, user_surname, user_command, user_date))
    conn.commit()


@bot.message_handler(commands=['start', 'hello_world'])
def start_welcome(message):
    """Функция приветствия."""
    logging.info(f'Пользователь {message.chat.id} ввел команду {message.text}')
    user = User.get_user(message.from_user.id)
    bot.send_message(message.from_user.id, 'Здравствуйте, я телеграмм бот для поиска отелей и я помогу найти вам '
                                           'отель по вашим предпочтениям. Чтобы узнать что я умею введите'
                                           ' /help. ')


@bot.message_handler(commands=['help'])
def help_welcome(message):
    """Функция вывода доступных команд."""
    logging.info(f'Пользователь {message.chat.id} ввел команду {message}')
    user = User.get_user(message.chat.id)
    bot.send_message(message.chat.id, "Список доступных команд: "
                                      "\n/lowprice - Вывод самых дешёвых отелей."
                                      "\n/highprice - Вывод самых дорогих отелей."
                                      "\n/bestdeal - Вывод отелей, наиболее подходящих по цене и "
                                      "расположению от центра. "
                                      "\n/history - Вывод истории поиска отелей."
                                      "\n/restart - Перезапуск бота.")


@bot.message_handler(content_types='text')
def city_input(message: types.Message):
    """
    Функция запрашивает город где искать отели.
    """
    logging.info(f'Пользователь - {message.chat.id} ввел сообщение: {message.text}')
    user = User.get_user(message.chat.id)
    user.command = message.text
    if message.text == "/lowprice" or message.text == "/highprice" or message.text == '/bestdeal':
        bot.send_message(message.chat.id, 'Введите город: ')
        bot.register_next_step_handler(message, data_travel)
    elif message.text == '/history':
        bot.send_message(message.chat.id, 'Совсем скоро здесь все будет!')
    elif message.text == '/restart':
        start_welcome(message)
    else:
        bot.send_message(message.chat.id, 'Команда не найдена, видимо вы что-то не так ввели!')
        help_welcome(message)


@logger
def data_travel(message: types.Message):
    """Функция сохраняет введенный город, и направляет на ввод даты."""
    logging.info(f'Пользователь - {message.chat.id} ввел сообщение: {message.text}')
    user = User.get_user(message.chat.id)
    user.city = message.text
    user.data_1, user.data_2 = None, None
    if len(user.city) < 3 or user.city.startswith('/'):
        bot.send_message(message.chat.id, 'Ошибка ввода города!')
        help_welcome(message)
    else:
        bot.send_message(message.chat.id, 'Когда будем заселяться?')
        start_calendar(message)


def start_calendar(message: types.Message):
    """Запускаем Календарь."""
    calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
    bot.send_message(message.chat.id, f"Выберите: {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call: types.CallbackQuery):
    res, key, step = DetailedTelegramCalendar(min_date=date.today()).process(call.data)
    if not res and key:
        bot.edit_message_text(f"Выберите: {LSTEP[step]}", call.message.chat.id, call.message.message_id,
                              reply_markup=key)
    elif res:
        bot.edit_message_text(f"Вы выбрали: {res}", call.message.chat.id, call.message.message_id)
        call.message.text = res
        get_date(call.message)


def get_date(message):
    user = User.get_user(message.chat.id)
    if user.data_1 is None:
        user.data_1 = message.text
        start_calendar(message)
    else:
        user.data_2 = message.text
        data_1 = user.data_1
        data_2 = user.data_2
        data_1 = int(''.join([digit for digit in str(data_1) if digit.isdigit()]))
        data_2 = int(''.join([digit for digit in str(data_2) if digit.isdigit()]))
        logging.info(f'Пользователь - {message.chat.id} ввел даты: {user.data_1} and {user.data_2}')
        if data_1 >= data_2:
            bot.send_message(message.chat.id, 'Неверный ввод даты, попробуйте еще раз.')
            user.data_1, user.data_2 = None, None
            start_calendar(message)
        elif data_1 < data_2 and (user.command == '/lowprice' or user.command == '/highprice'):
            count_hotel(message)
        elif data_1 < data_2 and user.command == '/bestdeal':
            price_range(message)


@logger
def price_range(message: types.Message):
    """
    Получаем диапазон цен для команды bestdeal
    """
    user = User.get_user(message.chat.id)
    user.price = []
    bot.send_message(message.chat.id, 'Введите диапазон цен (в формате: 100-200)')
    bot.register_next_step_handler(message, distance)
    logging.info(f'Функция price_range. Пользователь - {message.from_user.id} ввел сообщение: {message.text}')


@logger
def distance(message):
    user = User.get_user(message.chat.id)
    user.price = message.text.split('-')
    if len(user.price) < 2:
        message.text = user.command
        bot.send_message(message.chat.id, 'Ошибка ввода, попробуйте еще раз!')
        price_range(message)
    else:
        user.distance = None
        bot.send_message(message.chat.id, 'Введите до какого расстоянии от центра искать отели?')
        bot.register_next_step_handler(message, count_hotel)
        logging.info(f'Функция distance. Пользователь - {message.from_user.id} ввел сообщение: {message.text}')


@logger
def count_hotel(message):
    """Спрашиваем сколько отелей необходимо найти."""
    user = User.get_user(message.chat.id)
    if user.command == '/bestdeal':
        temp = message.text
        for i in temp:
            if not i.isdigit():
                bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число!')
                message.text = '-'.join(user.price)
                distance(message)
                break
        else:
            user.distance = message.text
            bot.send_message(message.chat.id, 'Сколько отелей необходимо найти?(Максимум 10!)')
            bot.register_next_step_handler(message, total_check)
            logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}')
    else:
        bot.send_message(message.chat.id, 'Сколько отелей необходимо найти?(Максимум 10!)')
        bot.register_next_step_handler(message, total_check)
        logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}')


@logger
def total_check(message: types.Message):
    """
    Функция проверяет введенные ранее данные и запрашивает нужны ли фотографии
    """
    logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}')
    user = User.get_user(message.chat.id)
    user.count_hotel = message.text
    if int(user.count_hotel) > 10:
        bot.send_message(message.from_user.id, "Ваше количество отелей больше 10, будет показано 10 отелей.")
        user.count_hotel = 10
    markup = telebot.types.ReplyKeyboardMarkup(True, True)
    yes = telebot.types.KeyboardButton("Yes")
    no = telebot.types.KeyboardButton("No")
    markup.add(yes, no)
    message = bot.send_message(message.chat.id, "Показать Фото?", reply_markup=markup)
    bot.register_next_step_handler(message, need_photo)


@logger
def need_photo(message):
    """Функция спрашивает сколько фотографий необходимо запросить?"""
    logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}')
    user = User.get_user(message.chat.id)
    if str(message.text).lower() == 'yes' or str(message.text).lower() == 'да':
        bot.send_message(message.from_user.id, 'Сколько фотографий. Максимум 10.')
        bot.register_next_step_handler(message, requests_city)
    elif str(message.text).lower() == 'no' or str(message.text).lower() == 'нет':
        message.text = 0
        requests_city(message)
    us_id = message.from_user.id
    us_name = message.from_user.first_name
    us_sname = message.from_user.last_name
    us_command = user.command
    us_date = datetime.now()

    db_table_val(user_id=us_id, user_name=us_name, user_surname=us_sname, user_command=us_command,
                 user_date=str(us_date))


@logger
def requests_city(message: types.Message) -> None:
    """Функция поиска города."""
    logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}')
    user = User.get_user(message.chat.id)
    user.count_photo = int(message.text)
    if user.count_photo > 10:
        bot.send_message(message.from_user.id, 'Ваше количество превышает максимально допустимое. Будет показано 10'
                                               'фотографий')
        user.count_photo = 10

    user.result = low_higth.search_city(user.city)
    if len(user.result) < 1:
        bot.send_message(message.from_user.id, f'Сожалеем, город {user.city} не найден!')
    else:
        question = 'Выберите город!'
        keyboard = types.InlineKeyboardMarkup()
        if len(user.result) == 1:
            one = types.InlineKeyboardButton(text=f'{user.result[0][1]}', callback_data='one')
            keyboard.add(one)
        elif len(user.result) == 2:
            one = types.InlineKeyboardButton(text=f'{user.result[0][1]}', callback_data='one')
            keyboard.add(one)
            two = types.InlineKeyboardButton(text=f'{user.result[1][1]}', callback_data='two')
            keyboard.add(two)
        elif len(user.result) >= 3:
            one = types.InlineKeyboardButton(text=f'{user.result[0][1]}', callback_data='one')
            keyboard.add(one)
            two = types.InlineKeyboardButton(text=f'{user.result[1][1]}', callback_data='two')
            keyboard.add(two)
            three = types.InlineKeyboardButton(text=f'{user.result[2][1]}', callback_data='three')
            keyboard.add(three)
        bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)


@logger
@bot.callback_query_handler(func=lambda call: True)
def get_hotel(call: types):
    """Функция поиска отелей"""
    user = User.get_user(call.message.chat.id)
    res = None
    if call.data == 'one':
        res = user.result[0][0]
    elif call.data == 'two':
        res = user.result[1][0]
    elif call.data == 'three':
        res = user.result[2][0]
    request_hotel(call.message, res)


def request_hotel(message, res):
    arrival_data = []
    user = User.get_user(message.chat.id)
    arrival_data.append(user.data_1), arrival_data.append(user.data_2)
    if user.command == '/highprice' or user.command == '/lowprice':
        search_hotel = low_higth.search_hotels(res, arrival_data, int(user.count_hotel), user.command,
                                               int(user.count_photo))
    else:
        search_hotel = bestdeal.search_hotels(res, arrival_data, int(user.count_hotel),
                                              user.price, user.distance, user.count_photo)
    bot.send_message(message.chat.id, 'Ожидайте идет поиск......')
    if len(search_hotel) > 0:
        for dct in search_hotel:
            result = ''
            for info in dct:
                if info != 'Photo':
                    result += f'{info}: {dct[info]}\n'
            bot.send_message(message.chat.id, result)
            media_group = list()
            for info in dct:
                if info == 'Photo':
                    for photo in dct[info]:
                        media_group.append(InputMediaPhoto(photo))
                    bot.send_media_group(message.chat.id, media_group)
    else:
        bot.send_message(message.chat.id, 'Ничего не найдено(((')
    bot.send_message(message.chat.id, "Поиск отелей завершен!")


if __name__ == '__main__':
    bot.infinity_polling()
