class CustomErrorSendMessage(Exception):
    """Исключение на случай ошибки.
    отправляния сообщения в Telegram чат.
    """
    pass
class CustomErrorGetApiAnswer(Exception):
    """Исключение на случай ошибки.
    преобразования формата JSON к типам данных Python.
    """
    pass
