import sqlite3

DB_NAME = "finance_tracker.db"

def get_connection():
    """Создаёт соединение с базой данных"""
    return sqlite3.connect(DB_NAME)

def init_db():
    """Создаёт все таблицы, если их ещё нет"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            daily_limit REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planned_transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
            planned_date TEXT,
            is_done INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('savings', 'investment')),
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print("База данных успешно создана!")

def add_user(telegram_id, username):
    """Добавляет нового пользователя, если его ещё нет"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (telegram_id, username)
    )
    conn.commit()
    conn.close()

def get_user(telegram_id):
    """Возвращает данные пользователя по его telegram_id"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    user = cursor.fetchone()
    conn.close()
    return user

DEFAULT_CATEGORIES = [
    ("Еда", "expense"),
    ("Транспорт", "expense"),
    ("Развлечения", "expense"),
    ("Жильё", "expense"),
    ("Здоровье", "expense"),
    ("Прочее", "expense"),
    ("Зарплата", "income"),
    ("Подарки", "income"),
    ("Прочий доход", "income"),
]

def add_default_categories(user_id):
    """Добавляет базовый набор категорий для нового пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    for name, cat_type in DEFAULT_CATEGORIES:
        cursor.execute(
            "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)",
            (user_id, name, cat_type)
        )
    conn.commit()
    conn.close()

def add_custom_category(user_id, name, cat_type):
    """Добавляет собственную категорию пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)",
        (user_id, name, cat_type)
    )
    conn.commit()
    conn.close()

def get_categories(user_id, cat_type=None):
    """Возвращает список категорий пользователя, опционально фильтруя по типу"""
    conn = get_connection()
    cursor = conn.cursor()
    if cat_type:
        cursor.execute(
            "SELECT * FROM categories WHERE user_id = ? AND type = ?",
            (user_id, cat_type)
        )
    else:
        cursor.execute(
            "SELECT * FROM categories WHERE user_id = ?",
            (user_id,)
        )
    categories = cursor.fetchall()
    conn.close()
    return categories

def add_transaction(user_id, category_id, amount, description=None):
    """Добавляет запись о доходе или трате"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (user_id, category_id, amount, description) VALUES (?, ?, ?, ?)",
        (user_id, category_id, amount, description)
    )
    conn.commit()
    conn.close()

def get_transactions(user_id, limit=10):
    """Возвращает последние транзакции пользователя вместе с названием категории"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT transactions.id, transactions.amount, categories.name, 
               categories.type, transactions.date, transactions.description
        FROM transactions
        JOIN categories ON transactions.category_id = categories.id
        WHERE transactions.user_id = ?
        ORDER BY transactions.date DESC
        LIMIT ?
    """, (user_id, limit))
    result = cursor.fetchall()
    conn.close()
    return result

if __name__ == "__main__":
    init_db()