import hashlib
import sqlite3
import os
from flask_login import UserMixin
from functools import wraps
from flask import abort
from flask_login import current_user

# SQLite database path in persistent volume
DB_PATH = '/app/data/users.db'

class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=False):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin

    def check_password(self, password):
        """Check if provided password matches the stored hash"""
        return self.password_hash == hash_password(password)

    @staticmethod
    def get(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash, is_admin FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2], bool(row[3]))
            return None
        finally:
            conn.close()

    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash, is_admin FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2], bool(row[3]))
            return None
        finally:
            conn.close()

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

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
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Check if is_admin column exists (migration for existing databases)
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_admin' not in columns:
            print("Adding is_admin column to users table...")
            cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
            # Make the first admin user (username='admin') an admin
            cursor.execute('UPDATE users SET is_admin = 1 WHERE username = ?', ('admin',))
            print("Migration complete: is_admin column added")

        # Check if any users exist
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]

        # Create default users if no users exist
        if user_count == 0:
            print("Creating default users...")
            cursor.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('admin', hash_password('admin123'), 1)
            )
            cursor.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('user', hash_password('user123'), 0)
            )
            print("Default users created: admin/admin123 (admin) and user/user123 (regular user)")

        conn.commit()
        print(f"Database initialized at {DB_PATH}")

    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_user(username, password, is_admin=False):
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
            'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
            (username, hash_password(password), 1 if is_admin else 0)
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

def get_all_users():
    """Get all users (admin only)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, is_admin, created_at FROM users ORDER BY id')
        rows = cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'is_admin': bool(row[2]),
                'created_at': row[3]
            })
        return users
    finally:
        conn.close()

def delete_user(user_id):
    """Delete a user by ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Prevent deleting the last admin
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_count = cursor.fetchone()[0]

        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

        if user and user[0] and admin_count <= 1:
            return False, "Cannot delete the last admin user"

        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        if cursor.rowcount == 0:
            return False, "User not found"

        conn.commit()
        return True, "User deleted successfully"

    except Exception as e:
        conn.rollback()
        print(f"Error deleting user: {e}")
        return False, f"Error deleting user: {str(e)}"
    finally:
        conn.close()

def update_user_password(user_id, new_password):
    """Update a user's password"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (hash_password(new_password), user_id)
        )

        if cursor.rowcount == 0:
            return False, "User not found"

        conn.commit()
        return True, "Password updated successfully"

    except Exception as e:
        conn.rollback()
        print(f"Error updating password: {e}")
        return False, f"Error updating password: {str(e)}"
    finally:
        conn.close()

def toggle_admin_status(user_id):
    """Toggle admin status for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Prevent removing admin from the last admin
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

        if user and user[0]:  # If currently admin
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                return False, "Cannot remove admin status from the last admin user"

        cursor.execute(
            'UPDATE users SET is_admin = NOT is_admin WHERE id = ?',
            (user_id,)
        )

        if cursor.rowcount == 0:
            return False, "User not found"

        conn.commit()
        return True, "Admin status updated successfully"

    except Exception as e:
        conn.rollback()
        print(f"Error updating admin status: {e}")
        return False, f"Error updating admin status: {str(e)}"
    finally:
        conn.close()
