import logging
import os
import requests
from random import randint

from dotenv import load_dotenv
from telebot import TeleBot, types
from pydub import AudioSegment, effects

from converter import Converter
from psn import get_psn_status


load_dotenv()

TOKEN = os.getenv('TOKEN')
bot = TeleBot(token=TOKEN)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger()

user_languages = {}

LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
}

CAT_URL = 'https://api.thecatapi.com/v1/images/search'
DOG_URL = 'https://api.thedogapi.com/v1/images/search'
HABR_URL = 'https://habr.com/ru/all/'

QUOTES = [
    'Began to spin.', 'System.', 'The system.', 'Cells.',
    'Interlinked.', 'Within cells interlinked.', 'Within.', 'Stem.',
    'Dreadfully.', 'Distinct.', 'Dark.', 'Against the dark.',
    'Fountain.', 'White Fountain.', 'A Tall White Fountain.',
]


# Util functions
def get_new_image():
    try:
        response = requests.get(CAT_URL)
    except Exception as error:
        logging.error(f'Error when requesting the main API: {error}')
        response = requests.get(DOG_URL)
    response = response.json()
    random_cat = response[0].get('url')
    return random_cat


def private_chat_only(func):
    def wrapper(message):
        if message.chat.type != 'private':
            return
        return func(message)
    return wrapper


def group_chat_only(func):
    def wrapper(message):
        if message.chat.type == 'private':
            return
        return func(message)
    return wrapper


# Command handlers
@bot.message_handler(commands=['newcat'])
def newcat(message):
    chat_id = message.chat.id
    bot.send_photo(chat_id, get_new_image())


@bot.message_handler(commands=['getaudio'])
def getaudio(message):
    chat_id = message.chat.id
    with open('Lana_Del_Rey_Born_To_Die.mp3', 'rb') as audio:
        bot.send_audio(chat_id, audio=audio)


@bot.message_handler(commands = ['getlink'])
def getlink(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text='habr.com', url=HABR_URL)
    markup.add(btn1)
    text = 'You can go to the website by clicking the button below'
    if user_languages:
        localization = {
            'en': 'You can go to the website by clicking the button below',
            'ru': 'По кнопке ниже можно перейти на сайт',
        }
        text = localization[user_languages[user_id]]
    bot.send_message(chat_id, text, reply_markup=markup)


@bot.message_handler(commands=['chlang'])
def chlang(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=name, callback_data=f'lang_{code}') for code, name in LANGUAGES.items()]
    markup.add(*buttons)
    bot.send_message(chat_id, 'Choose language / Выберите язык', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def language_callback(call):
    lang_code = call.data.split('_')[1]
    user_languages[call.from_user.id] = lang_code
    bot.answer_callback_query(call.id, f'{LANGUAGES[lang_code]}')
    bot.send_message(call.message.chat.id, f'Language set to {LANGUAGES[lang_code]}')


@bot.message_handler(commands=['checkstatus'])
def checkstatus(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, get_psn_status())


# Start function
@bot.message_handler(commands=['start'])
def start(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    name = message.from_user.first_name
    logger.info(f'Chat {name} (ID: {chat_id}) started bot')
    c1 = types.BotCommand(command='start', description='Restart Bot')
    c2 = types.BotCommand(command='newcat', description='Get New Cat')
    c3 = types.BotCommand(command='getaudio', description='Get Audio')
    c4 = types.BotCommand(command='getlink', description='Get Link')
    c5 = types.BotCommand(command='chlang', description='Choose Language')
    c6 = types.BotCommand(command='checkstatus', description='Check PSN Status')
    bot.set_my_commands([c1,c2,c3,c4,c5,c6])
    if message.chat.type == 'private':
        bot.set_chat_menu_button(chat_id, types.MenuButtonCommands('commands'))
    keyboard = types.ReplyKeyboardRemove()
    text = f'Hello, {name}. My name is Charlie'
    if user_languages:
        localization = {
            'en': f'Hello, {name}. My name is Charlie',
            'ru': f'Привет, {name}. Меня зовут Чарли',
        }
        text = localization[user_languages[user_id]]
    bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


# Content types handlers
@bot.message_handler(func=lambda message: message.chat.type == 'private' and message.text)
def chat(message):
    logger.info('Processing text...')
    chat = message.chat
    chat_id = chat.id
    quote = QUOTES[randint(0, 15)]
    bot.send_message(chat_id=chat_id, text=quote)


@bot.message_handler(content_types=['voice'])
def voice_to_text(message: types.Message):
    logger.info('Processing voice...')
    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = str(message.message_id)
    name = message.chat.first_name if message.chat.first_name else 'No_name'
    logger.info(f'Chat {name} (ID: {message.chat.id}) downloading file {file_name}')

    with open(file_name, 'wb') as new_file:
        new_file.write(downloaded_file)

    audio = AudioSegment.from_file(file_name, format='ogg')
    audio.export('file.wav', format='wav')
    converter = Converter('file.wav')
    os.remove(file_name)
    message_text = converter.audio_to_text()
    del converter

    bot.send_message(message.chat.id, message_text, reply_to_message_id=message.message_id)


# Moderation
@bot.message_handler(func=lambda message: message.chat.type != 'private' and message.entities is not None)
def delete_links(message):
    user_id = message.from_user.id
    logger.info('Deleting link...')
    for entity in message.entities:
        if entity.type in ['url', 'text_link']:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                logging.error(f'Exception while deleting a message: {e}')
            else:
                text = 'Posting links is prohibited'
                if user_languages:
                    localization = {
                        'en': 'Posting links is prohibited',
                        'ru': 'Публикация ссылок запрещена',
                    }
                    text = localization[user_languages[user_id]]
                bot.send_message(message.chat.id, text)
            break


def main():
    logger.info('Starting bot')
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
