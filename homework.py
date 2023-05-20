import os
import sys
from datetime import time
import time
import logging
from http import HTTPStatus

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
logger.setLevel(logging.INFO)


def check_tokens():
    if not PRACTICUM_TOKEN:
        return 'Не передан токен PRACTICUM_TOKEN'
    if not TELEGRAM_TOKEN:
        return 'Не передан токен TELEGRAM_TOKEN'
    if not TELEGRAM_CHAT_ID:
        return 'Не передан токен TELEGRAM_CHAT_ID'


def send_message(bot, message) -> None:
    try:
        logger.debug('Сообщение было отправлено')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error('Ошибка при отправке сообщения в Telegram')
        raise 'Ошибка при отправке сообщения в Telegram'


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS,
                                 params=payload)
        if homeworks.status_code != HTTPStatus.OK:
            raise requests.exceptions.HTTPError('Нет доступа.')
        else:
            return homeworks.json()
    except Exception as error:
        logger.error('Ошибка при запросе к эндпоинту.')


def check_response(response):
    if 'homeworks' not in response:
        raise KeyError('В запросе нет ключа "homeworks"')
    if not isinstance(response, dict):
        raise TypeError('Вы не привели данные в нужный формат.')
    return response['homeworks']


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
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
            if len(response) != 0:
                message = parse_status(response[0])
                send_message(bot, message)
            else:
                logger.debug('Бот не смог отправить сообщение, так как '
                             'ничего нового нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.critical(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
