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
from botrequests import history_bd
import re
import sqlite3
import time

# Записываем логи в файл, и выводим в консоль.
file_log = logging.FileHandler('Log.log', encoding='utf-8')
console_out = logging.StreamHandler()

logging.basicConfig(handlers=(file_log, console_out),
                    format='[%(asctime)s | %(levelname)s]: %(message)s',
                    datefmt='%m.%d.%Y %H:%M:%S',
                    level=logging.INFO)

bot_token = config('TOKEN')
bot = telebot.TeleBot(bot_token)
history_bd.create_tables()


def logger(func: Callable) -> Callable:
    """"Декоратор для обработки ошибок."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result: callable(func) = func(*args, **kwargs)
            return result
        except (TypeError, ValueError, AttributeError, IndexError, NameError) as err:
            message = args[0]
            bot.send_message(message.chat.id, 'Извините, произошла ошибка, попробуйте еще раз.')
            help_welcome(message)
            with open('logging.log', 'a') as file:
                file.write(f'\n{datetime.now()}; {type(err)}; {func.__name__}.')
    return wrapper


@bot.message_handler(commands=['start', 'hello-world'])
def start_welcome(message):
    """Функция приветствия, реагирует на команды ('start', 'hello_world')"""
    user = User.get_user(message.from_user.id)  # Получаем пользователя
    bot.send_message(message.from_user.id, 'Здравствуйте, я телеграмм бот для поиска отелей и я помогу найти вам '
                                           'отель по вашим предпочтениям. Чтобы узнать что я умею введите'
                                           ' /help. ')
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@bot.message_handler(commands=['help'])
def help_welcome(message) -> types.Message:
    """Функция вывода доступных команд."""
    user: object = User.get_user(message.from_user.id)  # Получаем пользователя
    bot.send_message(message.chat.id, "Список доступных команд: "
                                      "\n/lowprice - Вывод самых дешёвых отелей."
                                      "\n/highprice - Вывод самых дорогих отелей."
                                      "\n/bestdeal - Вывод отелей, наиболее подходящих по цене и "
                                      "расположению от центра. "
                                      "\n/history - Вывод истории поиска отелей."
                                      "\n/money - В какой валюте будем искать отели?")
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
@bot.message_handler(content_types='text')
def command_input(message: types.Message) -> types.Message:
    """Функция обрабатывает любой текст кроме команд ('/start', '/hello_world', /help)
    Если введены команды для поиска отелей, то сразу запрашивает город."""
    user: object = User.get_user(message.from_user.id)  # Получаем пользователя
    user.command = message.text

    if message.text == "/lowprice" or message.text == "/highprice" or message.text == '/bestdeal':
        bot.send_message(message.chat.id, 'Введите город: ')
        bot.register_next_step_handler(message, date_travel)

    elif message.text == '/history':  # Cоздаем replay клавиатуру для истории
        history = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        history.add(types.KeyboardButton("Показать"), types.KeyboardButton("Очистить"), types.KeyboardButton('Отмена'))
        message = bot.send_message(message.chat.id, "Выберите, что нужно сделать?", reply_markup=history)
        bot.register_next_step_handler(message, get_history)

    elif message.text == '/money':  # Cоздаем replay клавиатуру для выбора валюты
        money = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        money.add(types.KeyboardButton("В рублях"), types.KeyboardButton("В долларах"), types.KeyboardButton('Отмена'))
        message = bot.send_message(message.chat.id, "В какой валюте искать отели?", reply_markup=money)
        bot.register_next_step_handler(message, get_money)

    else:
        bot.send_message(message.chat.id, 'Команда не найдена, видимо вы что-то не так ввели!')
        help_welcome(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_history(message: types) -> types.Message:
    """Функция для получения истории пользователя."""
    user: object = User.get_user(message.from_user.id)  # Получаем пользователя

    if message.text == 'Показать':  # Запрашиваем дату и команду
        history_date: list = history_bd.get_date(message.from_user.id)
        len_history: int = len(history_date)
        history_date: iter = iter(history_date)
        if not len_history:  # Если в истории ничего пока нет
            bot.send_message(message.chat.id, 'В вашей истории ничего пока нет.')

        else:  # Если история есть
            for _ in range(len_history):
                com_info: list = next(history_date)
                bot.send_message(message.chat.id, f'Команда: {com_info[0]}, дата: {com_info[1][:16]}')
                history_info = history_bd.get_info(message.from_user.id, com_info[1])  # Получаем историю.
                time.sleep(2)  # Притормаживаем работу, чтобы телеграмм не ругался.
                data_history = True  # На случай если по текущей команде нет никаких данных

                for info in history_info:
                    data_history = False
                    time.sleep(1)  # Притормаживаем работу, чтобы телеграмм не ругался.
                    bot.send_message(message.chat.id, f'{info[0]}', disable_web_page_preview=True)

                    if len(info[1]) != 0:  # Если в истории есть фотографии
                        photo: list = info[1].split('\n')
                        media_group: list = list()
                        try:  # На всякий случай
                            for elem in photo:
                                media_group.append(InputMediaPhoto(elem))
                            bot.send_media_group(message.chat.id, media_group)
                        except Exception as err:
                            with open('logging.log', 'a') as file:
                                file.write(f'\n{datetime.now()}, {type(err)} photo')

                if data_history:  # Если команда и дата были ни с чем не связаны
                    bot.send_message(message.chat.id, 'По этой команде данных не найдено.')
            bot.send_message(message.chat.id, 'Это все что я нашел!')

    elif message.text == 'Очистить':  # Очищаем базу для этого пользователя
        history_bd.clean(message.from_user.id)
        bot.send_message(message.chat.id, f'Ваша история стёрта!')
        help_welcome(message)

    elif message.text == 'Отмена':
        help_welcome(message)

    else:  # Если пользователь ввел что-то вручную.
        bot.send_message(message.chat.id, 'Команда не найдена, давайте попробуем еще раз!')
        help_welcome(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_money(message: types) -> types.Message:
    """Функция для выбора денежной еденицы для поиска."""
    user: object = User.get_user(message.from_user.id)  # Получаем пользователя
    if message.text.lower() == 'в рублях' or message.text.lower() == "в долларах":
        if message.text.lower() == 'в рублях':
            user.money = "RUB"
        elif message.text.lower() == "в долларах":
            user.money = "USD"
        bot.send_message(message.chat.id, "Успешно!, Давайте искать отели!")
        help_welcome(message)

    elif message.text == 'Отмена':
        help_welcome(message)

    else:  # Если пользователь ввел что-то вручную.
        bot.send_message(message.chat.id, "Неверный ввод, давайте попробуем еще раз!")
        help_welcome(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def date_travel(message: types.Message) -> types.Message:
    """Функция сохраняет введенный город, и направляет на ввод даты."""
    user: object = User.get_user(message.from_user.id)  # Получаем пользователя
    user.city = message.text
    user.date_1, user.date_2 = None, None
    if user.city.startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        bot.send_message(message.chat.id, 'Ошибка ввода города!')
        help_welcome(message)

    else:
        bot.send_message(message.chat.id, 'Сейчас нужно будет ввести дату предполагаемого заселения, а затем '
                                          'дату выезда.')
        start_calendar(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def start_calendar(message: types.KeyboardButton) -> types.KeyboardButton:
    """Запускаем Календарь."""
    calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
    bot.send_message(message.chat.id, f"Выберите: {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call: types.CallbackQuery) -> types.Message:
    """Выбираем дату в календаре."""
    res, key, step = DetailedTelegramCalendar(min_date=date.today()).process(call.data)
    if not res and key:
        bot.edit_message_text(f"Выберите: {LSTEP[step]}", call.message.chat.id, call.message.message_id,
                              reply_markup=key)
    elif res:
        bot.edit_message_text(f"Вы выбрали: {res}", call.message.chat.id, call.message.message_id)
        call.message.text = res
        get_date(call.message)


@logger
def get_date(message: types.Message) -> types.Message:
    """Записываем введенные даты.
    В зависимости от типа команды спрашиваем либо сколько отелей ищем, либо запрашиваем диапазон цен."""
    user = User.get_user(message.chat.id)  # Получаем пользователя
    if user.date_1 is None:  # Проверяем если даты нет, то отправляем еще раз на календарь.
        user.date_1: str = message.text
        start_calendar(message)
    else:  # Значит дата возвращается второй раз
        user.date_2: str = message.text
        date_1, date_2 = user.date_1, user.date_2
        # Проверяем не ввел ли пользователь вторую дату меньше чем первую.
        date_1: int = int(''.join([digit for digit in str(date_1) if digit.isdigit()]))
        date_2: int = int(''.join([digit for digit in str(date_2) if digit.isdigit()]))
        if date_1 >= date_2:
            bot.send_message(message.chat.id, 'Дата отезда не может быть раньше даты заселения, '
                                              'давайте попробуем еще раз.')
            user.date_1, user.date_2 = None, None
            start_calendar(message)

        elif date_1 < date_2 and (user.command == '/lowprice' or user.command == '/highprice'):
            bot.send_message(message.chat.id, 'Введите количество отелей (цифра) которое необходимо показать, '
                                              'максимально допустимое число 15!')
            bot.register_next_step_handler(message, get_photo)

        elif date_1 < date_2 and user.command == '/bestdeal':
            bot.send_message(message.chat.id, 'Введите диапазон цен для поиска (в формате: min-max)')
            bot.register_next_step_handler(message, get_distance)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_distance(message: types.Message) -> types.Message:
    """Запрашиваем на каком расстоянии от центра ищем отели."""
    if message.text.startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        help_welcome(message)

    else:
        user: object = User.get_user(message.from_user.id)  # Получаем пользователя
        user.price: list = re.findall(r'\d{2,6}', message.text)  # Вытаскиваем диапазон цен
        if len(user.price) != 2 or int(user.price[1]) <= int(user.price[0]):  # Проверяем на ошибки
            message.text: str = user.command
            bot.send_message(message.chat.id, 'Ошибка ввода, введите еще раз еще раз!')
            bot.register_next_step_handler(message, get_distance)

        else:  # Если все введено верно то спрашиваем дистанцию
            user.distance = None
            bot.send_message(message.chat.id, 'Введите до какого расстоянии от центра искать отели?')
            bot.register_next_step_handler(message, count_hotel)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def count_hotel(message: types.Message) -> types.Message:
    """Спрашиваем сколько отелей необходимо найти."""
    if message.text.startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        help_welcome(message)
    else:
        user: object = User.get_user(message.from_user.id)  # Получаем пользователя
        if not message.text.isdigit():  # Проверяем была ли введена цифра
            bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, count_hotel)

        else:  # Если все верно то спрашиваем сколько отелей нужно найти
            user.distance = message.text
            bot.send_message(message.chat.id, 'Введите количество отелей (цифра) которое необходимо показать, '
                                              'максимально допустимое число 15!')
            bot.register_next_step_handler(message, get_photo)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_photo(message: types.Message) -> types.ReplyKeyboardMarkup:
    """Функция проверяет введенные ранее данные и запрашивает нужны ли фотографии"""
    if message.text.startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        help_welcome(message)

    else:
        user: object = User.get_user(message.chat.id)  # Получаем пользователя
        user.count_hotel: int = message.text
        if not message.text.isdigit():  # Проверяем была ли введена цифра
            bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, get_photo)

        else:
            if int(user.count_hotel) > 15:  # Проверяем была ли введена допустимая цифра
                bot.send_message(message.from_user.id, "Ваше количество отелей больше 15, будет показано 15 отелей.")
                user.count_hotel = '15'
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
            message = bot.send_message(message.chat.id, "Показать Фото?", reply_markup=markup)
            bot.register_next_step_handler(message, count_photo)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def count_photo(message: types.ReplyKeyboardMarkup) -> types.Message:
    """Функция спрашивает сколько фотографий необходимо запросить?"""
    user: object = User.get_user(message.chat.id)  # Получаем пользователя
    if str(message.text).lower() == 'yes' or str(message.text).lower() == 'да':  #Если выбрано да
        bot.send_message(message.from_user.id, 'Сколько фотографий. Максимум 10.')
        bot.register_next_step_handler(message, requests_city)

    elif str(message.text).lower() == 'no' or str(message.text).lower() == 'нет':  #Если выбрано нет
        message.text = '0'
        requests_city(message)

    elif str(message.text).startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        help_welcome(message)

    else:  # Если пользователь ввел что-то не то вручную
        bot.send_message(message.chat.id, 'Вы что-то не то ввели, давайте попробуем еще раз!')
        message.text = user.count_hotel
        get_photo(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def requests_city(message: types.Message) -> types.Message:
    """Функция поиска города."""
    user: object = User.get_user(message.chat.id)  # Получаем пользователя

    if message.text.startswith('/'):  # На случай если пользователь решил начать делать что-нибудь заново.
        help_welcome(message)

    else:
        if message.text.isdigit():  # Проверяем была ли введена цифра
            user.count_photo = int(message.text)
            if user.count_photo > 10:  # Проверяем была ли введена допустимая цифра
                bot.send_message(message.from_user.id, 'Ваше количество превышает максимально допустимое. Будет показано 10'
                                                       'фотографий')
                user.count_photo = '10'
            result: list or str = low_higth.search_city(user.city)  # Поиск введенного города
            if isinstance(result, list) and len(result) < 1: # Если поиск закончился но ничего не найдено.
                bot.send_message(message.from_user.id, f'Сожалеем, город {user.city} не найден!')

            elif isinstance(result, str):  # Если поиск закончился ошибкой
                bot.send_message(message.chat.id, result)
                help_welcome(message)

            else:  # Если все прошло благополучно реализуем replay клавиатуру.
                markup_city = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                for i in range(len(result)):
                    markup_city.add(types.KeyboardButton(f'{result[i][1]}'))
                markup_city.add(types.KeyboardButton('Отмена'))
                message = bot.send_message(message.chat.id, "Выберите город!", reply_markup=markup_city)
                bot.register_next_step_handler(message, get_hotel, result)

        else:  # Если было введено не число, просим ввести заново.
            bot.send_message(message.chat.id, 'Oшибка! Нужно ввести целое число. Давайте попробуем еще раз!')
            bot.register_next_step_handler(message, requests_city)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_hotel(message: types.InlineKeyboardMarkup, res: list) -> types.Message:
    """Функция выводящая результаты поиска по выбранному городу."""
    city: str = None
    user: object = User.get_user(message.chat.id)
    if message.text.lower() == 'отмена':  # Если пользователь нажал отмену
        help_welcome(message)
    else:
        for index in range(len(res)):  # Находим город выбранный пользователем
            if res[index][1] == message.text:
                city = int(res[index][0])
                break
        else:
            bot.send_message(message.chat.id, 'Такого города нет в списке!')  # Если пользователь ввел что-то вручную.
            help_welcome(message)

        if city: # Если выбор города прошел удачно
            arrival_date = [user.date_1, user.date_2]  # Список с датами.
            bot.send_message(message.chat.id, 'Ожидайте идет поиск, это не займет много времени!')

            if user.command == '/highprice' or user.command == '/lowprice':  # Поиск в зависимости от команды.
                search_hotel = low_higth.search_hotels(city, arrival_date, int(user.count_hotel),
                                                       user.command, user.money, int(user.count_photo))
            else:
                search_hotel = bestdeal.search_hotels(city, arrival_date, int(user.count_hotel),
                                                      user.price, user.distance, user.money, int(user.count_photo))
            res_id = history_bd.write_users(message.from_user.id, user.command, datetime.now())

            count = True  # На случай если поиск не даст результата
            for dct in search_hotel:  # Итерируем генератор
                result, photo_bd = '', ''
                count = False
                if isinstance(dct, dict):  # Если возвращается словарь, значит поиск прошел без ошибок
                    for info in dct:  # Собираем информацию об отеле
                        if info != 'Photo':
                            result += f'{info}: {dct[info]}\n'

                        elif info == 'Photo':  # Собираем фотографии для записи в историю
                            photo_bd = '\n'.join(dct['Photo'])
                    history_bd.write_hotels(message.from_user.id, result, res_id, photo_bd)  # Запись истории
                    bot.send_message(message.chat.id, result, disable_web_page_preview=True)
                    media_group = list()

                    try:  # Добавил, так как были эксцессы с выбросом ошибок в данном цикле.
                        for info in dct:
                            if info == 'Photo':  # Группируем фото для телеграмма
                                for photo in dct[info]:
                                    media_group.append(InputMediaPhoto(photo))
                                bot.send_media_group(message.chat.id, media_group)
                    except Exception as err:
                        with open('logging.log', 'a') as file:
                            file.write(f'\n{datetime.now()}, {type(err)} photo')
                        bot.send_message(message.chat.id, 'Ошибка загрузки фотографий.')

                elif isinstance(dct, str):  # На случай если произошла ошибка при поиске отеле, возвращается
                    bot.send_message(message.chat.id, dct)  # сообщение об ошибке

            if count:  # Срабатывает если ничего не найдено
                bot.send_message(message.chat.id, 'Ничего не найдено, попробуйте еще раз!')

        bot.send_message(message.chat.id, "Поиск отелей завершен!")
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


if __name__ == '__main__':
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
