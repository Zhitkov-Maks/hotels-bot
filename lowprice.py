import requests
import json
from typing import List, Iterator
from datetime import datetime
import functools
from typing import Callable


def logger(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except TypeError:
            mistake = 'TypeError'
            with open('logging.log', 'a') as file:
                file.write(f'{datetime.now()}, {mistake}, {func.__name__}')
        except KeyError:
            mistake = 'KeyError'
            with open('logging.log', 'a') as file:
                file.write(f'{datetime.now()}, {mistake}, {func.__name__}')
        except IndexError:
            mistake = 'IndexError'
            with open('logging.log', 'a') as file:
                file.write(f'{datetime.now()}, {mistake}, {func.__name__}')

        return result
    return wrapper


@logger
def search_city(city: str) -> List[list]:
    """
    Функция находит ID Запрашиваемого Города.
    :param city:
    :return: id_lst
    """
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    headers = {
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        'x-rapidapi-key': "8531ae8c46msha45091982d8dda3p1f0a60jsnffd9b8784f03"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)

    data = json.loads(response.text)
    id_city = data['suggestions'][0]['entities']
    total_list = []
    for dct in id_city:
        list_city = []
        for name in dct:
            if name == 'destinationId':
                list_city.append(dct[name])
            elif name == 'name':
                list_city.append(dct[name])
        total_list.append(list_city)
    return total_list


@logger
def search_hotels(id_city: int, data_lst: list, num_stop: int, command, count_photo=0) -> Iterator:
    """
    Функция для поиска дешевых отелей без фото.
    id_list: id города.
    data_lst: дата приезда и отбытия.
    num_stop: Количество отелей которое нужно вывести.
    command: '/lowprice' или '/highprice', выбираем сортировку.
    count_photo: Количество фотографий которые необходимо вывести.
    """
    sort = ''
    if command == '/lowprice':
        sort = "PRICE"
    elif command == '/highprice':
        sort = "HighPRICE"

    url = "https://hotels4.p.rapidapi.com/properties/list"
    querystring = {"destinationId": id_city, "pageNumber": "1", "pageSize": "25", "checkIn": data_lst[0],
                   "checkOut": data_lst[1], "adults1": "1", "sortOrder": sort, "locale": "ru_RU", "currency": "RUB"}
    headers = {
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        'x-rapidapi-key': "8531ae8c46msha45091982d8dda3p1f0a60jsnffd9b8784f03"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    data_hotels = json.loads(response.text)

    hotels = data_hotels['data']['body']['searchResults']['results']
    for index in range(len(hotels)):
        hotels_info = []
        for elem in hotels[index]:
            if elem == 'address':
                if 'streetAddress' in hotels[index]['address']:
                    hotels_info.append(hotels[index]['address']['streetAddress'])
            elif elem == 'name':
                hotels_info.append(hotels[index][elem])
            elif elem == 'ratePlan':
                hotels_info.append(hotels[index]['ratePlan']['price']['current'])
            elif elem == 'id' and count_photo > 0:
                result = photo(count_photo, hotels[index]['id'])
                hotels_info.append(result)
        yield hotels_info
        if index == num_stop - 1:
            return


@logger
def photo(count: int, id_hot: int) -> List[str]:
    """
    Функция для поиска фотографий.
    count: Сколько фотографий вывести.
    """
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": id_hot}
    headers = {
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        'x-rapidapi-key': "8531ae8c46msha45091982d8dda3p1f0a60jsnffd9b8784f03"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
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
