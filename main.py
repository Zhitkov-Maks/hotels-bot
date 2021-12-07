from telebot import types
import lowprice
import telebot
import re

token = "2129959600:AAHaQj719Z-rkkLf9AVNEH6OIy2pEfNnZIk"
bot = telebot.TeleBot(token)
city = ''
arrival_data = []
count = ''
photo = ''
temp_command = ''
count_photo = 0
result = []


@bot.message_handler(commands=['start', 'hello_world'])
def start_welcome(message):
    """Функция приветствия."""
    bot.send_message(message.from_user.id, 'Добро пожаловать в телеграмм бот по поиску отелей. Чтобы узнать список '
                                           'поддерживаемых команд введите /help. ')


@bot.message_handler(commands=['help'])
def help_welcome(message):
    """Функция вывода доступных команд."""
    bot.send_message(message.from_user.id, "Список команд"
                                           "\n/lowprice - Вывод самых дешёвых отелей."
                                           "\n/highprice - Вывод самых дорогих отелей."
                                           "\n/bestdeal - Вывод отелей, наиболее подходящих по цене и "
                                           "расположению от центра. "
                                           "\n/history - Вывод истории поиска отелей."
                                           "\n/restart - Перезапуск бота.")


@bot.message_handler(commands=['lowprice', 'highprice'])
def city_input(message: types.Message):
    """
    Функция запрашивает город где искать отели.
    """
    global temp_command  # Запоминает какие отели искать, самые дешевые или самые дорогие.
    temp_command = message.text
    bot.send_message(message.from_user.id, 'Введите город: ')
    bot.register_next_step_handler(message, date_arrival)


@bot.message_handler(commands=['bestdeal'])
def bestdeal_city(message: types.Message):
    bot.send_message(message.from_user.id, 'Здесь пока ничего нет((')
    message.text = '/help'
    help_welcome(message)


@bot.message_handler(commands=['history'])
def history(message: types.Message):
    bot.send_message(message.from_user.id, 'Тут тоже пока что пусто((')
    message.text = '/help'
    help_welcome(message)


@bot.message_handler(commands=['restart'])
def restart(message: types.Message):
    message.text = '/start'
    start_welcome(message)


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, 'Команда не найдена! Вот список доступных команд.')
    message.text = '/help'
    help_welcome(message)


def date_arrival(message: types.Message):
    """
    Функция запрашивает дату прибытия и отбытия из отеля.
    """
    global city
    city = message.text
    bot.send_message(message.from_user.id,
                     'Введите дату приезда и дату выезда в формате ГГГГ-ММ-ДД(через пробел): ')
    bot.register_next_step_handler(message, get_count_city)


def get_count_city(message: types.Message):
    """
    Функция запрашивает кол-во отелей для вывода.
    """
    global arrival_data
    arrival_data = message.text
    arrival_data = re.findall(r'[2][0][2][1-9]-[0-1][1-9]-[0-3][0-9]', arrival_data)
    bot.send_message(message.from_user.id, 'Сколько отелей показать (Максимум 10)?')
    bot.register_next_step_handler(message, total_check)


def total_check(message: types.Message):
    """
    Функция проверяет введенные ранее данные и запрашивает нужны ли фотографии
    """
    global count
    count = message.text
    data_one = arrival_data[0].split('-')
    data_two = arrival_data[1].split('-')
    check = True
    for i in range(3):
        if data_one[i] > data_two[i]:
            check = False
    if len(city) < 3 or len(arrival_data) < 2 or int(count) > 10 or not check:
        bot.send_message(message.from_user.id, 'Введенные данные не прошли проверку, будьте внимательней '
                                               'и попробуйте еще раз.')
        # Надо еще придумать как проверить дату на корректность по отношению к сегодняшнему дню
        message.text = '/help'
        help_welcome(message)
    else:
        bot.send_message(message.from_user.id, 'Фотографии нужны? (да/нет).')
        # хотел сделать инлайн клавиатуру но не смог реализовать нажатие на кнопку нет
        bot.register_next_step_handler(message, get_photo)


def get_photo(message: types.Message):
    """Функция спрашивает сколько фотографий необходимо запросить?"""
    if message.text.lower() == 'да':
        bot.send_message(message.from_user.id, 'Сколько фотографий. Максимум 20.')
        bot.register_next_step_handler(message, requests_city)
    elif message.text.lower() == 'нет':
        message.text = 0
        requests_city(message)


def requests_city(message: types.Message) -> None:
    """Функция поиска города."""
    global count_photo
    global result
    count_photo = int(message.text)
    if count_photo > 20:
        bot.send_message(message.from_user.id, 'Ваше количество превышает максимально допустимое. Будет показано 20'
                                               'фотографий')
        count_photo = 20

    result = lowprice.search_city(city)
    if len(result) < 1:
        bot.send_message(message.from_user.id, f'Сожалеем, город {city} не найден!')
    else:
        question = 'Выберите город!'
        keyboard = types.InlineKeyboardMarkup()
        if len(result) == 1:
            one = types.InlineKeyboardButton(text=f'{result[0][1]}', callback_data='one')
            keyboard.add(one)
        elif len(result) == 2:
            one = types.InlineKeyboardButton(text=f'{result[0][1]}', callback_data='one')
            keyboard.add(one)
            two = types.InlineKeyboardButton(text=f'{result[1][1]}', callback_data='two')
            keyboard.add(two)
        elif len(result) >= 3:
            one = types.InlineKeyboardButton(text=f'{result[0][1]}', callback_data='one')
            keyboard.add(one)
            two = types.InlineKeyboardButton(text=f'{result[1][1]}', callback_data='two')
            keyboard.add(two)
            three = types.InlineKeyboardButton(text=f'{result[2][1]}', callback_data='three')
            keyboard.add(three)
        bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def request_hotel(call: types):
    """Функция поиска отелей"""
    res = ''
    if call.data == 'one':
        res = result[0][0]
    elif call.data == 'two':
        res = result[1][0]
    elif call.data == 'three':
        res = result[2][0]

    search_hotel = lowprice.search_hotels(res, arrival_data, int(count), temp_command, int(count_photo))
    hotel_string = ''
    bot.send_message(call.message.chat.id, 'Ожидайте идет поиск......')
    for elem in search_hotel:
        for two_elem in elem:
            if isinstance(two_elem, str):
                hotel_string += two_elem + ' / '
        bot.send_message(call.message.chat.id, hotel_string)
        hotel_string = ''
        for three_elem in elem:
            if isinstance(three_elem, list):
                for hotel_photo in three_elem:
                    bot.send_photo(call.message.chat.id, hotel_photo)
    bot.send_message(call.message.chat.id, "Поиск отелей завершен!")


bot.infinity_polling()
