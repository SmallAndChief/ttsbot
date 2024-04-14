import logging
import time
from telebot import TeleBot
from telebot.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN, MAX_MESSAGE_SYMBOLS, MAX_TTS_MESSAGES, folder_id
from tts import create_iam_token, text_to_speech
from database import create_table, is_limit_users, insert_row, is_limit_messages


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='log_file.txt',
    filemode='a',
)


create_table()
token_data = create_iam_token()
expires_at = time.time() + token_data['expires_in']
iam_token = token_data['access_token']

bot = TeleBot(token=TOKEN)

bot.set_my_commands([BotCommand('start', 'начало работы'),
                     BotCommand('help', 'инструкция'),
                     BotCommand('tts', 'синтез речи')])

help_button = KeyboardButton("/help")
tts_button = KeyboardButton("/tts")


@bot.message_handler(commands=['start'])
def start_message(message):
    logging.info('Отправка приветственного сообщения')
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(help_button)
    user_name = message.from_user.first_name
    bot.send_message(chat_id=message.chat.id,
                     text=f'Приветствую вас, {user_name}! Это бот для синтеза речи. Ознакомьтесь с помощь /help.',
                     reply_markup=markup)


@bot.message_handler(commands=['help'])
def help_message(message):
    logging.info('Отправка инструкции')
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(tts_button)
    bot.send_message(chat_id=message.chat.id,
                     text=("Данный бот предоставляет возможности синтеза речи.\nЧтобы начать синтез необходимо "
                           "ввести команду /tts, а после отправить текст, который необходимо обработать.\n"
                           f"Учтите, что текст одного сообщения имеет ограничение в {MAX_MESSAGE_SYMBOLS} символов, "
                           f"а всего можно отправить сообщений на синтез {MAX_TTS_MESSAGES}"),
                     reply_markup=markup)


@bot.message_handler(commands=['tts'])
def help_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_limit_users():
        bot.send_message(chat_id=chat_id,
                         text="Достигнут лимит пользователей. Вы не сможете воспользоваться ботом.")
        logging.info("Достигнут лимит пользователей")
        return
    if is_limit_messages(user_id=user_id):
        bot.send_message(chat_id=chat_id,
                         text="Достигнут лимит сообщений. Вы не сможете воспользоваться ботом.")
        logging.info("Достигнут лимит пользователей")
        return
    logging.info('Введена команда tts')
    bot.send_message(chat_id=chat_id,
                     text='Отправь следующим сообщением текст, чтобы я его озвучил!')
    bot.register_next_step_handler(message, tts)


def tts(message, expires_at=expires_at, iam_token=iam_token):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        logging.warning(f'Неверный тип данных {user_id}')
        bot.register_next_step_handler(message, tts)
        return
    text = message.text
    if len(text) > MAX_MESSAGE_SYMBOLS:
        bot.send_message(chat_id=chat_id,
                         text='Превышен лимит символов. Сократите текст и отправьте его снова!')
        logging.warning(f'Превышен лимит символов {user_id}')
        bot.register_next_step_handler(message, tts)
        return
    if expires_at < time.time():
        token_data = create_iam_token()
        expires_at = time.time() + token_data['expires_in']
        iam_token = token_data['access_token']
        logging.info("смена iam_token")
    insert_row((user_id, text, len(text)))
    tts_answer = text_to_speech(text=text, iam_token=iam_token, folder_id=folder_id)
    if tts_answer:
        bot.send_voice(chat_id=chat_id, voice=tts_answer)
        logging.info(f'Отправка голосового сообщения к {user_id}')
    else:
        bot.send_message(chat_id=message.chat.id,
                         text='Произошла ошибка. Попробуйте повторить чуть позже.')


@bot.message_handler(commands=['debug'])
def debug_message(message):
    with open("log_file.txt", "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.message_handler(content_types=['text'])
def text_message(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(help_button)
    bot.send_message(chat_id=message.chat.id,
                     text='Я не понимаю чего вы хотите. Введите /help.',
                     reply_markup=markup)
    logging.info(f'Неизвестная команда от {message.from_user.id}')


bot.infinity_polling()
