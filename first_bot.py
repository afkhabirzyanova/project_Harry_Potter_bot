import telebot
import conf
from telebot import types
import csv
import random

bot = telebot.TeleBot(conf.TOKEN)

user_states = {}  # Словарь для отслеживания состояния игры каждого пользователя
user_scores = {}  # Словарь для хранения количества баллов каждого пользователя
model_scores = {}  # Словарь для хранения количества баллов модели
SENTENCES_PER_GAME = 10  # Количество предложений в каждой игре
USERS_DATA_FILE = 'users_data.csv'  # Имя файла для сохранения данных о пользователях


# Функция для выбора случайного предложения из файла
def get_random_sentence():
    with open('with_pred_hp.csv', 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        rows = list(csv_reader)
        random_row = random.choice(rows)
        sentence = random_row['sentence']
        classification = random_row['class']
        model_classification = random_row['model_class']
        return sentence, classification, model_classification


# Функция для сохранения данных о пользователях в файл CSV
def save_user_data():
    with open(USERS_DATA_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['User ID', 'Username', 'Score'])

        for user_id, score in user_scores.items():
            user = bot.get_chat(user_id)
            writer.writerow([user_id, user.first_name, score])


# Функция для загрузки данных о пользователях из файла CSV
def load_user_data():
    try:
        with open(USERS_DATA_FILE, mode='r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                user_id, username, score = row
                user_scores[int(user_id)] = int(score)
    except FileNotFoundError:
        pass


# Функция для отправки сообщения с началом игры
def send_game_start_message(chat_id):
    user_scores[chat_id] = 0
    model_scores[chat_id] = 0

    sentence, classification, model_classification = get_random_sentence()
    user_states[chat_id] = {'classification': classification, 'model_classification': model_classification,
                            'sentences_left': SENTENCES_PER_GAME}
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_original = types.KeyboardButton(text="Оригинал")
    button_generated = types.KeyboardButton(text="Сгенерирован")
    keyboard.add(button_original, button_generated)

    bot.send_message(chat_id, sentence, reply_markup=keyboard)


# Функция для определения победителя
def determine_winner(user_score, model_score):
    if user_score > model_score:
        return "Вы победили!"
    elif user_score < model_score:
        return "Модель Naive Bayes победила!"
    else:
        return "Ничья!"


# Обработчик команды /start для начала игры
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_start = types.KeyboardButton(text="Начать игру")
    button_top_players = types.KeyboardButton(text="Показать топ-10 игроков")
    keyboard.add(button_start, button_top_players)

    bot.send_message(message.chat.id,
                     message.from_user.first_name + ", давайте проверим насколько хорошо вы можете отличить оригинал\
 от сгенерированного текста. За одну игру будет 10 предложений. C вами параллельно будет угадывать модель Naive Bayes.",
                     reply_markup=keyboard)


# Обработчик кнопки "Сыграть еще раз"
@bot.message_handler(func=lambda message: message.text == "Сыграть еще раз")
def play_again(message):
    send_game_start_message(message.chat.id)


# Обработчик кнопки "Начать игру"
@bot.message_handler(func=lambda message: message.text == "Начать игру")
def game(message):
    if message.chat.id not in user_states:
        send_game_start_message(message.chat.id)


# Обработчик кнопки "Показать топ-10 игроков"
@bot.message_handler(func=lambda message: message.text == "Показать топ-10 игроков")
def show_top_players(message):
    # Сортируем словарь с оценками пользователей по убыванию баллов и выбираем топ-10
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    # Инициализируем строку с сообщением о топ-10 игроках
    top_players_message = "Топ-10 игроков:\n"
    # Перебираем отсортированных пользователей и добавляем их имена и баллы в сообщение
    for idx, (user_id, score) in enumerate(sorted_users, start=1):
        user = bot.get_chat(user_id)  # Получаем информацию о пользователе по его идентификатору
        top_players_message += f"{idx}. {user.first_name} - {score}\n"  # Добавляем имя и баллы в сообщение

    bot.send_message(message.chat.id, top_players_message)  # Отправляем сообщение с топ-10 игроками пользователю


# Обработчик сообщений пользователя, содержащих текст "Оригинал" или "Сгенерирован"
@bot.message_handler(func=lambda message: message.text in ["Оригинал", "Сгенерирован"])
def handle_buttons(message):
    chat_id = message.chat.id  # Получаем идентификатор чата пользователя
    state = user_states.get(chat_id)  # Получаем текущее состояние игры пользователя из словаря состояний
    # Если состояние пользователя отсутствует, возвращаемся из функции
    if state is None:
        return

    user_answer = message.text.lower()  # Получаем ответ пользователя и переводим его в нижний регистр
    correct_classification = state['classification']  # Получаем правильную классификацию текущего предложения
    model_classification = state['model_classification']  # Получаем классификацию модели Naive Bayes
    # Проверяем ответ пользователя и увеличиваем счетчик баллов
    if (user_answer == "оригинал" and correct_classification == "original") or \
            (user_answer == "сгенерирован" and correct_classification == "generated"):
        bot.send_message(chat_id, "Верно!")  # Отправляем сообщение пользователю о правильном ответе
        user_scores[chat_id] += 1  # Увеличиваем количество баллов пользователя
    else:
        bot.send_message(chat_id, "Не угадали!")  # Отправляем сообщение пользователю о неправильном ответе
    # Проверяем классификацию модели и увеличиваем счетчик баллов модели
    if model_classification == correct_classification:
        bot.send_message(chat_id, "Модель Naive Bayes угадала!")  # Отправляем сообщение о правильном ответе модели
        model_scores[chat_id] += 1  # Увеличиваем количество баллов модели
    else:
        bot.send_message(chat_id, "Модель Naive Bayes не угадала!")  # Отправляем сообщение о неправильном ответе модели

    state['sentences_left'] -= 1  # Уменьшаем количество оставшихся предложений в текущей игре на 1

    if state['sentences_left'] <= 0:  # Если оставшихся предложений нет
        # Создаем клавиатуру для кнопок "Сыграть еще раз" и "Показать топ-10 игроков"
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_play_again = types.KeyboardButton(text="Сыграть еще раз")
        button_top_players = types.KeyboardButton(text="Показать топ-10 игроков")
        keyboard.add(button_play_again, button_top_players)
        # Формируем сообщение о завершении игры и результате
        winner_message = determine_winner(user_scores.get(chat_id, 0), model_scores.get(chat_id, 0))
        # Отправляем сообщение о завершении игры с информацией о счете ппользователя и модели Naive Bayes
        bot.send_message(chat_id, "Игра завершена.\n" + message.from_user.first_name + f", у вас счет:"
                                                                                       f" {user_scores.get(chat_id, 0)}"
                                                                                       "/10.\nСчет модели Naive Bayes:"
                                                                                       f"{model_scores.get(chat_id, 0)}"
                                                                                       "/10.\n" + winner_message,
                         reply_markup=keyboard)
        # Удаляем состояние пользователя из словаря состояний
        del user_states[chat_id]
        save_user_data()  # Сохраняем данные о пользователе после игры
    else:
        # Если оставшиеся предложения есть, отправляем следующее предложение и обновляем состояние пользователя
        sentence, classification, model_classification = get_random_sentence()
        state['classification'] = classification
        state['model_classification'] = model_classification

        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_original = types.KeyboardButton(text="Оригинал")
        button_generated = types.KeyboardButton(text="Сгенерирован")
        keyboard.add(button_original, button_generated)

        bot.send_message(chat_id, sentence, reply_markup=keyboard)
        user_states[chat_id] = state


load_user_data()

bot.polling(none_stop=True)
