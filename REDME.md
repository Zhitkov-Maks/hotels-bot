# Python_basic_diploma
**Телеграмм бот для поиска отелей. Version 1.0.0**
***
***

## Запуск скрипта на компьютере.
### Подготовка компьютера.
- Создаем виртуальное окружение в котором будем запускать скрипт.
- Скачиваем архив с файлами скрипта на компьютер.
- Распаковываем архив в папку с уже созданным виртуальным окружением.


### Подготовка ключей.

Для использования бота, нам понадобится предварительно создать бота,
и получить ТОКЕН, как это сделать можно почитать здесь 
*https://habr.com/ru/post/262247/*,
так же нам понадобится открытый API Hotels, который расположен на
сайте [rapidapi](http://rapidapi.com). 
Чтобы получить возможность работать с этим API, необходимо:
* Зарегистрироваться на сайте [rapidapi](http://rapidapi.com). 
* Перейти в API Marketplace → категория Travel → Hotels 
* (либо просто перейти по
прямой ссылке на документацию 
* [Hotels API Documentation](https://rapidapi.com/apidojo/api/hotels4/)).
* Нажать кнопку Subscribe to Test.
* Выбрать пакет который вы хотите использовать.

Затем в папке с нашим проектом создаем файл .env в котором прописываем:
* TOKEN = "*Ваш токен для телеграмм бота.*"
* API_HOST = "hotels4.p.rapidapi.com"
* API_KEY = "Ваш API Hotels"

### Установка необходимых библиотек в venv.
Чтобы скрипт запустился, нам нужно установить в наше виртуальное окружение 
все дополнительные библиотеки для python которые были использованы при написании этого бота.
Для это в терминале нужно ввести ***pip install -r requirements.txt***.
Теперь мы готовы запускать нашего бота. 
***

## Описание работы команд.
Для хранения данных введенных пользователем - используется класс User,
в самом классе у нас находится словарь с пользователями *user_dict*, ссылку на которых при 
необходимости мы возвращаем, если пользователя нет, то создаем нового с помощью
метода класса *get_user*. Объект *user* создается по id пользователя бота,
а именно *message.from_user.id*.

### /start или hello-world
Простые команды для приветствия пользователя, просто выводим сообщение
для пользователя.

### /lowprice
Команда для поиска отелей с сортировкой от самых дешевых к самым дорогим.

##### Принцип работы:
* Запрашиваем у пользователя город который необходимо найти, функция *command_input*,
и отправляем на ввод дат.
* Спрашиваем две даты, дату заселения и отъезда. Запрос дат реализован с помощью
inline календаря, в котором можно ввести даты только с даты текущей, что избавляет 
нас от лишних проверок.
* Далее в функции *get_date* мы проверяем на корректность ввода даты, то есть
чтобы введенная вторая дата, была не меньше первой. Если проверка дат прошла успешно, 
то спрашиваем у пользователя сколько отелей нужно показать, я поставил максимальное количество 
отелей для отображения 15, но можно поменять и на большее значение, если даты проверку не прошли, то
отправляем снова на ввод дат.
* Следующая функция по этой команде, у нас *get_photo*, в ней мы сначала проверяем
была ли введенная команда числом(целым), если нет то просим попробовать снова, 
и уточняем что ввод должен быть числом. Если же проверка пройдена благополучно,
то далее мы создаем replay клавиатуру, в которой пользователь может выбрать - 
искать отели с фотографиями или фотографии ему не нужны.
* Следующая точка у нас только при положительном ответе из предыдущей функции, 
*count_photo*, в которой мы спрашиваем сколько нужно фотографий пользователю для 
счастья, я установил максимальное количество в 10 фотографий, что при необходимости
можно легко изменить.
* В следующей функции *requests_city* мы проверяем введенное количество фотографий, 
и если все хорошо, то делаем запрос на поиск введенного города,
low_higth.search_city(user.city). В этом запросе нас интересует id города, ну и 
название(для пользователя) которые мы сохраняем в список(хотя возможно удобнее 
было бы использовать словарь), и сохраняется все в общем списке, потому что найтись 
могут и города с похожими названиями. 
* Далее мы в этой же функции реализуем replay клавиатуру для выбора пользователем
нужного ему значения, и добавляем выбор *отмены*, если пользователь передумал, или 
в результате нет нужного варианта.
* В следующей функции *get_hotel* мы организуем поиск отелей по введенным ранее
пользователем данным, и выбранным городом. *search_hotel = low_higth.search_hotels*
    * В зависимости от команды выбираем нужную сортировку, в нашем случае это - 
        *sort = "PRICE"*, и заполняем остальные параметры запроса, такие как даты, 
        id города, и в какой валюте будем искать(по умолчанию выбрано в рублях)
    * Установил timeout=(10, 60) для того чтобы пользователь долго не ждал.
    * После получения ответа, проходимся по списку с отелями и выбираем в них 
        интересующие нас данные. Если нужны фотографии, то сразу же отправляем в функцию
        *photo* с id города и количеством необходимых фотографий.
        * В этой функции можно выбрать размер фотографий, *(photos['baseUrl'].format(size='z'))*,
          при желании можно изменить, изменив букву 'z' на другие. ***({'suffix': 'z', 'type': 15},
                                       {'suffix': 'w', 'type': 17},
                                       {'suffix': 'y', 'type': 14},
                                       {'suffix': 'b', 'type': 3},
                                       {'suffix': 'n', 'type': 11},
                                       {'suffix': 'd', 'type': 13},
                                       {'suffix': 'e', 'type': 16},
                                       {'suffix': 'g', 'type': 12},
                                       {'suffix': 'l', 'type': 9},
                                       {'suffix': 's', 'type': 2},
                                       {'suffix': 't', 'type': 1}]})***
    * Отправляем сразу же найденные данные в виде словаря в основную программу, с помощью генератора.
* Вернувшиеся данные группируем, и выводим для пользователя.

### Команда /highprice
Команда для поиска отелей с сортировкой начиная с самых дорогих.
В этой команде алгоритм работы, точно такой же как и в /lowprice, поэтому подробно на ней мы
останавливаться не будем, уточним лишь отличие. Отличие заключается в выборе сортировки.
Здесь нам нужен режим сортировки *sort = "PRICE_HIGHEST_FIRST"*.

### Команда /bestdeal
Команда для поиска отелей по параметрам пользователя, а именно пользователь может выбрать
диапазон цен приемлемых для его кошелька, и максимальное расстояние от центра города,
в пределах которого он готов поселиться.
Общий алгоритм программы похож на предыдущие команды, только несколько другой 
порядок выполнения, из-за добавления двух пунктов.
#### Алгоритм работы:
* Ввод города -command_input;
* Ввод дат - date_travel -> inline календарь;
* Ввод диапазона цен - get_date, в виде минимум-максимум;
* Ввод расстояния от центра - get_distance;
* Ввод количества отелей для вывода - count_hotel;
* Выбор нужны ли фотографии - get_photo;
* Если нужны то сколько - count_photo;
* Поиск введенного города - requests_city;
* Поиск отелей - get_hotel.
#### Особенности работы: 
Главной отличительной особенностью является наличие двух дополнительных 
данных, которые нам нужно использовать при запросе и поиске отеля.
Я использовал сортировку в таком виде: *"sortOrder": 'DISTANCE_FROM_LANDMARK', 
"priceMin": price[0], "priceMax": price[1]*, получается запрос отсортирован с 
наименьшего расстояния от центра, и цены в пределах введенного диапазона.
И при поиске данных сразу же проверяю расстояние, если расстояние превышает максимально 
допустимое для пользователя, значит все что можно было найти найдено, и заканчиваем 
поиск.

### Команда /history

Команда для вывода истории пользователя.
Для хранения истории мы использовали базу данных sqlite3, так как она уже встроена
в библиотеку python. Все сохранение истории у нас происходит в последней функции, где
идет непосредственно поиск отелей. Для хранения мы используем две таблицы, *users* и 
*hotels*. Соединены таблицы по уникальному идентификатору id из таблицы users, в таблице 
hotels это id_com. При поиске истории мы сначала получаем по id пользователя чата телеграмм,
список с командами и датами, затем по id пользователя и дате находим оставшуюся информацию.
Пришлось при выводе истории замедлить вывод информации, так как телеграмм ругается, что слишком 
много запросов отправлено. Результат выводит последние 20 запросов, начиная с последнего, мне
кажется не слишком разумно продолжать выводить историю более этой, но при желании можно изменить
это в функции get_date в модуле history_bd.py, строка
*cur.execute("""SELECT command, date from users WHERE id_user = ? ORDER BY date DESC LIMIT 20""", (id_user,))*

### Команда /money:

Команда для изменения валюты для поиска, можно выбрать либо в рублях, либо в долларах. 
Реализована через replay клавиатуру. По умолчанию стоит поиск в рублях. Меняется с 
помощью добавления в user.money USD или RUB.

### Команда /help

Команда выводящая список доступных команд. Ничего интересного.