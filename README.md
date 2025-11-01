# MBOX to PDF Converter

A containerized web application that converts MBOX email archive files to PDF documents.

## Features

- Convert MBOX files containing multiple emails to a single PDF
- Clean, modern web interface with drag-and-drop support
- Fully containerized with Docker
- Responsive design for mobile and desktop
- Automatic file cleanup after download
- Health check endpoint for monitoring
- Email metadata extraction (From, To, Cc, Date, Subject)
- Attachment listing in PDF
- Support for various email encodings

## Prerequisites

- Docker
- Docker Compose (optional, for easier deployment)

## Quick Start

### Using Docker Compose (Recommended)

1. Clone this repository:
```bash
git clone <repository-url>
cd PDFbox
```

2. Start the application:
```bash
docker-compose up -d
```

3. Access the application at: `http://localhost:8080`

4. Stop the application:
```bash
docker-compose down
```

### Using Docker

1. Build the image:
```bash
docker build -t mbox-to-pdf-converter .
```

2. Run the container:
```bash
docker run -d -p 5000:5000 --name mbox-converter mbox-to-pdf-converter
```

3. Access the application at: `http://localhost:8080`

4. Stop the container:
```bash
docker stop mbox-converter
docker rm mbox-converter
```

## Usage

1. Open your web browser and navigate to `http://localhost:8080`
2. Either drag and drop your MBOX file onto the upload area, or click to browse and select a file
3. Wait for the conversion to complete
4. Download the generated PDF file
5. Optionally convert another file

## Supported File Formats

- `.mbox` - Standard MBOX format
- `.mbx` - Alternative MBOX extension

## File Size Limits

- Maximum file size: 50MB
- Can be adjusted in `app/main.py` by modifying `MAX_FILE_SIZE`

## Configuration

### Environment Variables

- `FLASK_APP` - Flask application module (default: `app.main`)
- `PYTHONUNBUFFERED` - Python output buffering (default: `1`)

### Port Configuration

To change the default port (5000), modify:
- `docker-compose.yml`: Update the `ports` mapping
- `Dockerfile`: Update the `EXPOSE` directive

### Storage Volumes

By default, uploaded and generated files are stored in temporary directories inside the container. To persist files:

```yaml
volumes:
  - ./uploads:/tmp/uploads
  - ./outputs:/tmp/outputs
```

## Development

### Local Development (without Docker)

1. Install Python 3.11+
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m app.main
```

4. Access at `http://localhost:8080`

### Project Structure

```
PDFbox/
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask application
│   ├── mbox_parser.py       # MBOX parsing logic
│   ├── pdf_generator.py     # PDF generation logic
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Styling
│   │   └── js/
│   │       └── app.js       # Frontend logic
│   └── templates/
│       └── index.html       # Main interface
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker Compose configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Health Check

The application includes a health check endpoint:

```bash
curl http://localhost:8080/health
```

Response: `{"status": "healthy"}`

## API Endpoints

- `GET /` - Main application interface
- `POST /upload` - Upload and convert MBOX file
- `GET /download/<filename>` - Download converted PDF
- `GET /health` - Health check endpoint

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs -f
```

### File upload fails

- Ensure file is a valid MBOX format
- Check file size is under 50MB
- Verify the file extension is `.mbox` or `.mbx`

### PDF generation fails

- Check if MBOX file contains valid email data
- Look for encoding issues in the MBOX file
- Review application logs for detailed error messages

## Technologies Used

- **Backend**: Python 3.11, Flask
- **PDF Generation**: ReportLab
- **Email Parsing**: Python mailbox library
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose

## Security Notes

- Files are automatically deleted after download
- No persistent storage of uploaded files by default
- File size limits prevent DoS attacks
- File type validation on both frontend and backend

## License

This project is provided as-is for educational and practical purposes.

## Support

For issues, questions, or contributions, please open an issue in the repository.
