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
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload an MBOX file'}), 400

    try:
        # Get settings from request
        settings_json = request.form.get('settings', '{}')
        settings = json.loads(settings_json)
        separate_pdfs = settings.get('separatePDFs', False)

        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse MBOX file
        emails = parse_mbox(filepath)

        if not emails:
            return jsonify({'error': 'No emails found in MBOX file'}), 400

        base_filename = os.path.splitext(filename)[0]

        if separate_pdfs:
            # Generate separate PDFs for each email
            temp_pdf_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'{base_filename}_pdfs')
            os.makedirs(temp_pdf_dir, exist_ok=True)

            pdf_files = generate_separate_pdfs(emails, temp_pdf_dir, base_filename)

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

        # Clean up uploaded file
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
