import os
import sys
import time
import logging
from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv

from exceptions import ErrorMassage

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def check_tokens():
    """Функция check_tokens() проверяет доступность переменных окружения."""
    if not PRACTICUM_TOKEN:
        return 'Не передан токен PRACTICUM_TOKEN'
    if not TELEGRAM_TOKEN:
        return 'Не передан токен TELEGRAM_TOKEN'
    if not TELEGRAM_CHAT_ID:
        return 'Не передан токен TELEGRAM_CHAT_ID'


def send_message(bot, message):
    """Функция send_message() отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено')
    except telegram.TelegramError:
        logger.error('Не получилось отправить сообщение.')
        raise ErrorMassage('Ошибка при отправке сообщения в '
                                        'Telegram')


def get_api_answer(timestamp):
    """Функция get_api_answer() делает запрос к единственному эндпоинту
    API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS,
                                 params=payload)
        if homeworks.status_code != HTTPStatus.OK:
            raise requests.exceptions.HTTPError('Нет доступа.')
        else:
            return homeworks.json()
    except requests.RequestException:
        logger.error('Ошибка при запросе к эндпоинту.')


def check_response(response):
    """Функция check_response() проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Вы не привели данные в нужный формат.')
    if 'homeworks' not in response:
        raise KeyError('В запросе нет ключа "homeworks"')
    is_empty_homework = response['homeworks']
    if not isinstance(is_empty_homework, list):
        raise TypeError('Список пуст')
    return is_empty_homework


def parse_status(homework):
    """Функция parse_status() извлекает из информации о конкретной домашней
    работе статус этой работы. """
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('В запросе нет ключа "homework_name"')
    homework_status = homework.get('status')
    if not homework_status:
        raise KeyError('В запросе нет ключа "homework_status"')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Такого статуса нет в словаре HOMEWORK_VERDICTS')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is not None:
        logger.critical('Не все токены переданы! Бот упал.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = check_response(get_api_answer(timestamp))
            if len(response) > 0:
                message = parse_status(response[0])
                send_message(bot, message)
                logger.info('Статус домашки поменялся')
            else:
                logger.debug('Бот не смог отправить сообщение, так как '
                             'ничего нового нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, f'Сбой в работе программы: {error}')
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
