import requests
import json
from typing import List, Iterator
from datetime import datetime
from decouple import config
from requests.exceptions import Timeout, ConnectionError

api_host = config("API_HOST")
api_key = config('API_KEY')
url = "https://hotels4.p.rapidapi.com/locations/v2/search"
url_hotels = "https://hotels4.p.rapidapi.com/properties/list"
url_photo = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
headers = {
    'x-rapidapi-host': api_host,
    'x-rapidapi-key': api_key
}


def search_hotels(id_city: int, date_lst: list, num_stop: int, price: list, distance: int, money,
                  count_photo=0) -> GeneratorExit:
    """
    Функция для поиска отелей.
    Ищет отели в заданном ценовом диапазоне, а затем сортируется по удалению от центра.
    param id_list: id города который выбрал пользователь.
    param data_lst: дата приезда и отбытия.
    param price: Ценовой диапазон.
    param distance: Расстояние от центра города.
    param num_stop: Количество отелей которое нужно вывести.
    param count_photo: Количество фотографий которые необходимо вывести, если пользователь выбрал поиск с фото.
    """
    count = 0
    for page in range(1, 10):
        querystring: dict = {"destinationId": id_city,
                             "pageNumber": page,
                             "pageSize": "25",
                             "checkIn": date_lst[0],
                             "checkOut": date_lst[1],
                             "adults1": "1",
                             "priceMin": price[0],
                             "priceMax": price[1],
                             "sortOrder": "PRICE",
                             "locale": "ru_RU",
                             "currency": money}

        response = requests.request("GET", url_hotels, headers=headers, params=querystring, timeout=(25, 120))
        date_1 = int(''.join([digit for digit in str(date_lst[0]) if digit.isdigit()]))
        date_2 = int(''.join([digit for digit in str(date_lst[1]) if digit.isdigit()]))
        count_day = date_2 - date_1
        try:
            hotels: dict = response.json().get('data').get('body').get('searchResults').get('results')
            for index in range(len(hotels)):
                hotels_info = {}
                dist = hotels[index]['landmarks'][0]['distance'].split()
                dist_float = ''.join([i if i.isdigit() else i.replace(',', '.') for i in dist[0]])
                if float(dist_float) <= float(distance):
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
                                hotels_info.update({'Цена за все время проживания':
                                                    hotels[index]['ratePlan']['price']['current']})
                                hotels_info.update({'Цена за сутки':
                                                    round((hotels[index]['ratePlan']['price'][
                                                            'exactCurrent']) / count_day, 2)})
                            elif elem == 'id' and count_photo > 0:
                                result = photo(count_photo, hotels[index]['id'])
                                hotels_info.update({'Photo': result})
                        except (KeyError, TypeError, IndexError, AttributeError):
                            pass
                    count += 1
                    yield hotels_info
                if float(dist_float) > float(distance):
                    continue
                if count == num_stop:
                    return

        except (Timeout, ConnectionError):
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
        response = requests.request("GET", url_photo, headers=headers, params=querystring, timeout=(20, 60))
        data: dict = json.loads(response.content)
        data_loads: list = data['hotelImages']
        for i, photos in enumerate(data_loads):
            for elem in photos:
                if elem == 'baseUrl':
                    photo_list.append(photos['baseUrl'].format(size='z'))
            if i >= count - 1:
                break
        return photo_list
    except (Timeout, ConnectionError, IndexError, KeyError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)} photo')
        photo_list.append({'Photo': 'Не найдено!'})
        return photo_list
