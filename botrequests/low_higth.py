import requests
import json
from typing import List, Iterator
from decouple import config
from requests.exceptions import Timeout, ConnectionError
from datetime import datetime

api_host = config("API_HOST")
api_key = config('API_KEY')
url = "https://hotels4.p.rapidapi.com/locations/v2/search"
url_hotels = "https://hotels4.p.rapidapi.com/properties/list"
url_photo = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
headers = {
    'x-rapidapi-host': api_host,
    'x-rapidapi-key': api_key
}


def search_city(city: str) -> list or str:
    """
    Функция находит ID Запрашиваемого Города.
    Возвращает список ID найденных городов или районов города.
    param: city Город который ввел пользователь.
    """

    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=15)
        data: dict = json.loads(response.text)
        id_city: list = data['suggestions'][0]['entities']
        total_list: list = []  # Список для хранения всех найденных городов

        for dct in id_city:
            list_city: list = []

            for name in dct:

                if name == 'destinationId':  # Получаем id города
                    list_city.append(dct[name])

                elif name == 'name':  # Получаем название города
                    list_city.append(dct[name])
            total_list.append(list_city)

        return total_list
    except (Timeout, ConnectionError, KeyError, IndexError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)}, search_city')
        return 'Вышло время запроса, или произошел сбой. Пожалуйста попробуйте еще раз!'


def search_hotels(id_city: int, date_lst: list, num_stop: int, command: str, money, count_photo=0) -> Iterator[dict]:
    """
    Функция для поиска отелей.
    В зависимости от команды пользователя отели сортируются по цене,
    либо с самых дешевых либо с самых дорогих.
    param: id_list - id города который выбрал пользователь.
    param: data_lst - дата приезда и отбытия.
    param: num_stop - Количество отелей которое нужно вывести.
    param: command - '/lowprice' или '/highprice', выбираем сортировку.
    param: count_photo - Количество фотографий которые необходимо вывести, если пользователь выбрал поиск с фото.
    param: money - В какой валюте будем выводить стоимость проживания.
    """
    sort: str = ''
    if command == '/lowprice':  # Для поиска дешевых отелей
        sort = "PRICE"
    elif command == '/highprice':  # Для поиска дорогих отелей
        sort = "PRICE_HIGHEST_FIRST"

    querystring: dict = {
                        "destinationId": id_city,
                        "pageNumber": "1",
                        "pageSize": "25",
                        "checkIn": date_lst[0],
                        "checkOut": date_lst[1],
                        "adults1": "1",
                        "sortOrder": sort,
                        "locale": "ru_RU",
                        "currency": money
                        }
    # Находим количество дней проживания.
    date_1 = int(''.join([digit for digit in str(date_lst[0]) if digit.isdigit()]))
    date_2 = int(''.join([digit for digit in str(date_lst[1]) if digit.isdigit()]))
    count_day: int = date_2 - date_1
    try:
        response = requests.request("GET", url_hotels, headers=headers, params=querystring, timeout=(10, 60))
        hotels: dict = response.json().get('data').get('body').get('searchResults').get('results')

        for index in range(len(hotels)):
            hotels_info: dict = {}
            try:
                for elem in hotels[index]:
                    if elem == 'starRating':  # Рейтинг отеля
                        hotels_info.update({'Рейтинг': int(hotels[index]['starRating']) * '*'})

                    elif elem == 'address':  # Город и Адрес отеля
                        hotels_info.update({'Город': hotels[index]['address']['locality']})
                        if 'streetAddress' in hotels[index]['address']:
                            hotels_info.update({'Адрес': hotels[index]['address']['streetAddress']})

                    elif elem == 'landmarks':  # Расстояние от центра
                        hotels_info[hotels[index]['landmarks'][0]['label']] = \
                            hotels[index]['landmarks'][0]['distance']

                    elif elem == 'name':  # Название отеля
                        hotels_info.update({'Название отеля': hotels[index][elem]})

                    elif elem == 'ratePlan':  # Прейскурант проживания
                        hotels_info.update(
                            {'Цена за все время проживания': hotels[index]['ratePlan']['price']['current']})
                        hotels_info.update({'Цена за сутки': round((hotels[index]['ratePlan']['price'][
                                                    'exactCurrent']) / count_day, 2)})

                    elif elem == 'id':  # Ссылка на отель
                        hotels_info.update(
                            {'Ссылка на отель': 'ru.hotels.com/ho{0}'.format(hotels[index]['id'])}
                        )
                        if count_photo > 0:  # Если нужны фотографии то отправляем на поиск фото
                            result = photo(count_photo, hotels[index]['id'])
                            hotels_info.update({'Photo': result})

            except (KeyError, TypeError, IndexError, AttributeError) as err:
                with open('logging.log', 'a') as file:  # Записываем ошибки в файл
                    file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')
                    # Если при поиске данных у отеля произошла ошибка то мы этот отель просто пропускаем.
                    continue

            # Для отправки результата используем генератор
            if len(hotels_info) > 0:
                yield hotels_info

            if index == num_stop - 1:  # Если количество найденных отелей равно запросу пользователя, останавливаем.
                return
    except (Timeout, ConnectionError) as err:  # Записываем ошибки в файл
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')

        yield 'Вышло время запроса, или произошел сбой. Пожалуйста попробуйте еще раз!'


def photo(count: int, id_hot: int) -> List[str]:
    """
    Функция для поиска фотографий.
    param: count Сколько фотографий вывести.
    param: id_hot: id отеля по которому ищем фотографии.
    """
    photo_list: list = []
    try:
        querystring: dict = {"id": id_hot}
        response = requests.request("GET", url_photo, headers=headers, params=querystring, timeout=(10, 60))
        data: dict = json.loads(response.content)
        data_loads: list = data['hotelImages']

        for i, photos in enumerate(data_loads):
            for elem in photos:

                if elem == 'baseUrl':
                    photo_list.append(photos['baseUrl'].format(size='z'))  # Заменяем чтобы получить фото.

            if i >= count - 1:  # Останавливаем если количество фото достигло нужного значения.
                break
        return photo_list

    except (Timeout, ConnectionError, IndexError, KeyError) as err:
        with open('logging.log', 'a') as file:  # Записываем ошибки в файл
            file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')
        return []
