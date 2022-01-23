class User:
    """"
    Класс юзер. Сохраняет введенные пользователем данные.
    city: Город введенный пользователем.
    count_photo: Количество фотографий которое необходимо показать.
    count_hotel: Количество отелей которое необходимо показать.
    command: Команда которую ввел пользователь.
    date_1, date_2: Дата приезда и отъезда.
    distance: Расстояние от центра города, до которого нужно вести поиск.
    price: Минимальная и максимальная цена для поиска.
    Класс хранит в себе словарь с пользователями.
    """
    user_dict: dict = dict()

    def __init__(self):
        self.city = None
        self.count_photo = None
        self.count_hotel = None
        self.command = None
        self.date_1 = None
        self.date_2 = None
        self.money = "RUB"
        self.distance = None
        self.price = []

    @classmethod
    def get_user(cls, id_user):
        """
        Метод для получения пользователя.
        Если пользователь существует в словаре, то возвращаем ссылку на него, если пользователя нет то
        создаем его и также возвращаем ссылку на пользователя.
        param id_user: ID Пользователя чата.
        """
        if id_user in User.user_dict:
            user = User.user_dict[id_user]
        else:
            user: object = User()
            User.user_dict[id_user] = user
        return user
