import json
import os
import time
from datetime import datetime

# File to store file ownership and metadata
FILES_DB = '/tmp/files.json'

def load_files_db():
    """Load file database"""
    if not os.path.exists(FILES_DB):
        return {}

    try:
        with open(FILES_DB, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_files_db(files_db):
    """Save file database"""
    try:
        with open(FILES_DB, 'w') as f:
            json.dump(files_db, f, indent=2)
    except Exception as e:
        print(f"Error saving files database: {e}")

def register_file(filename, user_id, file_type='pdf', email_count=0, separate_pdfs=False, original_mbox_name=None):
    """Register a new file with user ownership"""
    files_db = load_files_db()

    file_info = {
        'filename': filename,
        'user_id': user_id,
        'file_type': file_type,  # 'pdf' or 'zip'
        'email_count': email_count,
        'separate_pdfs': separate_pdfs,
        'original_mbox_name': original_mbox_name,
        'created_at': datetime.now().isoformat(),
        'file_size': get_file_size(filename)
    }

    files_db[filename] = file_info
    save_files_db(files_db)
    return file_info

def get_user_files(user_id):
    """Get all files owned by a specific user"""
    files_db = load_files_db()
    user_files = []

    for filename, file_info in files_db.items():
        if file_info.get('user_id') == user_id:
            # Check if file still exists
            output_path = os.path.join('/tmp/outputs', filename)
            if os.path.exists(output_path):
                # Update file size in case it changed
                file_info['file_size'] = get_file_size(filename)
                file_info['exists'] = True
                user_files.append(file_info)
            else:
                file_info['exists'] = False
                user_files.append(file_info)

    # Sort by creation date (newest first)
    user_files.sort(key=lambda x: x['created_at'], reverse=True)
    return user_files

def get_file_info(filename):
    """Get file information"""
    files_db = load_files_db()
    return files_db.get(filename)

def delete_file_record(filename):
    """Delete file from database and filesystem"""
    files_db = load_files_db()

    if filename in files_db:
        # Delete from filesystem
        output_path = os.path.join('/tmp/outputs', filename)
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")

        # Remove from database
        del files_db[filename]
        save_files_db(files_db)
        return True

    return False

def cleanup_orphaned_files():
    """Remove database entries for files that no longer exist"""
    files_db = load_files_db()
    orphaned = []

    for filename in files_db.keys():
        output_path = os.path.join('/tmp/outputs', filename)
        if not os.path.exists(output_path):
            orphaned.append(filename)

    for filename in orphaned:
        del files_db[filename]

    if orphaned:
        save_files_db(files_db)

    return len(orphaned)

def get_file_size(filename):
    """Get file size in bytes"""
    try:
        output_path = os.path.join('/tmp/outputs', filename)
        if os.path.exists(output_path):
            return os.path.getsize(output_path)
    except:
        pass
    return 0

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"

def get_stats_for_user(user_id):
    """Get file statistics for a user"""
    user_files = get_user_files(user_id)

    total_files = len(user_files)
    total_size = sum(f['file_size'] for f in user_files if f['exists'])
    pdf_files = len([f for f in user_files if f['file_type'] == 'pdf' and f['exists']])
    zip_files = len([f for f in user_files if f['file_type'] == 'zip' and f['exists']])

    return {
        'total_files': total_files,
        'total_size': total_size,
        'total_size_formatted': format_file_size(total_size),
        'pdf_files': pdf_files,
        'zip_files': zip_files,
        'existing_files': len([f for f in user_files if f['exists']])
    }