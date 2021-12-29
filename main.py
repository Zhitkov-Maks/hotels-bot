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
)  # Выводит в консоль введенные данные.

bot_token = config('TOKEN')
bot = telebot.TeleBot(bot_token)

def logger(func: Callable) -> Callable:
    """"Декоратор для обработки ошибок."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result: callable(func) = func(*args, **kwargs)
        except (TypeError, ValueError, AttributeError, IndexError, NameError) as err:
            bot.send_message(message.chat.id, 'Извините произошла ошибка. Попробуйте еще раз!')
            help_welcome(message)
            with open('logging.log', 'a') as file:
                file.write(f'\n{datetime.now()}, {type(err)} {func.__name__}')
        return result
    return wrapper


@bot.message_handler(commands=['start', 'hello_world'])
def start_welcome(message):
    """Функция приветствия, реагирует на команды ('start', 'hello_world')"""
    user = User.get_user(message.from_user.id)
    bot.send_message(message.from_user.id, 'Здравствуйте, я телеграмм бот для поиска отелей и я помогу найти вам '
                                           'отель по вашим предпочтениям. Чтобы узнать что я умею введите'
                                           ' /help. ')
    logging.info(f'Пользователь {message.chat.id} ввел команду {message.text}, функция start_welcome. {user}')


@bot.message_handler(commands=['help'])
def help_welcome(message) -> None:
    """Функция вывода доступных команд."""
    user: object = User.get_user(message.chat.id)
    bot.send_message(message.chat.id, "Список доступных команд: "
                                      "\n/lowprice - Вывод самых дешёвых отелей."
                                      "\n/highprice - Вывод самых дорогих отелей."
                                      "\n/bestdeal - Вывод отелей, наиболее подходящих по цене и "
                                      "расположению от центра. "
                                      "\n/history - Вывод истории поиска отелей."
                                      "\n/settings - В какой валюте будем искать отели?")
    logging.info(f'Пользователь {message.chat.id} ввел команду {message.text}, функция help_welcome, {user}')


@logger
@bot.message_handler(content_types='text')
def command_input(message: types.Message) -> None:
    """
    Функция обрабатывает любой текст кроме команд ('/start', '/hello_world', /help)
    """
    user: object = User.get_user(message.chat.id)
    user.command = message.text
    if message.text == "/lowprice" or message.text == "/highprice" or message.text == '/bestdeal':
        bot.send_message(message.chat.id, 'Введите город: ')
        bot.register_next_step_handler(message, date_travel)

    elif message.text == '/history':
        bot.send_message(message.chat.id, 'Совсем скоро здесь все будет!')

    elif message.text == '/settings':
        bax = telebot.types.ReplyKeyboardMarkup(True, True)
        rub = telebot.types.KeyboardButton("В рублях!")
        dollars = telebot.types.KeyboardButton("In dollars")
        bax.add(rub, dollars)
        message = bot.send_message(message.chat.id, "В какой валюте искать отели?", reply_markup=bax)
        bot.register_next_step_handler(message, money)
    else:
        bot.send_message(message.chat.id, 'Команда не найдена, видимо вы что-то не так ввели!')
        help_welcome(message)
    logging.info(f'Пользователь - {message.chat.id} ввел сообщение: {message.text}, функция city_input. {user}')


@logger
def money(message):
    user: object = User.get_user(message.from_user.id)
    if message.text == 'В рублях!':
        user.money = "RUB"
    elif message.text == "In dollars":
        user.money = "USD"
    bot.send_message(message.chat.id, "Успешно!, Давайте искать отели!")
    help_welcome(message)


@logger
def date_travel(message: types.Message) -> None:
    """Функция сохраняет введенный город, и направляет на ввод даты."""
    user: object = User.get_user(message.chat.id)
    user.city = message.text
    user.date_1, user.date_2 = None, None

    if len(user.city) < 3:
        bot.send_message(message.chat.id, 'Ошибка ввода города! Введите еще раз!')
        bot.register_next_step_handler(message, data_travel)

    elif user.city.startswith('/'):
        bot.send_message(message.chat.id, 'Ошибка ввода города!')
        help_welcome(message)

    else:
        bot.send_message(message.chat.id, 'Когда будем заселяться?')
        start_calendar(message)
    logging.info(f'Пользователь - {message.chat.id} ввел сообщение: {message.text}, функция data_travel. {user}')


@logger
def start_calendar(message: types.KeyboardButton) -> None:
    """Запускаем Календарь."""
    calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
    bot.send_message(message.chat.id, f"Выберите: {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call: types.CallbackQuery) -> None:
    res, key, step = DetailedTelegramCalendar(min_date=date.today()).process(call.data)
    if not res and key:
        bot.edit_message_text(f"Выберите: {LSTEP[step]}", call.message.chat.id, call.message.message_id,
                              reply_markup=key)
    elif res:
        bot.edit_message_text(f"Вы выбрали: {res}", call.message.chat.id, call.message.message_id)
        call.message.text = res
        get_date(call.message)


@logger
def get_date(message: types.Message) -> None:
    user = User.get_user(message.chat.id)
    if user.date_1 is None:
        user.date_1 = message.text
        start_calendar(message)
    else:
        user.date_2 = message.text
        date_1 = user.date_1
        date_2 = user.date_2
        # Проверяем не ввел ли пользователь вторую дату меньше чем первую.
        date_1: int = int(''.join([digit for digit in str(date_1) if digit.isdigit()]))
        date_2: int = int(''.join([digit for digit in str(date_2) if digit.isdigit()]))
        logging.info(f'Пользователь - {message.chat.id} ввел даты: {user.date_1} and {user.date_2}')

        if date_1 >= date_2:
            bot.send_message(message.chat.id, 'Неверный ввод даты, попробуйте еще раз.')
            user.date_1, user.date_2 = None, None
            start_calendar(message)

        elif date_1 < date_2 and (user.command == '/lowprice' or user.command == '/highprice'):
            bot.send_message(message.chat.id, 'Сколько отелей необходимо показать?(Максимум 25)')
            bot.register_next_step_handler(message, get_photo)

        elif date_1 < date_2 and user.command == '/bestdeal':
            bot.send_message(message.chat.id, 'Введите диапазон цен (в формате: min-max)')
            bot.register_next_step_handler(message, distance)
        logging.info(f'Пользователь - {message.chat.id} ввел сообщение: {message.text}, функция data_travel. {user}')


@logger
def distance(message: types.Message) -> None:
    if message.text.startswith('/'):
        help_welcome(message)
    else:
        user: object = User.get_user(message.chat.id)
        user.price = message.text.split('-')
        if len(user.price) < 2:
            message.text = user.command
            bot.send_message(message.chat.id, 'Ошибка ввода, введите еще раз еще раз!')
            bot.register_next_step_handler(message, distance)
        else:
            user.distance = None
            bot.send_message(message.chat.id, 'Введите до какого расстоянии от центра искать отели?')
            bot.register_next_step_handler(message, count_hotel)
        logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, Функция distance. {user}')


@logger
def count_hotel(message: types.Message):
    """Спрашиваем сколько отелей необходимо найти."""
    if message.text.startswith('/'):
        help_welcome(message)
    else:
        user: object = User.get_user(message.chat.id)
        temp = message.text
        if not temp.isdigit():
            bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, count_hotel)
        else:
            user.distance = message.text
            bot.send_message(message.chat.id, 'Сколько отелей необходимо найти?(Максимум 25!)')
            bot.register_next_step_handler(message, get_photo)
        logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, count_hotel. {user}')


@logger
def get_photo(message: types.Message) -> None:
    """
    Функция проверяет введенные ранее данные и запрашивает нужны ли фотографии
    """
    if message.text.startswith('/'):
        help_welcome(message)
    else:
        user: object = User.get_user(message.chat.id)
        user.count_hotel = message.text
        try:
            if int(user.count_hotel) > 25:
                bot.send_message(message.from_user.id, "Ваше количество отелей больше 25, будет показано 25 отелей.")
                user.count_hotel = 25
            markup = telebot.types.ReplyKeyboardMarkup(True, True)
            yes = telebot.types.KeyboardButton("Yes")
            no = telebot.types.KeyboardButton("No")
            markup.add(yes, no)
            message = bot.send_message(message.chat.id, "Показать Фото?", reply_markup=markup)
            bot.register_next_step_handler(message, need_photo)
        except ValueError:
            bot.send_message(message.chat.id, 'Нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, get_photo)
        logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, get_photo. {user}')


@logger
def need_photo(message: types.ReplyKeyboardMarkup) -> None:
    """Функция спрашивает сколько фотографий необходимо запросить?"""
    user: object = User.get_user(message.chat.id)
    if str(message.text).lower() == 'yes' or str(message.text).lower() == 'да':
        bot.send_message(message.from_user.id, 'Сколько фотографий. Максимум 10.')
        bot.register_next_step_handler(message, requests_city)
    elif str(message.text).lower() == 'no' or str(message.text).lower() == 'нет':
        message.text = '0'
        requests_city(message)
    elif str(message.text).startswith('/'):
        help_welcome(message)
    logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, need_photo. {user}')


@logger
def requests_city(message: types.Message) -> None:
    """Функция поиска города."""
    user: object = User.get_user(message.chat.id)
    if message.text.startswith('/'):
        help_welcome(message)
    else:
        try:
            user.count_photo = int(message.text)
            if user.count_photo > 10:
                bot.send_message(message.from_user.id, 'Ваше количество превышает максимально допустимое. Будет показано 10'
                                                       'фотографий')
                user.count_photo = 10

            result: list = low_higth.search_city(user.city)
            if len(result) < 1:
                bot.send_message(message.from_user.id, f'Сожалеем, город {user.city} не найден!')
            else:
                markup_city = telebot.types.ReplyKeyboardMarkup(True, True)
                for i in range(len(result)):
                    new_btn = telebot.types.KeyboardButton(f'{result[i][1]}')
                    markup_city.add(new_btn)
                message = bot.send_message(message.chat.id, "Выберите город!", reply_markup=markup_city)
                bot.register_next_step_handler(message, get_hotel, result)
        except ValueError:
            bot.send_message(message.from_user.id, 'Oшибка! Нужно ввести целое число. Давайте попробуем еще раз!')
            bot.register_next_step_handler(message, requests_city)
        logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, request_city. {user}')


@logger
def get_hotel(message: types.ReplyKeyboardMarkup, res: list) -> None:
    city: str = None
    user: object = User.get_user(message.chat.id)
    for index in range(len(res)):
        if res[index][1] == message.text:
            city = int(res[index][0])
            break
    else:
        bot.send_message(message.chat.id, 'Такого города нет в списке!')
        help_welcome(message)

    if city:
        arrival_date = []
        arrival_date.append(user.date_1), arrival_date.append(user.date_2)
        bot.send_message(message.chat.id, 'Ожидайте идет поиск, это не займет много времени!')
        if user.command == '/highprice' or user.command == '/lowprice':
            search_hotel = low_higth.search_hotels(city, arrival_date, int(user.count_hotel), user.command, user.money,
                                                   int(user.count_photo))
        else:
            search_hotel = bestdeal.search_hotels(city, arrival_date, int(user.count_hotel),
                                                  user.price, user.distance, user.money, user.count_photo)

        for dct in search_hotel:
            result: str = ''
            if isinstance(dct, dict):
                for info in dct:
                    if info != 'Photo':
                        result += f'{info}: {dct[info]}\n'
                bot.send_message(message.chat.id, result)
                media_group = list()
                try:
                    for info in dct:
                        if info == 'Photo':
                            for photo in dct[info]:
                                media_group.append(InputMediaPhoto(photo))
                            bot.send_media_group(message.chat.id, media_group)
                except Exception:
                    bot.send_message(message.chat.id, 'Ошибка загрузки фотографий.')
            else:
                for elem in dct:
                    bot.send_message(message.chat.id, elem)
    else:
        bot.send_message(message.chat.id, 'Ничего не найдено(((')
    bot.send_message(message.chat.id, "Поиск отелей завершен!")
    logging.info(f'Пользователь - {message.from_user.id} ввел сообщение: {message.text}, get_hotel. {user}')


if __name__ == '__main__':
    bot.infinity_polling(non_stop=True)
