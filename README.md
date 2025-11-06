# UnboxedWeb - MBOX to PDF Converter

A powerful, containerized web application that converts MBOX email archive files to beautifully formatted PDF documents with full HTML rendering, inline images, and embedded attachments.

## Features

### Email Processing
- **HTML Email Rendering** - Preserves original HTML formatting, styles, and layout
- **Inline Image Support** - Automatically embeds inline images referenced in emails (CID resolution)
- **Attachment Embedding** - Embeds images, PDFs, and text files directly into the generated PDF
- **Email Threading** - Intelligent quote detection and formatting for email conversations
- **Batch Processing** - Combine multiple MBOX files into a single PDF or generate separate PDFs
- **Rich Metadata** - Extracts and displays From, To, Cc, Date, Subject, and attachment information

### User Management
- **Authentication System** - Secure login with Flask-Login
- **Admin Panel** - User management interface for administrators
- **Role-Based Access** - Admin and standard user roles
- **File History** - Track conversion history per user
- **Statistics Dashboard** - View processing stats and file management

### Interface & UX
- **Modern Web UI** - Clean, responsive design for desktop and mobile
- **Drag-and-Drop Upload** - Easy file upload with visual feedback
- **Real-Time Progress** - Live updates during conversion
- **File Manager** - Browse, download, and delete previous conversions
- **Smart File Cleanup** - Automatic cleanup of old files after 1 hour

### Technical Features
- **Fully Containerized** - Docker-based deployment
- **SQLite Database** - Persistent user and file metadata storage
- **Health Check Endpoint** - Built-in monitoring support
- **Multiple Email Encodings** - Handles various character encodings
- **Image Processing** - Automatic resizing and format conversion
- **PDF Merging** - Combines multiple PDF attachments

## Prerequisites

- Docker
- Docker Compose (optional, for easier deployment)

## Quick Start

### Using Docker Compose (Recommended)

1. Clone this repository:
```bash
git clone <repository-url>
cd UnboxedWeb
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
docker run -d -p 8080:5000 --name mbox-converter mbox-to-pdf-converter
```

3. Access the application at: `http://localhost:8080`

4. Stop the container:
```bash
docker stop mbox-converter
docker rm mbox-converter
```

## Usage

### First Time Setup

1. Open your web browser and navigate to `http://localhost:8080`
2. Log in with default admin credentials (admin / admin123)
3. Create user accounts through the Admin panel

### Converting MBOX Files

1. Log in to your account
2. Upload MBOX file(s) via drag-and-drop or file browser
3. Choose conversion options:
   - **Combine into One PDF** - Merge all emails into a single document
   - **Generate Separate PDFs** - Create individual PDFs per email (downloads as ZIP)
4. Wait for the conversion to complete
5. Download your PDF(s)
6. View conversion history in "My Files"

### Admin Functions

Administrators can:
- Create new user accounts
- Reset user passwords
- Toggle admin privileges
- Delete user accounts
- View all system activity

## Supported File Formats

### Input
- `.mbox` - Standard MBOX format
- `.mbx` - Alternative MBOX extension

### Embedded Attachments
- **Images**: JPEG, PNG, GIF, BMP, TIFF (automatically embedded)
- **PDFs**: Merged into the main PDF document
- **Text Files**: Rendered with proper formatting
- **Other Files**: Listed in attachment table with metadata

## Configuration

### Environment Variables

```bash
FLASK_APP=app.main              # Flask application module
PYTHONUNBUFFERED=1              # Python output buffering
SECRET_KEY=your-secret-key      # Change in production!
```

### Port Configuration

Default port: `5000` (mapped to `8080` on host)

To change ports, modify:
- `docker-compose.yml`: Update the `ports` mapping
- `Dockerfile`: Update the `EXPOSE` directive

### Storage Volumes

Persistent storage is configured in `docker-compose.yml`:

```yaml
volumes:
  - ./data:/app/data  # SQLite database and user data
```

### File Cleanup Settings

Modify `FILE_CLEANUP_DELAY` in `app/main.py`:
```python
FILE_CLEANUP_DELAY = 3600  # 1 hour in seconds
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

## API Endpoints

### Public Endpoints
- `GET /login` - Login page
- `POST /login` - Authenticate user

### Authenticated Endpoints
- `GET /` - Main upload interface
- `POST /upload` - Upload and convert MBOX file(s)
- `GET /download/<filename>` - Download generated PDF
- `GET /files` - View file history
- `POST /delete_file/<file_id>` - Delete file
- `GET /logout` - Log out

### Admin Endpoints
- `GET /admin` - Admin panel
- `POST /admin/create_user` - Create new user
- `POST /admin/delete_user` - Delete user
- `POST /admin/update_password` - Reset user password
- `POST /admin/toggle_admin` - Toggle admin status

### System Endpoints
- `GET /health` - Health check endpoint

## Technologies Used

### Backend
- **Python 3.11** - Core application language
- **Flask 3.0** - Web framework
- **Flask-Login** - User session management
- **SQLite** - User and file metadata database

### PDF & Email Processing
- **ReportLab** - PDF generation and styling
- **BeautifulSoup4** - HTML parsing
- **html5lib** - HTML5 parsing support
- **Pillow (PIL)** - Image processing and embedding
- **pypdf** - PDF merging for attachments
- **Python mailbox** - MBOX file parsing

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Modern styling with responsive design
- **JavaScript (Vanilla)** - Interactive UI elements
- **Bootstrap 5** - UI components (admin panel)

### Containerization
- **Docker** - Application containerization
- **Docker Compose** - Multi-container orchestration