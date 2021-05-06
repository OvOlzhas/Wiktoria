import re
import requests
import sqlite3
import telebot

from bs4 import BeautifulSoup


bot = telebot.TeleBot('1694007852:AAH_S25nSS6Fo4ChnGaMVK5VSKZjiifr2eo')
HOST = 'https://en.wikipedia.org/'
HEADERS = {
    'accept': f'{open("accept.txt").read()}',
    'user-agent': f'{open("useragent.txt").read()}'
}
trash = ['of', 'the', 'in', 'to', 'a', 'an', 'from', 'into', 'and', 'on',
         'at', 'for', 'as', 'by', 'is', 'are', 'he', 'she', 'it', 'they',
         'we', 'their', 'i', 'that', 'was', 'were', 'be', 'not', 'as',
         'or', 'and', 'do', 'with', 'why', 'where', 'what', 'how', 'him', 'her',
         'his', 'us', 'own', 'who', 'when', 'whose', 'which', '']


def get_html(url, message, params=''):
    """
    Возвращает html по url.
    """
    if HOST not in url:
        # Нет строки HOST в url
        bot.send_message(message.from_user.id, "Ничего не найдено. /help")
        return None
    try:
        return requests.get(url, headers=HEADERS, params=params)
    except Exception:
        # Открытие сайта не увенчалось успехом
        bot.send_message(message.from_user.id, "Ничего не найдено. /help")
        return None


def get_content(html, message):
    """
    Возвращает текст из Википедии(TEXT), а также заголовок(NAME).
    """
    TEXT = ""
    soup = BeautifulSoup(html, 'lxml')
    body = soup.find("div", class_="mw-parser-output")
    if body is None:  # Проверка на существование текста
        bot.send_message(message.from_user.id, "Ничего не найдено. /help")
        return None, None
    NAME = soup.find("h1", id="firstHeading").get_text()  # Берется заголовок
    texts_p = body.find_all('p')
    texts_span = body.find_all('span', class_="mw-headline")
    # Удаляются table из html
    for table in body.find_all('table'):
        table.clear()

    # Добавляются в текст "p" и "span"
    for text in body.find_all(['p', 'span']):
        if text in texts_p or text in texts_span:
            TEXT += text.get_text() + '\n'
    return NAME, TEXT


def create_table(cur, conn):
    """
    Создается бд с sqlite.
    """
    cur.execute('''
        CREATE TABLE user (
            user_id INTEGER,
            user_name VARCHAR(255),
            last_text_name VARCHAR(255),
            last_url VARCHAR(255),
            top VARCHAR(255)
        )''')
    cur.execute('''
        CREATE TABLE wiki (
            name VARCHAR(255),
            count INTEGER
        )''')
    conn.commit()


def add_user(cur, conn, user_id, user_name):
    """
    Добавляется новый пользователь в таблицу user.
    """
    cur.execute(f'''INSERT INTO user (user_id, user_name, last_text_name, last_url, top)
                    VALUES ('{user_id}', '{user_name}', '', '', '')''')
    conn.commit()


def check_user(cur, conn, user_id, user_name):
    """
    Проверка на наличие пользователся в таблице user.
    При отсутствии добавляется.
    """
    cur.execute(f'''SELECT *
                    FROM user
                    WHERE user_id={user_id}''')
    if len(cur.fetchall()) == 0:
        add_user(cur, conn, user_id, user_name)


def get_user_content(cur, conn, user_id):
    """
    Возвращаются last_text_name, last_url и top пользователья из таблицы user.
    """
    cur.execute(f'''SELECT last_text_name, last_url, top
                    FROM user
                    WHERE user_id={user_id}''')
    row = cur.fetchone()
    if not row:
        return '', '', ''
    return row


def add_wiki(cur, conn, NAME):
    """
    Добавляется новая статья из Википедии в таблицу wiki.
    """
    cur.execute(f'''INSERT INTO wiki (name, count)
                    VALUES ('{NAME}', '1')''')
    conn.commit()


