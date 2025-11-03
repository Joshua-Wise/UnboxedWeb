import os
import json
import zipfile
import shutil
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from app.mbox_parser import parse_mbox
from app.pdf_generator import generate_pdf, generate_separate_pdfs

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
ALLOWED_EXTENSIONS = {'mbox', 'mbx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
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

        if separate_pdfs:
            # Generate separate PDFs for each email
            temp_pdf_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'{base_filename}_pdfs')
            os.makedirs(temp_pdf_dir, exist_ok=True)

            pdf_files = generate_separate_pdfs(emails, temp_pdf_dir, base_filename, naming_config)

            if not pdf_files:
                return jsonify({'error': 'Failed to generate PDF files'}), 500

            # Create ZIP file
            output_filename = f"{base_filename}.zip"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(temp_pdf_dir, pdf_file)
                    zipf.write(pdf_path, pdf_file)

            # Clean up temporary PDF directory
            shutil.rmtree(temp_pdf_dir)

        else:
            # Generate single PDF with all emails
            output_filename = f"{base_filename}.pdf"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            generate_pdf(emails, output_path)

        # Clean up uploaded files
        for filepath in saved_filepaths:
            os.remove(filepath)

        return jsonify({
            'success': True,
            'filename': output_filename,
            'email_count': len(emails),
            'separate_pdfs': separate_pdfs
        })

    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/download/<filename>')
def download_file(filename):
    try:
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(output_path):
            return jsonify({'error': 'File not found'}), 404
        
        response = send_file(output_path, as_attachment=True, download_name=filename)
        
        # Clean up generated file after sending
        @response.call_on_close
        def cleanup():
            try:
                os.remove(output_path)
            except:
                pass
        
        return response
    
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
