import os
import sys
from datetime import time
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


# Проверяет доступность переменных окружения, которые необходимы для работы
# программы. Если отсутствует хотя бы одна переменная окружения —
# продолжать работу бота нет смысла.
def check_tokens():
    if not PRACTICUM_TOKEN:
        return 'Не передан токен PRACTICUM_TOKEN'
    if not TELEGRAM_TOKEN:
        return 'Не передан токен TELEGRAM_TOKEN'
    if not TELEGRAM_CHAT_ID:
        return 'Не передан токен TELEGRAM_CHAT_ID'


# Отправляет сообщение в Telegram чат, определяемый переменной окружения
# TELEGRAM_CHAT_ID. Принимает на вход два параметра:
# экземпляр класса Bot и строку с текстом сообщения.
def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


# Делает запрос к единственному эндпоинту API-сервиса.
# В качестве параметра в функцию передается временная метка.
# В случае успешного запроса должна вернуть ответ API,
# приведя его из формата JSON к типам данных Python.
def get_api_answer(timestamp):
    payload = {'from_date': 1549962000}
    homeworks = requests.get(ENDPOINT, headers=HEADERS,
                             params=payload).json()
    return homeworks


# Проверяет ответ API на соответствие документации из урока API сервиса
# Практикум.Домашка. В качестве параметра функция получает ответ API,
# приведенный к типам данных Python.
def check_response(response):
    if 'homeworks' not in response:
        raise KeyError('В запросе нет ключа "homeworks"')
    if not isinstance(response, dict):
        raise TypeError('Вы не привели данные в нужный формат.')
    return response['homeworks']


# Извлекает из информации о конкретной домашней работе статус этой работы.
# В качестве параметра функция получает только один элемент из списка домашних
# работ. В случае успеха, функция возвращает подготовленную для отправки
# в Telegram строку, содержащую один из вердиктов словаря HOMEWORK_VERDICTS
def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is not None:
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = check_response(get_api_answer(timestamp))
            if len(response) != 0:
                message = parse_status(response[0])
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
