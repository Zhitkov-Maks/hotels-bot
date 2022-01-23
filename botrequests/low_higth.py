import requests
import json
from datetime import datetime
from typing import List, Union, Iterator
from requests.exceptions import Timeout, ConnectionError

from decouple import config


api_host = config("API_HOST")
api_key = config('API_KEY')
url = "https://hotels4.p.rapidapi.com/locations/v2/search"
url_hotels = "https://hotels4.p.rapidapi.com/properties/list"
url_photo = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
headers = {
    'x-rapidapi-host': api_host,
    'x-rapidapi-key': api_key
}


def search_city(city: str) -> Union[List[list] or str]:
    """
    Функция находит ID Запрашиваемого Города.
    Возвращает список ID и названий найденных городов или районов города.
    param: city Город который ввел пользователь.
    """

    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=15)
        data: dict = json.loads(response.text)
        id_city: list = data['suggestions'][0]['entities']
        # Проходимся по списку с полученным результатом и сохраняем id и название города в список.
        total_list: list = []
        for info in id_city:
            list_city: list = []
            for name in info:
                if name == 'destinationId':
                    list_city.append(info[name])
                elif name == 'name':
                    list_city.append(info[name])
            # Сохраняем все в общий список, в котором будут все найденные города.
            total_list.append(list_city)
        return total_list

    except (Timeout, ConnectionError, KeyError, IndexError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)}, search_city')
        return 'Вышло время запроса, или произошел сбой. Пожалуйста попробуйте еще раз!'


def search_hotels(id_city: int, date_lst: list, num_stop: int, command: str, money, count_photo=0) \
        -> Union[Iterator[dict], Iterator[str]]:
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
    # В зависимости от команды выбираем нужную сортировку.
    if command == '/lowprice':
        sort = "PRICE"
    elif command == '/highprice':
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

        # Проходимся по списку с найденными отелями и собираем нужную информацию.
        for index in range(len(hotels)):
            hotels_info: dict = {}
            try:
                for elem in hotels[index]:
                    if elem == 'starRating':
                        hotels_info.update({'Рейтинг': int(hotels[index]['starRating']) * '*'})

                    elif elem == 'address':
                        hotels_info.update({'Город': hotels[index]['address']['locality']})
                        if 'streetAddress' in hotels[index]['address']:
                            hotels_info.update({'Адрес': hotels[index]['address']['streetAddress']})

                    elif elem == 'landmarks':
                        hotels_info[hotels[index]['landmarks'][0]['label']] = \
                            hotels[index]['landmarks'][0]['distance']

                    elif elem == 'name':
                        hotels_info.update({'Название отеля': hotels[index][elem]})

                    elif elem == 'ratePlan':
                        hotels_info.update(
                            {'Цена за все время проживания': hotels[index]['ratePlan']['price']['current']})
                        hotels_info.update({'Цена за сутки': round((hotels[index]['ratePlan']['price'][
                                                    'exactCurrent']) / count_day, 2)})

                    elif elem == 'id':
                        hotels_info.update(
                            {'Ссылка на отель': 'ru.hotels.com/ho{0}'.format(hotels[index]['id'])}
                        )
                        # Если нужны фотографии, то отправляем в функцию photo для поиска фотографий.
                        if count_photo > 0:
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

            if index == num_stop - 1:
                return
    except (Timeout, ConnectionError) as err:
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
                    # Сейчас нам нужно заменить в найденной строке size, на букву(которая обозначает размер фото)
                    photo_list.append(photos['baseUrl'].format(size='z'))
            if i >= count - 1:
                break
        return photo_list

    except (Timeout, ConnectionError, IndexError, KeyError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')
        return []
