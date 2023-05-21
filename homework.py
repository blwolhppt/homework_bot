import os
import sys
import time
import logging

import requests
import telegram
from dotenv import load_dotenv

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
logger.setLevel(logging.DEBUG)


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    if not PRACTICUM_TOKEN:
        return 'Не передан токен PRACTICUM_TOKEN'
    if not TELEGRAM_TOKEN:
        return 'Не передан токен TELEGRAM_TOKEN'
    if not TELEGRAM_CHAT_ID:
        return 'Не передан токен TELEGRAM_CHAT_ID'


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено.')
    except Exception:
        logger.error('Не получилось отправить сообщение.')
        raise Exception('Ошибка при отправлении сообщения.')


def get_api_answer(timestamp):
    """Функция делает запрос к эндпоинту API-сервиса."""
    payload = {'from_date': 1549962000}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS,
                                 params=payload)
    except Exception:
        raise Exception('Ошибка при запросе к эндпоинту.')
    if homeworks.status_code != 200:
        logger.error('Недоступно')
        raise requests.exceptions.HTTPError('Нет доступа.')
    return homeworks.json()


def check_response(response):
    """Функция проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Вы не привели данные в нужный формат.')
    if 'homeworks' not in response:
        raise KeyError('В запросе нет ключа "homeworks"')
    list_homework = response['homeworks']
    if not isinstance(list_homework, list):
        raise TypeError('Список пуст')
    return list_homework


def parse_status(homework):
    """Функция извлекает статус домашней работы."""
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
            response = get_api_answer(timestamp)
            list_homeworks = check_response(response)
            if list_homeworks:
                response_homework, *trash_response = list_homeworks
                message = parse_status(response_homework)
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
