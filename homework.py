import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests import RequestException

load_dotenv()


PRACTICUM_TOKEN = os.getenv('token_practicum')
TELEGRAM_TOKEN = os.getenv('token_telegram')
TELEGRAM_CHAT_ID = os.getenv('chat_id_telegram')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
str_fmt = '[%(asctime)s] [%(levelname)s] > %(message)s'
date_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(fmt=str_fmt, datefmt=date_fmt)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Отправлено сообщение: {message}')
    except telegram.TelegramError:
        logger.error('Не удалось отправить сообщение.')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        status = response.status_code
        if status == HTTPStatus.OK:
            try:
                return response.json()
            except json.decoder.JSONDecodeError:
                logger.error(
                    'Ошибка преобразования формата JSON к типам данных Python')
        else:
            logger.error(
                f'Недоступность эндпоинта {ENDPOINT}. Код ответа API: {status}'
            )
            raise AssertionError
    except RequestException:
        logger.exception(f'Ошибка при запросе к эндпоинту {ENDPOINT}.')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        logger.error('Ответ API не является словарем.')
        raise TypeError

    if ('current_date' in response) and ('homeworks' in response):
        if type(response['homeworks']) is not list:
            logger.error('Ответ API не соответствует.')
            raise TypeError
        homeworks = response.get('homeworks')
        return homeworks
    else:
        logger.error('Ключи словаря не соответствуют ожиданиям.')
        raise KeyError


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней.
    работе статус этой работы.
    """
    if homework:
        homework_name = homework.get('homework_name')
        if not homework_name:
            logger.error(f'отсутствует или пустое поле: {homework_name}')
            raise KeyError
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            logger.error(f'Неизвестный статус: {homework_status}')
            raise KeyError
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logger.error('Пустой словарь')
        raise KeyError


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('новые статусы в ответе отсутствуют')
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
