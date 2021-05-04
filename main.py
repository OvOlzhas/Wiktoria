import re
import sys
import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3

bot = telebot.TeleBot('1694007852:AAH_S25nSS6Fo4ChnGaMVK5VSKZjiifr2eo')
HOST = 'https://en.wikipedia.org/wiki/'
HEADERS = {
    'accept': 
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36'
}
musor = ['в', 'без', 'до', 'из', 'к', 'на', 'по', 'о', 'от', 'перед', 'при', 'через', 'с', 'у',
         'за', 'над', 'об', 'под', 'про', 'для', 'и', 'не', 'что', 'как', 'а', 'то',
         'of', 'the', 'in', 'to', 'a', 'an', 'from', 'into', 'and', 'on', 'at', 'for', 'as', 'by',
         'is', 'are', '']


def get_html(url, message, params=''):
    if not HOST in url:
        bot.send_message(message.from_user.id, "Ссылка не корректна.")
        sys.exit()
    try:
        return requests.get(url, headers=HEADERS, params=params)
    except:
        bot.send_message(message.from_user.id, "Ссылка не корректна.")
        sys.exit()


def get_content(html):
    TEXT = ""
    soup = BeautifulSoup(html, 'lxml')
    body = soup.find("div", class_="mw-parser-output")
    NAME = soup.find("h1", id="firstHeading").get_text()
    texts_p = body.find_all('p')
    texts_span = body.find_all('span', class_="mw-headline")
    for table in body.find_all('table'):
        table.clear()

    for text in body.find_all(['p', 'span']):
        if text in texts_p or text in texts_span:
            TEXT += text.get_text() + '\n'
    return (NAME, TEXT)


def create_table(cur, conn):
    cur.execute('DROP TABLE IF EXISTS user')
    cur.execute('DROP TABLE IF EXISTS wiki')

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
    cur.execute(f'''INSERT INTO user (user_id, user_name, last_text_name, last_url, top) 
                    VALUES ('{user_id}', '{user_name}', '', '', '')''')
    conn.commit()

def check_user(cur, conn, user_id, user_name):
    cur.execute(f'''SELECT *
                    FROM user
                    WHERE user_id={user_id}''')
    if len(cur.fetchall()) == 0:
        add_user(cur, conn, user_id, user_name)

def get_user_content(cur, conn, message):
    cur.execute(f'''SELECT last_text_name, last_url, top
                    FROM user
                    WHERE user_id={message.from_user.id}''')
    row = cur.fetchone()
    if not row:
        return ('', '', '')
    return row

def add_wiki(cur, conn, NAME):
    cur.execute(f'''INSERT INTO wiki (name, count) 
                    VALUES ('{NAME}', '1')''')
    conn.commit()

def get_top_wiki(cur, conn, message):
    cur.execute(f'''SELECT count, name
                    FROM wiki''')
    WTOP = ""
    wikies = []
    for wiki in cur.fetchall():
        wikies.append(wiki)
    reversed(sorted(wikies))
    for (i, wiki) in zip(range(5), wikies):
        WTOP += str(i + 1) + ". " + wiki[1] + " => " + str(wiki[0])
        if i != 4:
            WTOP += '\n'
    return WTOP


def save_content(user_id, user_name, url, NAME, TOP):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    check_user(cur, conn, user_id, user_name)
    cur.execute(f'''UPDATE user 
                    SET last_text_name="{NAME}", top="{TOP}", last_url="{url}"
                    WHERE user_id={user_id}''')
    
    cur.execute(f'''SELECT count, name
                    FROM wiki
                    WHERE name="{NAME}"''')
    row = cur.fetchall()
    if len(row) == 0:
        add_wiki(cur, conn, NAME)
    else:
        cur.execute(f'''UPDATE wiki
                        SET count={row[0][0] + 1}
                        WHERE name="{NAME}"''')
    conn.commit()
    conn.close()


