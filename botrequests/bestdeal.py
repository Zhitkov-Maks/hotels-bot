import requests
import json
from typing import List, Iterator
from datetime import datetime
import functools
from typing import Callable
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


@logger
def search_city(city: str) -> List[list]:
    """
    Функция находит ID Запрашиваемого Города.
    :param city:
    :return: id_lst
    """

    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    response = requests.request("GET", url, headers=headers, params=querystring, timeout=15)
    data = json.loads(response.text)
    id_city = data.get('suggestions')[0].get('entities')
    total_list = []
    for dct in id_city:
        list_city = []
        for name in dct:
            if name == 'destinationId':
                list_city.append(dct[name])
            elif name == 'name':
                list_city.append(dct[name])
        total_list.append(list_city)
    if len(total_list) < 1:
        total_list.append('Извините, но мне не удалось найти такого города((')
    return total_list


@logger
def search_hotels(id_city: int, data_lst: list, num_stop: int, price: list, distance: float,
                  count_photo=0) -> Iterator:
    """
    Функция для поиска отелей.
    id_list: id города.
    data_lst: дата приезда и отбытия.
    num_stop: Количество отелей которое нужно вывести.
    command: '/lowprice' или '/highprice', выбираем сортировку.
    count_photo: Количество фотографий которые необходимо вывести.
    """
    hotels_info = {}
    total_list = []
    querystring = {"destinationId": id_city,
                   "pageNumber": "1",
                   "pageSize": "25",
                   "checkIn": data_lst[0],
                   "checkOut": data_lst[1],
                   "adults1": "1",
                   "priceMin": price[0],
                   "priceMax": price[1],
                   "sortOrder": "PRICE",
                   "locale": "ru_RU",
                   "currency": "RUB"}

    response = requests.request("GET", url_hotels, headers=headers, params=querystring, timeout=25)
    if response.status_code == 200:
        hotels = response.json().get('data').get('body').get('searchResults').get('results')
        for index in range(len(hotels)):
            hotels_info = {}
            dist = hotels[index]['landmarks'][0]['distance'].split()
            dist_float = ''.join([i if i.isdigit() else i.replace(',', '.') for i in dist[0]])
            if float(dist_float) <= float(distance):
                for elem in hotels[index]:
                    if elem == 'starRating':
                        hotels_info.update({'Star': int(hotels[index]['starRating']) * '*'})
                    elif elem == 'address':
                        hotels_info.update({'City': hotels[index]['address']['locality']})
                        if 'streetAddress' in hotels[index]['address']:
                            hotels_info.update({'Address': hotels[index]['address']['streetAddress']})
                    elif elem == 'landmarks':
                        hotels_info[hotels[index]['landmarks'][0]['label']] = \
                            hotels[index]['landmarks'][0]['distance']
                    elif elem == 'name':
                        hotels_info.update({'Name Hotel': hotels[index][elem]})
                    elif elem == 'ratePlan':
                        hotels_info.update({'Price': hotels[index]['ratePlan']['price']['current']})
                    elif elem == 'id' and count_photo > 0:
                        result = photo(count_photo, hotels[index]['id'])
                        hotels_info.update({'Photo': result})
                total_list.append(hotels_info)
            if index == num_stop - 1:
                break
            if float(dist_float) > float(distance):
                continue
    if response.status_code == 400:
        hotels_info.update({'Result': 'Сбой запроса!'})
        total_list.append(hotels_info)
    return total_list


@logger
def photo(count: int, id_hot: int) -> List[str]:
    """
    Функция для поиска фотографий.
    count: Сколько фотографий вывести.
    """
    querystring = {"id": id_hot}
    response = requests.request("GET", url_photo, headers=headers, params=querystring, timeout=25)
    data = json.loads(response.content)
    data_loads = data['hotelImages']
    photo_list = []
    for i, photos in enumerate(data_loads):
        for elem in photos:
            if elem == 'baseUrl':
                photo_list.append(photos['baseUrl'].format(size='z'))
        if i >= count - 1:
            break
    return photo_list
