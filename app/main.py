import os
import json
import zipfile
import shutil
import threading
import time
import gc
from urllib.parse import unquote
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.mbox_parser import parse_mbox
from app.pdf_generator import generate_pdf, generate_separate_pdfs
from app.users import User, authenticate_user, init_db, migrate_json_to_sqlite, admin_required, get_all_users, create_user, delete_user, update_user_password, toggle_admin_status
from app.file_manager import register_file, get_user_files, get_file_info, delete_file_record, get_stats_for_user, cleanup_orphaned_files
from app.attachment_handler import create_attachments_zip

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
ALLOWED_EXTENSIONS = {'mbox', 'mbx'}
FILE_CLEANUP_DELAY = 3600  # 1 hour in seconds

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize database on startup
print("Initializing database...")
init_db()
migrate_json_to_sqlite()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def schedule_file_cleanup(file_path, delay_seconds=FILE_CLEANUP_DELAY):
    """Schedule file deletion after a delay using a background thread"""
    def delayed_cleanup():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Failed to cleanup file {file_path}: {str(e)}")

    # Start cleanup in a daemon thread so it doesn't prevent app shutdown
    cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
    cleanup_thread.start()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = authenticate_user(username, password)
        if user:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # Check for multiple files (new format) or single file (backward compatibility)
    files = request.files.getlist('files')
    if not files or (len(files) == 1 and files[0].filename == ''):
        # Try old single file format for backward compatibility
        if 'file' in request.files:
            files = [request.files['file']]
        else:
            return jsonify({'error': 'No files provided'}), 400

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400

    # Validate all files
    for file in files:
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type: {file.filename}. Please upload only MBOX files'}), 400

    try:
        # Get settings from request
        settings_json = request.form.get('settings', '{}')
        settings = json.loads(settings_json)
        separate_pdfs = settings.get('separatePDFs', False)
        include_attachments = settings.get('includeAttachments', True)
        separate_attachments_zip = settings.get('separateAttachmentsZip', False)
        naming_config = settings.get('naming', {
            'items': [
                {'id': 'subject', 'enabled': True},
                {'id': 'date', 'enabled': False},
                {'id': 'sender', 'enabled': False}
            ]
        })

        # Process all MBOX files and collect emails
        all_emails = []
        saved_filepaths = []

        for file in files:
            # Save uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_filepaths.append(filepath)

            # Parse MBOX file
            emails = parse_mbox(filepath)

            # Add source file information to each email
            source_name = os.path.splitext(filename)[0]
            for email in emails:
                email['source_file'] = source_name

            all_emails.extend(emails)

        # Use all emails from all files
        emails = all_emails

        if not emails:
            return jsonify({'error': 'No emails found in MBOX files'}), 400

        # Generate output filename based on number of source files
        if len(files) == 1:
            base_filename = os.path.splitext(files[0].filename)[0]
        else:
            base_filename = f'combined_{len(files)}_mbox_files'

        # Create separate attachments ZIP if requested
        attachments_zip_path = None
        attachment_count = 0
        if separate_attachments_zip:
            temp_attachments_zip = f"{base_filename}_attachments_temp.zip"
            attachments_zip_path = os.path.join(app.config['OUTPUT_FOLDER'], temp_attachments_zip)

            success, attachment_count, error_msg = create_attachments_zip(emails, attachments_zip_path)

            if success:
                print(f"Created attachments ZIP with {attachment_count} attachments")
            else:
                # No attachments to save
                print(f"No attachments ZIP created: {error_msg}")
                attachments_zip_path = None
                attachment_count = 0

        if separate_pdfs:
            # Generate separate PDFs for each email
            temp_pdf_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'{base_filename}_pdfs')
            os.makedirs(temp_pdf_dir, exist_ok=True)

            pdf_files = generate_separate_pdfs(emails, temp_pdf_dir, base_filename, naming_config, include_attachments, separate_attachments_zip)

            if not pdf_files:
                return jsonify({'error': 'Failed to generate PDF files'}), 500

            # Create ZIP file with PDFs
            output_filename = f"{base_filename}.zip"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(temp_pdf_dir, pdf_file)
                    zipf.write(pdf_path, pdf_file)
                
                # Add attachments ZIP to the main ZIP if it exists
                if attachments_zip_path and os.path.exists(attachments_zip_path):
                    zipf.write(attachments_zip_path, 'attachments.zip')
                    print(f"Added attachments.zip to main ZIP")

            # Clean up temporary PDF directory
            shutil.rmtree(temp_pdf_dir)

        else:
            # Generate single PDF with all emails
            # If attachments ZIP exists, we need to create a ZIP containing both
            if attachments_zip_path and os.path.exists(attachments_zip_path):
                # Create a ZIP containing the PDF and attachments ZIP
                pdf_filename = f"{base_filename}.pdf"
                temp_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
                generate_pdf(emails, temp_pdf_path, include_attachments, separate_attachments_zip)
                
                # Create the final ZIP
                output_filename = f"{base_filename}.zip"
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(temp_pdf_path, pdf_filename)
                    zipf.write(attachments_zip_path, 'attachments.zip')
                    print(f"Created ZIP with PDF and attachments")
                
                # Clean up temporary PDF
                os.remove(temp_pdf_path)
            else:
                # No attachments ZIP, just create the PDF
                output_filename = f"{base_filename}.pdf"
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                generate_pdf(emails, output_path, include_attachments, separate_attachments_zip)

        # Clean up temporary attachments ZIP if it exists
        if attachments_zip_path and os.path.exists(attachments_zip_path):
            os.remove(attachments_zip_path)
            print(f"Cleaned up temporary attachments ZIP")

        # Clean up uploaded files
        for filepath in saved_filepaths:
            os.remove(filepath)

        # Determine original mbox name for file tracking
        original_mbox_name = files[0].filename if len(files) == 1 else f'{len(files)} MBOX files'

        # Register file with user ownership
        file_type = 'zip' if (separate_pdfs or (separate_attachments_zip and attachment_count > 0)) else 'pdf'
        register_file(
            filename=output_filename,
            user_id=current_user.id,
            file_type=file_type,
            email_count=len(emails),
            separate_pdfs=separate_pdfs,
            original_mbox_name=original_mbox_name
        )
        
        # Store email count before cleanup
        email_count = len(emails)
        
        # Force garbage collection to free memory after large file processing
        del emails
        del all_emails
        gc.collect()
        print(f"Memory cleanup completed after processing {email_count} emails")

        response_data = {
            'success': True,
            'filename': output_filename,
            'email_count': email_count,
            'separate_pdfs': separate_pdfs
        }

        # Include attachment count if attachments were saved
        if attachment_count > 0:
            response_data['attachment_count'] = attachment_count
            response_data['attachments_bundled'] = True

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/files')
@login_required
def files():
    user_files = get_user_files(current_user.id)
    stats = get_stats_for_user(current_user.id)

    # Clean up orphaned files from database
    cleanup_orphaned_files()

    message = request.args.get('message')
    success = request.args.get('success', 'false') == 'true'

    return render_template('files.html', files=user_files, stats=stats, message=message, success=success)


