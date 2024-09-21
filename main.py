import json
import requests
import telebot
from telebot import types
import sqlite3

GEOCODE_KEY = "3c696182-3c53-41e3-b481-8101f0451a48"
OGRANIZATION_KEY = "379ae701-2423-4bdb-9536-d21e1f86f8c4"
TOKEN = '7672536595:AAH8JYchr5Nd4MLI1ZZ1Ojy4IJGBHaF8XYE'
bot = telebot.TeleBot(TOKEN)


def json_file(response):
    file = open('data_json.json', 'w', encoding='utf8')
    json.dump(response.json(), file, ensure_ascii=False, indent=4)
    file.close()


def geocoder_find(toponym_to_find):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
    geocoder_params = {
        "apikey": GEOCODE_KEY,
        "geocode": toponym_to_find,
        "format": "json"}

    return requests.get(geocoder_api_server, params=geocoder_params)


def organization_find(toponym_to_find, lang, coords):
    organization_api_server = "https://search-maps.yandex.ru/v1/"
    ll = ','.join(coords)
    finder_params = {
        "apikey": OGRANIZATION_KEY,
        "text": toponym_to_find,
        "format": "json",
        "lang": lang,
        "ll": ll,
        "results": 50,
        "type": 'biz',
        "spn": '0.1,0.1'
    }

    return requests.get(organization_api_server, params=finder_params)


@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Отправить геопозицию' + chr(128205), request_location=True)
    markup.add(item1)
    bot.send_message(message.from_user.id, 'Здравствуйте! Для поиска ближайших спортивных объектов, введите адрес или '
                                           'отправьте геопозицию.',
                     reply_markup=markup)


@bot.message_handler(content_types=['location', 'text'])
def get_location(message):
    try:
        coords = [str(message.location.longitude), str(message.location.latitude)]
        toponym = ",".join(coords)
    except AttributeError:
        toponym = message.text
    response = geocoder_find(toponym)
    json_response = response.json()
    json_file(response)
    if not json_response['response']['GeoObjectCollection']['featureMember']:
        bot.send_message(message.from_user.id, 'Ошибка. Такого адреса не существует. Попробуйте ещё раз')
        bot.register_next_step_handler(message, get_location)
    else:
        ll = json_response['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos'].split()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton('Спортивный комплекс')
        item2 = types.KeyboardButton('Спортплощадка')
        item3 = types.KeyboardButton('Фитнес клуб')
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)

        bot.send_message(message.from_user.id, 'Укажите спортивный объект который хотите найти (выберите из '
                                               'предложенных вариантов или введите свой):',
                         reply_markup=markup)
        bot.register_next_step_handler(message, disabled, *ll)


def disabled(message, *ll):
    db_con = sqlite3.connect('statistic.db')
    cur = db_con.cursor()
    res = cur.execute(f'SELECT rate FROM main WHERE request = "{message.text.capitalize()}"').fetchall()
    if not res:
        cur.execute(f'INSERT INTO main (rate, request) VALUES    (?, ?)', (1, message.text.capitalize()))
    else:
        cur.execute(f'UPDATE main SET rate = {res[0][0] + 1} WHERE request = "{message.text.capitalize()}"')
    db_con.commit()

    data_for_find = message
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Да'))
    markup.add(types.KeyboardButton('Нет'))
    bot.send_message(message.from_user.id, 'Требуется ли инфраструктура для людей с ограниченными возможностями?',
                     reply_markup=markup)
    bot.register_next_step_handler(message, objects, *ll, data_for_find=data_for_find)


