import requests
import json
from typing import List, Iterator
from datetime import datetime
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


def search_city(city: str) -> List[list]:
    """
    Функция находит ID Запрашиваемого Города.
    Возвращает список ID найденных городов или районов города.
    param city: Город который ввел пользователь
    param return: id_lst
    """

    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=15)
        data: dict = json.loads(response.text)
        id_city: list = data['suggestions'][0]['entities']
        total_list: list = []
        for dct in id_city:
            list_city: list = []
            for name in dct:
                if name == 'destinationId':
                    list_city.append(dct[name])
                elif name == 'name':
                    list_city.append(dct[name])
            total_list.append(list_city)
        return total_list
    except (TimeoutError, ConnectionError, KeyError, IndexError):
        return []


def search_hotels(id_city: int, data_lst: list, num_stop: int, command: str, money, count_photo=0) -> Iterator:
    """
    Функция для поиска отелей.
    В зависимости от команды пользователя отели сортируются по цене,
    либо с самых дешевых либо с самых дорогих.
    param id_list: id города который выбрал пользователь.
    param data_lst: дата приезда и отбытия.
    param num_stop: Количество отелей которое нужно вывести.
    param command: '/lowprice' или '/highprice', выбираем сортировку.
    param count_photo: Количество фотографий которые необходимо вывести, если пользователь выбрал поиск с фото.
    """
    sort: str = ''
    if command == '/lowprice':
        sort = "PRICE"
    elif command == '/highprice':
        sort = "PRICE_HIGHEST_FIRST"

    querystring: dict = {"destinationId": id_city, "pageNumber": "1", "pageSize": "25", "checkIn": data_lst[0],
                         "checkOut": data_lst[1], "adults1": "1", "sortOrder": sort, "locale": "ru_RU",
                         "currency": money}
    try:
        response = requests.request("GET", url_hotels, headers=headers, params=querystring, timeout=25)
        hotels: dict = response.json().get('data').get('body').get('searchResults').get('results')
        for index in range(len(hotels)):
            hotels_info: dict = {}
            for elem in hotels[index]:
                try:
                    if elem == 'starRating':
                        hotels_info.update({'Star': int(hotels[index]['starRating']) * '*'})
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
                        hotels_info.update({'Цена за все время проживания': hotels[index]['ratePlan']['price']['current']})
                    elif elem == 'id' and count_photo > 0:
                        result = photo(count_photo, hotels[index]['id'])
                        hotels_info.update({'Photo': result})
                except (TypeError, IndexError, KeyError, AttributeError):
                    pass
            yield hotels_info
            if index == num_stop - 1:
                return
    except (TimeoutError, ConnectionError, KeyError, IndexError):
        return ['Ошибка запроса либо вышло время ожидания запроса!']


def photo(count: int, id_hot: int) -> List[str]:
    """
    Функция для поиска фотографий.
    param count: Сколько фотографий вывести.
    param id_hot: id отеля по которому ищем фотографии.
    """
    photo_list: list = []
    try:
        querystring: dict = {"id": id_hot}
        response = requests.request("GET", url_photo, headers=headers, params=querystring, timeout=15)
        data = json.loads(response.content)
        data_loads: list = data['hotelImages']
        for i, photos in enumerate(data_loads):
            for elem in photos:
                if elem == 'baseUrl':
                    photo_list.append(photos['baseUrl'].format(size='z'))
            if i >= count - 1:
                break
        return photo_list
    except (TimeoutError, ConnectionError, IndexError, KeyError):
        photo_list.append({'Photo': 'Не найдено!'})
