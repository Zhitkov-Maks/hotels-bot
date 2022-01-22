import requests
import json
from typing import List, Union, Iterator
from datetime import datetime
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


def search_hotels(id_city: int, date_lst: list, num_stop: int, price: list, distance: int, money,
                  count_photo=0) -> Union[Iterator[dict], Iterator[str]]:
    """
    Функция для поиска отелей.
    Ищет отели в заданном ценовом диапазоне, а затем сортируется по удалению от центра.
    param: id_list id - города который выбрал пользователь.
    param: data_lst - дата приезда и отбытия.
    param: price - Ценовой диапазон.
    param: distance - Расстояние от центра города.
    param: num_stop - Количество отелей которое нужно вывести.
    param: count_photo - Количество фотографий которые необходимо вывести, если пользователь выбрал поиск с фото.
    """
    count = 0
    querystring: dict = {
        "destinationId": id_city,
        "pageNumber": '1',
        "pageSize": "25",
        "checkIn": date_lst[0],
        "checkOut": date_lst[1],
        "adults1": "1",
        "sortOrder": 'DISTANCE_FROM_LANDMARK',
        "priceMin": price[0],
        "priceMax": price[1],
        "locale": "ru_RU",
        "currency": money
    }

    response = requests.request("GET", url_hotels, headers=headers, params=querystring, timeout=(15, 60))
    # Ищем сколько дней будет проживать клиент.
    date_1 = int(''.join([digit for digit in str(date_lst[0]) if digit.isdigit()]))
    date_2 = int(''.join([digit for digit in str(date_lst[1]) if digit.isdigit()]))
    count_day = date_2 - date_1
    try:
        hotels: dict = response.json().get('data').get('body').get('searchResults').get('results')
        for index in range(len(hotels)):
            hotels_info = {}
            # Находим дистанцию до центра города, нужна чтобы отсеять ненужные значения
            dist: list = hotels[index]['landmarks'][0]['distance'].split()
            dist_float: str = ''.join([i if i.isdigit() else i.replace(',', '.') for i in dist[0]])

            # Продолжаем собирать результат пока расстояние от центра меньше чем ввел пользователь.
            if float(dist_float) <= float(distance):
                try:
                    # Собираем интересующую нас информацию
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
                            hotels_info.update({
                                'Цена за все время проживания': hotels[index]['ratePlan']['price']['current']
                            })
                            hotels_info.update({'Цена за сутки': round((hotels[index]['ratePlan']['price'][
                                'exactCurrent']) / count_day, 2)})

                        elif elem == 'id':
                            hotels_info.update(
                                {'Ссылка на отель': 'ru.hotels.com/ho{0}'.format(hotels[index]['id'])}
                            )
                            # Отправляем на поиск фото, если это нужно.
                            if count_photo > 0:
                                result = photo(count_photo, hotels[index]['id'])
                                hotels_info.update({'Photo': result})

                except (KeyError, TypeError, IndexError, AttributeError) as err:
                    with open('logging.log', 'a') as file:
                        file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')
                        # Если при поиске данных у отеля произошла ошибка то мы этот отель просто пропускаем.
                        continue

                count += 1
                # Для отправки результата используем генератор
                if len(hotels_info) > 0:
                    yield hotels_info

            if float(dist_float) > float(distance):
                # Так как у нас сортировка идет по дистанции он центра, то при достижении расстояния от центра
                # больше чем ввел пользователь дальнейший поиск не имеет смысла.
                return

            if count == num_stop:  # Если количество найденных отелей равно запросу пользователя, останавливаем.
                return

    except (Timeout, ConnectionError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)}, search_hotels')
        yield 'Вышло время запроса, или произошел сбой. Пожалуйста попробуйте еще раз!'


def photo(count: int, id_hot: int) -> List[str]:
    """
    Функция для поиска фотографий.
    param: count - Сколько фотографий вывести.
    param: id_hot - id отеля по которому ищем фотографии.
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
                    # Сейчас нам нужно заменить в найденной строке size, на букву(которая обозначает размер фото)
                    photo_list.append(photos['baseUrl'].format(size='z'))
            if i >= count - 1:
                break
        return photo_list

    except (Timeout, ConnectionError, IndexError, KeyError) as err:
        with open('logging.log', 'a') as file:
            file.write(f'\n{datetime.now()}, {type(err)} photo')
        return []
