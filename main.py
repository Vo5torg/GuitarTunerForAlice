import logging
import json
from copy import deepcopy
from random import choice, shuffle
from flask import Flask, request
from cards import get_menu_card
from constants import *


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
sessionStorage = {}

CHOICE_DICT = {
    1: ['1', 'один', 'первый', 'первая', 'первое', 'первые', 'раз', 'однёрка'],
    2: ['2', 'два', 'второй', 'вторая', 'второе', 'вторые', 'двойка'],
    3: ['3', 'три', 'третий', 'третья', 'третье', 'третьи', 'тройка'],
    4: ['4', 'четыре', 'четвёртый', 'четвёртая', 'четвёртое', 'четвёртые', 'четвёрка',
          'четвертый', 'четвертая', 'четвертое', 'четверка', 'четвертые'],
    5: ['5', 'пять', 'пятый', 'пятая', 'пятое', 'пятые', 'пятёрка', 'пятерка'],
    6: ['6', 'шестёрка', 'шесть', 'шестой', 'шестая', 'шестое', 'шаха', 'шест']
}


@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    req = request.json
    handle_dialog(response, req)
    user_id = req['session']['user_id']
    res_text = response['response']['text']
    # Здесь учитываются все баги, когда какого-то ключа нет в реквесте
    if 'original_utterance' in req['request'] and req['request']['original_utterance'] != 'ping':
        log(user_id, req['request']['original_utterance'], res_text)
    elif 'command' in req['request'] and req['request']['command'] != 'ping':
        log(user_id, req['request']['command'], res_text)
    elif 'payload' in req['request']:
        log(user_id, req['request']['payload']['text'], res_text)
    return json.dumps(response)


# Вывод логов формата ID: запрос-ответ
def log(user_id, request, response):
    logging.info(f'{user_id[:5]}\nREQUEST: {request}\nRESPONSE: {response}\n----------------')


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req["request"].get("original_utterance", "") == 'ping':
        res['response']['text'] = 'Хватит пинговать с моего USER_ID, ты всё портишь.'
        return

    if req['session']['new']:
        sessionStorage[user_id] = {
            'state': STATE_HELLO
        }
        text = 'Салам гитаристам! Выбери орудие!'
        card, tts = get_menu_card(text)

        res['response']['text'] = text
        res['response']['card'] = card
        res['response']['tts'] = text + tts
        res['response']['buttons'] = []
    else:
        tokens = req['request']['nlu']['tokens']
        if not tokens:
            if 'payload' in req['request']:
                tokens = req['request']['payload']['text'].lower()
            else:
                tokens = req['request']['command'].lower()
        if user_id not in sessionStorage:
            sessionStorage[user_id] = {'state': STATE_HELLO}
        game_info = sessionStorage[user_id]

        if any(word in tokens for word in ['акустика', 'акустическая', 'кусты']):
            game_info['state'] = STATE_ACOUSTIC
            show_guitar(res, game_info)
        elif any(word in tokens for word in ['классика', 'классическая', 'обычная']):
            game_info['state'] = STATE_CLASSIC
            show_guitar(res, game_info)
        elif any(word in tokens for word in ['бас', 'басс', 'бочка', 'басовая', 'бас-гитара']):
            game_info['state'] = STATE_BAS
            show_guitar(res, game_info)
        elif any(word in tokens for word in ['электро', 'электроника', 'электрогитара']):
            game_info['state'] = STATE_ELECTRO
            show_guitar(res, game_info)
        elif any(word in tokens for word in ['помощь', 'помоги', 'как', 'подсказка']):
            res['response']['text'] = 'Текст помощи'
        elif any(word in tokens for word in ['умеешь', 'можешь']):
            res['response']['text'] = 'Что я умею'
        elif STATE_ACOUSTIC <= game_info['state'] <= STATE_ELECTRO:
            flag = 0
            for i in CHOICE_DICT:
                if any(word in tokens for word in CHOICE_DICT[i]):
                    flag = i
                    break

            if flag:
                game_info['string'] = flag
                res['response']['text'] = f'Воспроизвожу звук {flag} струны.'
                res['response']['tts'] = '<speaker audio="dialogs-upload/f3258314-b2a4-4dfd-92bc-ffe1d6b71de4/{}.opus">'\
                    .format(GUITARS[game_info["state"] - 1]["strings"][str(flag)]) * REPEATS
            else:
                if 'string' in game_info and any(word in req['request']['nlu']['tokens'] for word in
                        ['еще', 'ещё', 'повтори', 'повтори-ка',
                        'повтор', 'понял', 'слышал', 'услышал',
                        'расслышал', 'прослушал', 'скажи', 'а']):
                    i = game_info['string']
                    res['response']['text'] = f'Воспроизвожу звук {i} струны.'
                    res['response'][
                        'tts'] = '<speaker audio="dialogs-upload/f3258314-b2a4-4dfd-92bc-ffe1d6b71de4/{}.opus">' \
                                     .format(GUITARS[game_info["state"] - 1]["strings"][str(i)]) * REPEATS
                else:
                    res['response']['text'] = f'Выберите струну'

        elif any(word in tokens for word in [
            'выход', 'хватит', 'пока', 'свидания', 'стоп', 'выйти',
            'выключи', 'останови', 'остановить', 'отмена', 'закончить',
            'закончи', 'отстань', 'назад', 'обратно', 'верни', 'вернись'
        ]):
            res['response']['text'] = 'Пока'
            res['response']['end_session'] = True
        else:
            res['response']['text'] = 'Ты чё несёшь'

    add_default_buttons(res, req)


def show_guitar(res, game_info):
    res['response']['text'] = 'Выберите струну.'
    if 'string' in game_info:
        game_info.pop('string')
    for guitar in GUITARS:
        if guitar['state'] == game_info['state']:
            res['response']['buttons'] = [
                {
                    'title': s,
                    'hide': True
                } for s in guitar['strings']
            ]
            break


# Добавление прошлых кнопок, чтобы они не пропадали после неверного запроса
def add_default_buttons(res, req):
    user_id = req['session']['user_id']
    game_info = sessionStorage[user_id]

    if 'buttons' in res['response']:
        game_info['last_btns'] = deepcopy(res['response']['buttons'])
    else:
        res['response']['buttons'] = deepcopy(sessionStorage[user_id]['last_btns'])

    for button in ['Помощь', 'Что ты умеешь?']:
        button_dict = {'title': button, 'hide': True}
        if button_dict not in res['response']['buttons']:
            res['response']['buttons'].append(button_dict)