def top_words(TEXT):
    global musor

    WORDS = {}
    for word in TEXT.split():
        word = word.lower()
        copy = word
        for c in copy:
            if ord('a') > ord(c) or ord(c) > ord('z'):
                word = re.sub(f'[{c}]', '', word)
        if not word.lower() in musor:
            WORDS[word.lower()] = WORDS.get(word, 0) + 1
    words = []
    TOP = ""
    for word in WORDS.items():
        words.append((word[1], word[0]))
    for (i, word) in zip(range(5), reversed(sorted(words))):
        TOP += str(i + 1) + ". " + str(word[1]) + " => " + str(word[0])
        if i != 4:
            TOP += "\n"
    return TOP


def print_text(message, NAME, TEXT):
    markup = telebot.types.InlineKeyboardMarkup()
    button1 = telebot.types.InlineKeyboardButton("View all text", callback_data="AllText")
    button2 = telebot.types.InlineKeyboardButton("Top 5 words", callback_data="TopWords")
    markup.row(button1, button2)
    
    start = 0
    first_text = ""
    for start in range(0, len(TEXT)):
        if TEXT[start] == '\n':
            if len(first_text) != 0:
                break
            continue
        first_text += TEXT[start]
    
    TEXT = TEXT[start:len(TEXT)]
    if (len(TEXT) != 0):
        bot.send_message(message.chat.id, "*" + NAME + "*\n\n" + first_text, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "*" + NAME + "*\n\n" + first_text, parse_mode='Markdown')


def print_top(message):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    (NAME, url, TOP) = get_user_content(cur, conn, message)
    bot.send_message(message.from_user.id, TOP)
    conn.close()
    


@bot.callback_query_handler(lambda q: q.data == 'AllText')
def callback_query(call):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    (NAME, url, TOP) = get_user_content(cur, conn, call)
    
    html = get_html(url, call)
    NAME, TEXT = get_content(html.text)

    ok = False
    for start in range(0, len(TEXT)):
        if TEXT[start] == '\n':
            if ok:
                break
            continue
        ok = True
    TEXT = TEXT[start:len(TEXT)]
    bot.answer_callback_query(call.id)
    for x in range(0, len(TEXT), 4096):
        bot.send_message(call.from_user.id, TEXT[x:x+4096])
    conn.close()


@bot.callback_query_handler(lambda q: q.data == 'TopWords')
def callback_query(call):
    bot.answer_callback_query(call.id)
    print_top(call)


@bot.message_handler(commands=["start", "help"])
def get_command(message):
    if message.text == "/help" or message.text == "/start":
        mess = '''
Доступные тебе команды:    
1. *GetText <Ссылка на статью из Википедию>* - Вывод текста из Википедии    
_(Cсылка должна начинаться как https://en.wikipedia.org/wiki/)_    
2. *LastTop* - Вывод пяти наиболее встречаемых слов     
3. *LastWiki* - Вывод названия последнего текста      
4. *TopWiki* - Вывод названии, 5 наиболее запрашиваемых статьей'''
        if (message.text == "/start"):
            mess = "Привет!     " + mess
        bot.send_message(message.from_user.id, mess, parse_mode="Markdown")
        
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        check_user(cur, conn, message.from_user.id, message.from_user.first_name)
        conn.close()


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    global TOP
    words = message.text.split()
    if words[0].lower() == "gettext" and len(words) != 1:
        html = get_html(words[1], message)
        NAME, TEXT = get_content(html.text)
        TOP = top_words(TEXT)
        print_text(message, NAME, TEXT)
        save_content(message.from_user.id, message.from_user.first_name, words[1], NAME, TOP)
    elif words[0].lower() == "lasttop":
        print_top(message)
    elif words[0].lower() == "lastwiki":
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        (NAME, url, TOP) = get_user_content(cur, conn, message)

        bot.send_message(message.from_user.id, NAME)
        conn.close()
    elif words[0].lower() == "topwiki":
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        bot.send_message(message.from_user.id, get_top_wiki(cur, conn, message))
        conn.close()
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")


def start():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    create_table(cur, conn)
    conn.close()

start()

bot.polling(none_stop=True, interval=0)
