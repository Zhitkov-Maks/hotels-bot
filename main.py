import functools
import logging
from datetime import date, datetime
from typing import Union, Callable
import re
import time

import telebot
from decouple import config
from telebot import types
from telebot.types import InputMediaPhoto
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

from botrequests import low_higth, bestdeal, history_bd
from users import User


# Записываем логи в файл, и выводим в консоль.
file_log = logging.FileHandler('Log.log', encoding='utf-8')
console_out = logging.StreamHandler()

logging.basicConfig(handlers=(file_log, console_out),
                    format="%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s)."
                           "%(funcName)s(%(lineno)d) - %(message)s", level=logging.INFO)

bot_token = config('TOKEN')
bot = telebot.TeleBot(bot_token)
history_bd.create_tables()


def logger(func: Callable) -> Callable:
    """"Декоратор для обработки ошибок."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Callable:
        try:
            result: callable(func) = func(*args, **kwargs)
            return result
        except (TypeError, ValueError, AttributeError, IndexError, NameError) as err:
            message = args[0]
            bot.send_message(message.chat.id, 'Извините, произошла ошибка, попробуйте еще раз.')
            menu(message)
            with open('logging.log', 'a') as file:
                file.write(f'\n{datetime.now()}; {type(err)}; {func.__name__}.')
    return wrapper


@bot.message_handler(commands=['start', 'hello-world'])
def start_welcome(message: types.Message) -> None:
    """Функция приветствия, реагирует на команды ('start', 'hello_world')"""
    bot.send_message(message.chat.id, 'Здравствуйте, я телеграмм бот для поиска отелей и я помогу найти вам '
                                      'отель по вашим предпочтениям. Чтобы узнать что я умею введите'
                                      ' /help. ')
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@bot.message_handler(commands=['help'])
def menu(message: types.Message) -> None:
    """Функция вывода доступных команд."""
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
def command_input(message: types.Message) -> None:
    """Функция обрабатывает любой текст кроме команд ('/start', '/hello_world', /help)
    Если введены команды для поиска отелей, то сразу запрашивает город."""
    user = User.get_user(message.from_user.id)
    user.command = message.text
    if message.text == "/lowprice" or message.text == "/highprice" or message.text == '/bestdeal':
        bot.send_message(message.chat.id, 'Введите город: ')
        bot.register_next_step_handler(message, date_travel)

    elif message.text == '/history':
        history = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        history.add(types.KeyboardButton("Показать"), types.KeyboardButton("Очистить"), types.KeyboardButton('Отмена'))
        message = bot.send_message(message.chat.id, "Выберите, что нужно сделать?", reply_markup=history)
        bot.register_next_step_handler(message, get_history)

    elif message.text == '/money':
        money = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        money.add(types.KeyboardButton("В рублях"), types.KeyboardButton("В долларах"), types.KeyboardButton('Отмена'))
        message = bot.send_message(message.chat.id, "В какой валюте искать отели?", reply_markup=money)
        bot.register_next_step_handler(message, get_money)

    else:
        bot.send_message(message.chat.id, 'Команда не найдена, видимо вы что-то не так ввели!')
        menu(message)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_history(message: types.Message) -> None:
    """
    Функция для получения истории пользователя. Сначала запрашиваем команду
    и дату, а затем по id пользователя и дате ищем информацию о найденных отелях.
    """
    if message.text == 'Показать':
        history_date: list = history_bd.get_date(message.from_user.id)
        # Если в истории ничего нет, то придет пустой список.
        if not len(history_date):
            bot.send_message(message.chat.id, 'В вашей истории ничего пока нет.')
            menu(message)
        # Если история есть, то запрашиваем и выводим информацию.
        else:
            for com_info in history_date:
                bot.send_message(message.chat.id, f'Команда: {com_info[0]}, дата: {com_info[1][:16]}')
                history_info = history_bd.get_info(message.from_user.id, com_info[1])
                # Притормаживаем работу, чтобы телеграмм не ругался.
                time.sleep(2)

                # На случай если по текущей команде нет никаких данных, используем булевы значения.
                data_history = True
                for info in history_info:
                    data_history = False
                    # Еще раз притормаживаем работу, чтобы телеграмм не ругался.
                    time.sleep(1)
                    bot.send_message(message.chat.id, f'{info[0]}', disable_web_page_preview=True)
                    if len(info[1]) != 0:
                        photo: list = info[1].split('\n')
                        media_group: list = list()
                        try:
                            for elem in photo:
                                media_group.append(InputMediaPhoto(elem))
                            bot.send_media_group(message.chat.id, media_group)
                        except Exception as err:
                            with open('logging.log', 'a') as file:
                                file.write(f'\n{datetime.now()}, {type(err)} photo')

                # Если наш data_history так и остался True
                if data_history:
                    bot.send_message(message.chat.id, 'По этой команде данных не найдено.')
            bot.send_message(message.chat.id, 'Это все что я нашел!')
            menu(message)

    elif message.text == 'Очистить':
        history_bd.clean(message.from_user.id)
        bot.send_message(message.chat.id, f'Ваша история стёрта!')
        menu(message)
    elif message.text == 'Отмена':
        menu(message)
    else:
        bot.send_message(message.chat.id, 'Команда не найдена, давайте попробуем еще раз!')
        menu(message)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@logger
def get_money(message: types.Message) -> None:
    """Функция для выбора денежной единицы для поиска."""
    user = User.get_user(message.from_user.id)
    if message.text.lower() == 'в рублях' or message.text.lower() == "в долларах":
        if message.text.lower() == 'в рублях':
            user.money = "RUB"
        elif message.text.lower() == "в долларах":
            user.money = "USD"
        bot.send_message(message.chat.id, "Успешно!, Давайте искать отели!")
        menu(message)
    elif message.text == 'Отмена':
        menu(message)
    else:
        bot.send_message(message.chat.id, "Неверный ввод, давайте попробуем еще раз!")
        menu(message)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@logger
def date_travel(message: types.Message) -> None:
    """Функция сохраняет введенный город, и направляет на ввод даты."""
    user = User.get_user(message.from_user.id)
    user.city = message.text
    user.date_1, user.date_2 = None, None
    if user.city.startswith('/'):
        bot.send_message(message.chat.id, 'Ошибка ввода города!')
        menu(message)
    else:
        bot.send_message(message.chat.id, 'Сейчас нужно будет ввести дату предполагаемого заселения, а затем '
                                          'дату выезда.')
        start_calendar(message)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@logger
def start_calendar(message: types.Message) -> None:
    """Запускаем Календарь."""
    calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
    bot.send_message(message.chat.id, f"Выберите: {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call: types.CallbackQuery) -> None:
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
def get_date(message: types.Message) -> None:
    """Записываем введенные даты.
    В зависимости от типа команды спрашиваем либо сколько отелей ищем, либо запрашиваем диапазон цен."""
    user = User.get_user(message.chat.id)
    # Проверяем если даты нет, то отправляем еще раз на календарь, если есть то идем на проверку.
    if user.date_1 is None:
        user.date_1 = message.text
        start_calendar(message)
    else:
        user.date_2 = message.text
        date_1: str = user.date_1
        date_2: str = user.date_2
        # Проверяем не ввел ли пользователь вторую дату меньше чем первую.
        date_1: int = int(''.join([digit for digit in str(date_1) if digit.isdigit()]))
        date_2: int = int(''.join([digit for digit in str(date_2) if digit.isdigit()]))
        if date_1 >= date_2:
            bot.send_message(message.chat.id, 'Дата отъезда не может быть раньше даты заселения, '
                                              'давайте попробуем еще раз.')
            user.date_1, user.date_2 = None, None
            start_calendar(message)
        elif date_1 < date_2 and (user.command == '/lowprice' or user.command == '/highprice'):
            bot.send_message(message.chat.id, 'Введите количество отелей (цифра) которое необходимо показать, '
                                              'максимально допустимое число 15!')
            bot.register_next_step_handler(message, get_photo)
        elif date_1 < date_2 and user.command == '/bestdeal':
            bot.send_message(message.chat.id, f'Введите диапазон цен для поиска в формате: min-max({user.money})')
            bot.register_next_step_handler(message, get_distance)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@logger
def get_distance(message: types.Message) -> None:
    """Запрашиваем на каком расстоянии от центра ищем отели."""
    if message.text.startswith('/'):
        menu(message)
    else:
        # Вытаскиваем из строки диапазон цен и проверяем на корректность.
        user = User.get_user(message.from_user.id)
        user.price = re.findall(r'\d{2,6}', message.text)
        if len(user.price) != 2 or int(user.price[1]) <= int(user.price[0]):
            bot.send_message(message.chat.id, 'Ошибка ввода, введите еще раз еще раз!')
            bot.register_next_step_handler(message, get_distance)
        else:
            user.distance = None
            bot.send_message(message.chat.id, 'Введите до какого расстоянии от центра искать отели?')
            bot.register_next_step_handler(message, count_hotel)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def count_hotel(message: types.Message) -> None:
    """Спрашиваем сколько отелей необходимо найти."""
    if message.text.startswith('/'):
        menu(message)
    else:
        user = User.get_user(message.from_user.id)
        if not message.text.isdigit():
            bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, count_hotel)
        else:
            user.distance = message.text
            bot.send_message(message.chat.id, 'Введите количество отелей (цифра) которое необходимо показать, '
                                              'максимально допустимое число 15!')
            bot.register_next_step_handler(message, get_photo)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_photo(message: types.Message) -> None:
    """Функция проверяет введенные ранее данные и запрашивает нужны ли фотографии"""
    if message.text.startswith('/'):
        menu(message)
    else:
        user = User.get_user(message.chat.id)
        user.count_hotel = message.text
        if not message.text.isdigit():
            bot.send_message(message.chat.id, 'Ошибка ввода, нужно ввести целое число! Попробуйте еще раз!')
            bot.register_next_step_handler(message, get_photo)
        else:
            # Проверяем цифру на приемлемость, и реализуем replay клавиатуру.
            if int(user.count_hotel) > 15:
                bot.send_message(message.from_user.id, "Ваше количество отелей больше 15, будет показано 15 отелей.")
                user.count_hotel = '15'
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
            message = bot.send_message(message.chat.id, "Показать Фото?", reply_markup=markup)
            bot.register_next_step_handler(message, count_photo)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def count_photo(message: types.Message) -> None:
    """Функция спрашивает сколько фотографий необходимо запросить?"""
    user = User.get_user(message.from_user)
    if str(message.text).lower() == 'yes' or str(message.text).lower() == 'да':
        bot.send_message(message.chat.id, 'Сколько фотографий. Максимум 10.')
        bot.register_next_step_handler(message, requests_city)
    elif str(message.text).lower() == 'no' or str(message.text).lower() == 'нет':
        message.text = '0'
        requests_city(message)
    elif str(message.text).startswith('/'):
        menu(message)
    else:
        bot.send_message(message.chat.id, 'Вы что-то не то ввели, давайте попробуем еще раз!')
        message.text = user.count_hotel
        get_photo(message)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


@logger
def requests_city(message: types.Message) -> None:
    """Функция поиска города."""
    user = User.get_user(message.from_user.id)
    if message.text.startswith('/'):
        menu(message)
    else:
        if message.text.isdigit():
            user.count_photo = int(message.text)
            if user.count_photo > 10:
                bot.send_message(message.from_user.id,
                                 'Ваше количество превышает максимально допустимое. Будет показано 10 фотографий')
                user.count_photo = '10'
            # Отправляем на поиск города, введенного пользователем.
            result: Union[list or str] = low_higth.search_city(user.city)

            # Если поиск закончился но ничего не найдено, возвращается пустой список.
            if isinstance(result, list) and len(result) < 1:
                bot.send_message(message.from_user.id, f'Сожалеем, город {user.city} не найден!')
                menu(message)

            # Если поиск закончился ошибкой, то возвращается строка, которую и выводим пользователю.
            elif isinstance(result, str):
                bot.send_message(message.chat.id, result)
                menu(message)

            # Если все прошло благополучно реализуем replay клавиатуру.
            else:
                markup_city = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                for i in range(len(result)):
                    markup_city.add(types.KeyboardButton(f'{result[i][1]}'))
                markup_city.add(types.KeyboardButton('Отмена'))
                message = bot.send_message(message.chat.id, "Выберите город!", reply_markup=markup_city)
                bot.register_next_step_handler(message, get_hotel, result)
        else:
            bot.send_message(message.chat.id, 'Вы ошиблись, Нужно ввести целое число. Давайте попробуем еще раз!')
            bot.register_next_step_handler(message, requests_city)
    logging.info(f'ID user-{message.chat.id}; ввел - {message.text};')


@logger
def get_hotel(message: types.Message, res: list) -> None:
    """Функция выводящая результаты поиска по выбранному городу."""
    city: int = 0
    user = User.get_user(message.from_user.id)
    if message.text.lower() == 'отмена':
        menu(message)
    else:
        # Ищем город, который выбрал пользователь.
        for index in range(len(res)):
            if res[index][1] == message.text:
                city: int = int(res[index][0])
                break
        else:
            bot.send_message(message.chat.id, 'Такого города нет в списке!')
            menu(message)

        # Если город который выбрал пользователь найден, то отправляем на поиск с id этого города.
        if city:
            arrival_date = [user.date_1, user.date_2]
            bot.send_message(message.chat.id, 'Ожидайте идет поиск, это не займет много времени!')
            if user.command == '/highprice' or user.command == '/lowprice':
                search_hotel = low_higth.search_hotels(city, arrival_date, int(user.count_hotel),
                                                       user.command, user.money, int(user.count_photo))
            else:
                search_hotel = bestdeal.search_hotels(city, arrival_date, int(user.count_hotel),
                                                      user.price, user.distance, user.money, int(user.count_photo))
            res_id: int = history_bd.write_users(message.from_user.id, user.command, str(datetime.now()))

            count = True  # На случай если поиск не даст результата
            for dct in search_hotel:
                result, photo_bd = '', ''
                count = False
                # Если возвращается словарь, значит поиск прошел без ошибок, и можно выводить информацию.
                if isinstance(dct, dict):
                    for info in dct:
                        if info != 'Photo':
                            result += f'{info}: {dct[info]}\n'
                        elif info == 'Photo':  # Для истории
                            photo_bd = '\n'.join(dct['Photo'])
                    history_bd.write_hotels(message.from_user.id, result, res_id, photo_bd)
                    bot.send_message(message.chat.id, result, disable_web_page_preview=True)

                    media_group: list = list()
                    # Добавил try except, так как были эксцессы с выбросом ошибок в данном цикле.
                    try:
                        for info in dct:
                            if info == 'Photo':
                                for photo in dct[info]:
                                    media_group.append(InputMediaPhoto(photo))
                                bot.send_media_group(message.chat.id, media_group)
                    except Exception as err:
                        with open('logging.log', 'a') as file:
                            file.write(f'\n{datetime.now()}, {type(err)} photo')
                        bot.send_message(message.chat.id, 'Ошибка загрузки фотографий.')

                # На случай если произошла ошибка при поиске отеле, возвращается строка
                elif isinstance(dct, str):
                    bot.send_message(message.chat.id, dct)
            if count:
                bot.send_message(message.chat.id, 'Ничего не найдено, попробуйте еще раз!')
                menu(message)
        bot.send_message(message.chat.id, "Поиск отелей завершен!")
        menu(message)
    logging.info(f'ID user-{message.from_user.id}; ввел - {message.text};')


if __name__ == '__main__':
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