def get_top_wiki(cur, conn):
    """
    Возвращается 5 наибольее часто запрашиваемых статей из Википедии.
    """
    cur.execute('''SELECT count, name
                    FROM wiki''')
    WTOP = ""
    wikies = []
    for wiki in cur.fetchall():  # Берутся все статьи
        wikies.append(wiki)
    wikies.sort()
    wikies.reverse()
    for (i, wiki) in zip(range(5), wikies):  # 5 наиболее встречаемых статьей
        WTOP += str(i + 1) + ". " + wiki[1] + " => " + str(wiki[0]) + '\n'
    # Проверка на пустоту
    if len(WTOP) == 0:
        WTOP = "Еще не была введена ни одна статья. /help"
    return WTOP


def save_content(user_id, user_name, url, NAME, TOP):
    """
    Обновляется статья в таблице wiki, а также пользователь в user.
    """
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    check_user(cur, conn, user_id, user_name)
    # Обновляется пользователь
    cur.execute(f'''UPDATE user
                    SET last_text_name="{NAME}", top="{TOP}", last_url="{url}"
                    WHERE user_id={user_id}''')

    cur.execute(f'''SELECT count, name
                    FROM wiki
                    WHERE name="{NAME}"''')
    row = cur.fetchall()
    # Обновляется статья или же создается
    if len(row) == 0:
        add_wiki(cur, conn, NAME)
    else:
        # Обновляется количество статьей с заголовком NAME
        cur.execute(f'''UPDATE wiki
                        SET count={row[0][0] + 1}
                        WHERE name="{NAME}"''')
    conn.commit()
    conn.close()


def top_words(TEXT):
    """
    Возвращается 5 наибольее часто встречающиеся слова,
    кроме слов из trash.
    """
    global trash

    WORDS = {}
    for word in TEXT.split():
        word = word.lower()
        copy = word
        # Удаляются нежелаемые символы
        for c in copy:
            if ord('a') > ord(c) or ord(c) > ord('z'):
                word = re.sub(f'[{c}]', '', word)
        # Проверка на содержании в trash
        if not word.lower() in trash:
            # Добавляется слово
            WORDS[word.lower()] = WORDS.get(word, 0) + 1
    words = []
    TOP = ""
    # Берутся слова, которые встречаются наибольшее количество раз
    for word in WORDS.items():
        words.append((word[1], word[0]))
    words.sort()
    words.reverse()
    for (i, word) in zip(range(5), words):  # 5 наиболее встречаемых слов
        TOP += str(i + 1) + ". " + str(word[1]) + " => " + str(word[0]) + "\n"
    # Проверка на пустоту
    if len(TOP) == 0:
        TOP = "Еще не была введена ни одна статья. /help"
    return TOP


def print_text(message, NAME, TEXT):
    """
    Отправляется сообщение с первым абзацем текста с кнопками
    "View all text" и "Top 5 words".
    """
    # Создание кнопок
    markup = telebot.types.InlineKeyboardMarkup()
    button1 = telebot.types.InlineKeyboardButton("View all text", callback_data="AllText")
    button2 = telebot.types.InlineKeyboardButton("Top 5 words", callback_data="TopWords")
    markup.row(button1, button2)

    # Берется первый абзац
    start = 0
    first_text = ""
    for start in range(0, len(TEXT)):
        if TEXT[start] == '\n':
            if len(first_text) != 0:
                break
            continue
        first_text += TEXT[start]

    # Удаляется первый абзац
    TEXT = TEXT[start:len(TEXT)]
    # Отправка первого абзаца
    if (len(TEXT) != 0):
        bot.send_message(message.chat.id, "*" + NAME + "*\n\n" + first_text,
                         reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "*" + NAME + "*\n\n" + first_text,
                         parse_mode='Markdown')


def print_top(message):
    """
    Отправляется сообщение с 5 наиболее встречаемыми словами.
    """
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    (NAME, url, TOP) = get_user_content(cur, conn, message.from_user.id)
    if len(TOP) == 0:
        TOP = 'Еще не была введена ни одна статья. /help'
    bot.send_message(message.from_user.id, TOP)
    conn.close()


