class User:
    """"
    Класс юзер. Сохраняет введенные пользователем данные
    """
    user_dict = dict()

    def __init__(self):
        self.city = None
        self.count_photo = None
        self.count_hotel = None
        self.command = None
        self.data_1 = None
        self.data_2 = None
        self.result = None
        self.distance = None
        self.price = []

    @classmethod
    def get_user(cls, id_user):
        """
        Метод для получения пользователя
        """
        if id_user in User.user_dict:
            user = User.user_dict[id_user]
        else:
            user = User()
            User.user_dict[id_user] = user
        return user