def objects(message, *ll, data_for_find):
    categories = ['fitness', 'sportcenter', 'stadium', 'playground']
    if not (message.text.lower() == 'да' or message.text.lower() == 'нет'):
        bot.send_message(message.from_user.id, 'Некорректный ответ, попробуйте ещё раз')
        bot.register_next_step_handler(message, objects, *ll, data_for_find=data_for_find)
    else:
        lang = data_for_find.from_user.language_code
        response = organization_find(data_for_find.text, lang, ll)
        json_file(response)
        json_response = response.json()
        list_of_objects = []
        results = json_response['properties']['ResponseMetaData']['SearchResponse']['found']
        if results > 50:
            results = 50
        for i in range(results):
            disabled_inf = []
            base = json_response['features'][i]
            for k in base['properties']['CompanyMetaData']['Categories']:
                if 'Зеленоград' in base['properties']['CompanyMetaData']['address']:
                    try:
                        if k["class"] in categories:
                            try:
                                disabled_base = base['properties']['CompanyMetaData']['Features']
                                for j in disabled_base:
                                    if (type(j['value']) == list and 'доступно' in j['value']['name']) or j['value'] == True:
                                        disabled_inf.append(j['name'])
                                list(set(disabled_inf))
                            except Exception:
                                if message.text.lower() == 'да':
                                    continue
                                else:
                                    disabled_inf = ['Не найдено']
                            try:
                                url = base['properties']['CompanyMetaData']['url']
                            except Exception:
                                url = 'Не найдено'
                            try:
                                phone = base['properties']['CompanyMetaData']['Phones'][0]['formatted']
                            except Exception:
                                phone = 'Не найдено'
                            try:
                                hours = base['properties']['CompanyMetaData']['Hours']['text']
                            except Exception:
                                hours = "Не найдено"

                            di = {
                                'coords': base['geometry']['coordinates'],
                                'name': base['properties']['name'],
                                'address': base['properties']['CompanyMetaData']['address'],
                                'url': url,
                                'phone': phone,
                                'hours': hours,
                                'disabled_inf': ', '.join(disabled_inf)
                            }
                            list_of_objects.append(di)
                            break
                    except KeyError:
                      pass
        if len(list_of_objects) != 0:
            with open("data_file.json", 'w', encoding='utf8') as w:
                json.dump(list_of_objects, w, ensure_ascii=False, indent=4)
            output(message, list_of_objects)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                types.KeyboardButton('Отправить геопозицию' + chr(128205), request_location=True))
            bot.send_message(message.from_user.id,
                             'Спортивные объекты не найдены, попробуйте начать поиск заново, для этого введите адрес или отправьте геопозицию',
                             reply_markup=markup)
            bot.register_next_step_handler(message, get_location)


def output(message, list_of_objects):
    a = types.ReplyKeyboardRemove()
    bot.send_message(message.from_user.id, f'Найдено объектов: {len(list_of_objects)}', reply_markup=a)
    ct = 0

    keyboard = types.InlineKeyboardMarkup()
    key_next = types.InlineKeyboardButton('->', callback_data="{\"NumberPage\":" + str(ct + 1) + "}")
    key_count = types.InlineKeyboardButton(str(ct + 1), callback_data='counter')
    keyboard.row(key_count, key_next)

    bot.send_location(message.from_user.id, list_of_objects[ct]['coords'][1], list_of_objects[ct]['coords'][0])
    bot.send_message(message.from_user.id, f"""<b>Название</b>: {list_of_objects[ct]['name']}
<b>Адрес</b>: {list_of_objects[ct]['address']}
<b>Сайт</b>: {list_of_objects[ct]['url']}
<b>Номер телефона</b>: {list_of_objects[ct]['phone']}
<b>Часы работы</b>: {list_of_objects[ct]['hours']}
<b>Инфраструктура для людей с ограниченными возможностями</b>: {list_of_objects[ct]['disabled_inf']}""",
                     reply_markup=keyboard,
                     parse_mode='HTML')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Отправить геопозицию' + chr(128205), request_location=True))
    bot.send_message(message.from_user.id, 'Если хотите начать поиск заново, просто укажите новый адрес',
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def next_prev(call):
    if call.data == 'counter':
        pass
    else:
        bot.delete_message(call.from_user.id, call.message.id + 1)
        bot.delete_message(call.from_user.id, call.message.id)
        bot.delete_message(call.from_user.id, call.message.id - 1)
        with open('data_file.json', encoding='utf8') as ff:
            list_of_objects = json.load(ff)
        json_string = json.loads(call.data)
        ct = json_string['NumberPage']
        keyboard = types.InlineKeyboardMarkup()
        key_next = types.InlineKeyboardButton('->', callback_data="{\"NumberPage\":" + str(ct + 1) + "}")
        key_prev = types.InlineKeyboardButton('<-', callback_data="{\"NumberPage\":" + str(ct - 1) + "}")
        key_count = types.InlineKeyboardButton(str(ct + 1), callback_data='counter')
        if ct == 0:
            keyboard.add(key_count, key_next)
        elif ct == len(list_of_objects) - 1:
            keyboard.add(key_prev, key_count)
        elif len(list_of_objects) == 1:
            keyboard.add(key_count)
        else:
            keyboard.add(key_prev, key_count, key_next)
        bot.send_location(call.from_user.id, list_of_objects[ct]['coords'][1], list_of_objects[ct]['coords'][0])
        bot.send_message(call.from_user.id, f"""<b>Название</b>: {list_of_objects[ct]['name']}
<b>Адрес</b>: {list_of_objects[ct]['address']}
<b>Сайт</b>: {list_of_objects[ct]['url']}
<b>Номер телефона</b>: {list_of_objects[ct]['phone']}
<b>Часы работы</b>: {list_of_objects[ct]['hours']}
<b>Инфраструктура для людей с ограниченными возможностями</b>: {list_of_objects[ct]['disabled_inf']}""",
                         reply_markup=keyboard,
                         parse_mode='HTML')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Отправить геопозицию' + chr(128205), request_location=True))
        bot.send_message(call.from_user.id, 'Если хотите начать поиск заново, просто укажите новый адрес',
                         reply_markup=markup)


bot.polling(none_stop=True, interval=0)
