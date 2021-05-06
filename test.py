import unittest
import main
import sqlite3


class TestMain(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect('database.db')
        self.cur = self.conn.cursor()
        main.create_table(self.cur, self.conn)

    def tearDown(self):
        self.conn.close()

    def test_get_content(self):
        NAME, TEXT = main.get_content(
            main.get_html('https://en.wikipedia.org/wiki/Hajime_no_Ippo', '').text,
            '')
        self.assertEqual(NAME, 'Hajime no Ippo')

    def test_create_table(self):
        self.cur.execute('''SELECT *
                        FROM user''')
        self.assertEqual(self.cur.fetchall(), [])
        self.cur.execute('''SELECT *
                        FROM wiki''')
        self.assertEqual(self.cur.fetchall(), [])

    def test_add_user(self):
        main.add_user(self.cur, self.conn, 123, 'Ippo')
        self.cur.execute('''SELECT user_id, user_name, last_text_name, last_url, top
                        FROM user''')
        self.assertEqual(self.cur.fetchall(), [(123, 'Ippo', '', '', '')])

    def test_check_user(self):
        main.check_user(self.cur, self.conn, 123, 'Ippo')
        self.cur.execute('''SELECT user_id, user_name, last_text_name, last_url, top
                        FROM user''')
        self.assertEqual(self.cur.fetchall(), [(123, 'Ippo', '', '', '')])

    def test_get_user_content(self):
        main.check_user(self.cur, self.conn, 123, 'Ippo')
        self.assertEqual(main.get_user_content(self.cur, self.conn, 123), ('', '', ''))

    def test_add_wiki(self):
        main.add_wiki(self.cur, self.conn, 'Hajime no Ippo')
        self.cur.execute('''SELECT name, count
                        FROM wiki''')
        self.assertEqual(self.cur.fetchall(), [('Hajime no Ippo', 1)])

    def test_get_top_wiki(self):
        main.add_wiki(self.cur, self.conn, 'a')
        main.add_wiki(self.cur, self.conn, 'b')
        self.assertEqual(main.get_top_wiki(self.cur, self.conn), "1. b => 1\n2. a => 1\n")

    def test_save_content(self):
        main.save_content(123, 'Ippo', 'url', 'Hajime no Ippo', '1. b => 1\n2. a => 1\n')
        self.cur.execute('''SELECT user_id, user_name, last_text_name, last_url, top
                        FROM user
                        WHERE user_id=123''')
        self.assertEqual(self.cur.fetchone(), (123, 'Ippo', 'Hajime no Ippo', 'url', '1. b => 1\n2. a => 1\n'))
        self.cur.execute('''SELECT name, count
                        FROM wiki
                        WHERE name="Hajime no Ippo"''')
        self.assertEqual(self.cur.fetchone(), ('Hajime no Ippo', 1))

    def test_top_words(self):
        self.assertEqual(main.top_words('Ippo Ippo Hajime'), '1. ippo => 2\n2. hajime => 1\n')


if __name__ == '__main__':
    unittest.main()