@app.route('/delete-file', methods=['POST'])
@login_required
def delete_file():
    filename = request.form.get('filename')
    if not filename:
        return redirect(url_for('files', message='No filename provided', success='false'))

    # Check if file belongs to current user
    file_info = get_file_info(filename)
    if not file_info or file_info.get('user_id') != current_user.id:
        return redirect(url_for('files', message='File not found or access denied', success='false'))

    # Delete file
    success = delete_file_record(filename)
    if success:
        return redirect(url_for('files', message='File deleted successfully', success='true'))
    else:
        return redirect(url_for('files', message='Failed to delete file', success='false'))


@app.route('/download/<filename>')
@login_required
def download_file(filename):
    try:
        # Decode URL-encoded filename (e.g., %40 -> @)
        decoded_filename = unquote(filename)

        # Security check: prevent directory traversal attacks
        if '..' in decoded_filename or '/' in decoded_filename or '\\' in decoded_filename:
            return jsonify({'error': 'Invalid filename'}), 400

        # Check if file belongs to current user
        file_info = get_file_info(decoded_filename)
        if not file_info or file_info.get('user_id') != current_user.id:
            return jsonify({'error': 'File not found or access denied'}), 404

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], decoded_filename)

        if not os.path.exists(output_path):
            return jsonify({'error': 'File not found'}), 404

        response = send_file(output_path, as_attachment=True, download_name=decoded_filename)

        # No automatic cleanup - files persist until manually deleted by user

        return response

    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin panel for user management"""
    return render_template('admin.html')


@app.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        users = get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def create_new_user():
    """Create a new user (admin only)"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        is_admin = data.get('is_admin', False)

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400

        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        success, message = create_user(username, password, is_admin)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users/delete', methods=['POST'])
@login_required
@admin_required
def delete_user_endpoint():
    """Delete a user (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400

        # Prevent deleting yourself
        if int(user_id) == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400

        success, message = delete_user(user_id)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users/update-password', methods=['POST'])
@login_required
@admin_required
def update_password_endpoint():
    """Update a user's password (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_password = data.get('new_password', '').strip()

        if not user_id or not new_password:
            return jsonify({'success': False, 'error': 'User ID and new password are required'}), 400

        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        success, message = update_user_password(user_id, new_password)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_endpoint():
    """Toggle admin status for a user (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400

        # Prevent changing your own admin status
        if int(user_id) == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot change your own admin status'}), 400

        success, message = toggle_admin_status(user_id)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


@app.route('/admin/clear-memory', methods=['POST'])
@login_required
@admin_required
def clear_memory():
    """Force garbage collection to free memory (admin only)"""
    try:
        # Force garbage collection
        collected = gc.collect()
        
        return jsonify({
            'success': True,
            'message': f'Garbage collection completed. Collected {collected} objects.',
            'objects_collected': collected
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
