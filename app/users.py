import hashlib
import sqlite3
import os
from flask_login import UserMixin

# SQLite database path in persistent volume
DB_PATH = '/app/data/users.db'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        """Check if provided password matches the stored hash"""
        return self.password_hash == hash_password(password)

    @staticmethod
    def get(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2])
            return None
        finally:
            conn.close()

    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2])
            return None
        finally:
            conn.close()

def hash_password(password):
    """Simple password hashing using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create tables if they don't exist"""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if any users exist
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        # Create default users if no users exist
        if user_count == 0:
            print("Creating default users...")
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('admin', hash_password('admin123'))
            )
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('user', hash_password('user123'))
            )
            print("Default users created: admin/admin123 and user/user123")
        
        conn.commit()
        print(f"Database initialized at {DB_PATH}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_user(username, password):
    """Create a new user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        if cursor.fetchone()[0] > 0:
            return False, "Username already exists"
        
        # Create new user
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, hash_password(password))
        )
        
        conn.commit()
        return True, "User created successfully"
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating user: {e}")
        return False, f"Error creating user: {str(e)}"
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = User.get_by_username(username)
    if user and user.check_password(password):
        return user
    return None

def migrate_json_to_sqlite():
    """One-time migration from JSON to SQLite (if JSON file exists)"""
    json_file = '/tmp/users.json'
    if not os.path.exists(json_file):
        return
    
    try:
        import json
        print(f"Found existing JSON user file at {json_file}, migrating to SQLite...")
        
        with open(json_file, 'r') as f:
            users = json.load(f)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for user_data in users:
            try:
                cursor.execute(
                    'INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)',
                    (user_data['username'], user_data['password_hash'])
                )
            except Exception as e:
                print(f"Error migrating user {user_data.get('username')}: {e}")
        
        conn.commit()
        conn.close()
        
        # Backup the JSON file
        backup_file = json_file + '.backup'
        os.rename(json_file, backup_file)
        print(f"Migration complete. JSON file backed up to {backup_file}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