@bot.callback_query_handler(lambda q: q.data == 'AllText')
def callback_alltext(call):
    """
    Нажата кнопка "View all text".
    Отправляются сообщения с текстом без первого абзаца.
    """
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    (NAME, url, TOP) = get_user_content(cur, conn, call.from_user.id)

    html = get_html(url, call)
    if html is None:
        conn.close()
        return
    NAME, TEXT = get_content(html.text, call)
    if NAME is None or TEXT is None:
        conn.close()
        return

    # Удаляется первый абзац
    ok = False
    for start in range(0, len(TEXT)):
        if TEXT[start] == '\n':
            if ok:
                break
            continue
        ok = True
    TEXT = TEXT[start:len(TEXT)]

    # Отправка текста без первого абзаца
    bot.answer_callback_query(call.id)
    for x in range(0, len(TEXT), 4096):  # 4096 - макс. количество символов в одном сообщение
        if x + 4096 >= len(TEXT):
            markup = telebot.types.InlineKeyboardMarkup()
            button = telebot.types.InlineKeyboardButton("Top 5 words", callback_data="TopWords")
            markup.add(button)
            bot.send_message(call.from_user.id, TEXT[x:x+4096], reply_markup=markup)
        else:
            bot.send_message(call.from_user.id, TEXT[x:x+4096])
    conn.close()


@bot.callback_query_handler(lambda q: q.data == 'TopWords')
def callback_topwords(call):
    """
    Нажата кнопка "Top 5 words".
    Отправляется сообщение с 5 наиболее встречаемыми словами.
    """
    bot.answer_callback_query(call.id)
    print_top(call)


@bot.message_handler(commands=["start", "help", "lasttop", "lastwiki", "topwiki", "gettext"])
def get_command(message):
    """
    Обрабатываются команды /start, /help,  /lasttop, /lastwiki и /topwiki.
    """
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    if message.text == "/help" or message.text == "/start":
        mess = '''
Доступные тебе команды:
1. *GetText* or */gettext* - Вывод текста из английской Википедии.
После команды должно последовать сообщение с тем, что Вы ищете.
2. *LastTop* or */lasttop* - Вывод пяти наиболее встречаемых слов
3. *LastWiki* or */lastwiki* - Вывод названия последнего текста
4. *TopWiki* or */topwiki* - Вывод названии 5 наиболее запрашиваемых статьей
5. /help - Вывод всех доступных команд'''
        if message.text == "/start":
            mess = f"Привет, {message.from_user.first_name}!     " + mess
        bot.send_message(message.from_user.id, mess, parse_mode="Markdown")

        check_user(cur, conn, message.from_user.id, message.from_user.first_name)
    elif message.text == "/lasttop":
        # Введено LastTop
        print_top(message)
    elif message.text == "/lastwiki":
        # Введено LastWiki
        (NAME, url, TOP) = get_user_content(cur, conn, message.from_user.id)

        if len(NAME) == 0:
            NAME = "Еще не была введена ни одна статья."
        bot.send_message(message.from_user.id, NAME)
    elif message.text == "/topwiki":
        # Введено TopWiki
        bot.send_message(message.from_user.id, get_top_wiki(cur, conn))
    elif message.text == "/gettext":
        bot.send_message(message.from_user.id, 'Введите, что Вы хотите найти на Википедии. *(На английском)*',
                         parse_mode="Markdown")
        bot.register_next_step_handler(message, get_text)
    conn.close()


def get_text(message):
    html = get_html(HOST + '/w/index.php?search=' + message.text, message)
    if html is None:
        return
    NAME, TEXT = get_content(html.text, message)
    if NAME is None or TEXT is None:
        return
    TOP = top_words(TEXT)
    print_text(message, NAME, TEXT)
    save_content(message.from_user.id, message.from_user.first_name, HOST + '/w/index.php?search=' + message.text, NAME, TOP)


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    """
    Ожидаются команды "GetText", "LastTop", "LastWiki" и "TopWiki".
    """
    words = message.text.split()
    if words[0].lower() in ["gettext", "lasttop", "lastwiki", "topwiki"]:
        message.text = '/' + words[0].lower()
        get_command(message)
    else:
        # Неизвестная команда
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")


def start():
    """
    Создается таблица.
    """
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    create_table(cur, conn)
    conn.close()


start()

# Бот работает бесконечно
if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
