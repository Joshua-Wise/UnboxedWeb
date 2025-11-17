# UnboxedWeb - MBOX to PDF Converter

A powerful, containerized web application that converts MBOX email archive files to beautifully formatted PDF documents with full HTML rendering, inline images, and embedded attachments.

## Features

### Email Processing
- **HTML Email Rendering** - Preserves original HTML formatting, styles, and layout
- **Inline Image Support** - Automatically embeds inline images referenced in emails (CID resolution)
- **Flexible Attachment Handling** - Choose to embed attachments in PDF or bundle them separately
- **Smart Attachment Processing** - Automatically detects and handles images, PDFs, text files, and binary documents
- **Email Threading** - Intelligent quote detection and formatting for email conversations
- **Batch Processing** - Combine multiple MBOX files into a single PDF or generate separate PDFs
- **Custom PDF Naming** - Configure filename format with subject, date, and sender combinations
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
- **Persistent Storage** - Files remain available until manually deleted
- **Settings Panel** - Customizable conversion options saved per user

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
2. Click the Settings gear icon to configure conversion options:
   - **Generate Separate PDF per Email** - Create individual PDFs per email (bundled as ZIP)
     - Configure custom filename format (subject, date, sender)
     - Reorder naming components with drag-and-drop
   - **Embed Attachments** - Embed supported attachments directly in the PDF
   - **Save non-text attachments to separate ZIP** - Bundle attachments separately
3. Upload MBOX file(s) via drag-and-drop or file browser
4. Click "Process Files" to start conversion
5. Wait for the conversion to complete
6. Download your PDF(s)
7. View conversion history in "My Files"

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

### Attachment Handling

The application intelligently processes different attachment types:

#### Text Attachments (Embeddable)
- **Text Files**: `.txt`, `.csv`, `.xml`, `.rtf`
- **HTML Files**: `.html`, `.htm`
- These are embedded in the PDF when "Embed Attachments" is enabled

#### Non-Text Attachments (Embeddable or Bundled)
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`
- **PDF Documents**: Merged into the main PDF document
- **Office Documents**: `.xlsx`, `.docx`, `.pptx` (bundled in ZIP)
- **Other Binary Files**: Any unsupported file types

#### Attachment Options

**When "Embed Attachments" is checked:**
- Text files are embedded directly in the PDF with formatting
- Images are resized and embedded inline
- PDF attachments are merged at the end of the document

**When "Save non-text attachments to separate ZIP" is checked:**
- Non-text attachments (images, PDFs, Office docs, etc.) are bundled in `attachments.zip`
- The ZIP file is included in your download
- Organized by email with folder structure: `email_00001_Subject/filename.ext`

**When both are checked (Recommended):**
- Text attachments are embedded in the PDF for easy reading
- All other attachments are saved to `attachments.zip` for preservation
- Best of both worlds - readable PDF + original files preserved

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

### File Management

Files are stored persistently and managed through the "My Files" interface. Users can:
- View all their converted files
- Download files at any time
- Delete files manually when no longer needed
- See statistics on total conversions and file sizes

Note: Files are not automatically deleted - users maintain full control over their data.

## Conversion Settings

The application provides a comprehensive settings panel accessible via the gear icon:

### PDF Generation Options
- **Generate Separate PDF per Email**
  - Creates one PDF file per email
  - All PDFs are bundled in a ZIP file
  - Configure custom filename patterns (subject, date, sender)
  - Drag-and-drop to reorder filename components

### Attachment Handling Options
- **Embed Attachments**
  - Embeds supported attachments directly in the PDF
  - Images are resized and optimized
  - Text files are formatted for readability
  - PDF attachments are merged at the end

- **Save non-text attachments to separate ZIP**
  - Creates an `attachments.zip` file within your download
  - Preserves original file formats
  - Organized by email in separate folders
  - Includes images, PDFs, Office docs, and binary files

Settings are saved in your browser and persist between sessions.

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

4. Access at `http://localhost:5000`

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
- `GET /admin/users` - Get all users (JSON)
- `POST /admin/users/create` - Create new user
- `POST /admin/users/delete` - Delete user
- `POST /admin/users/update-password` - Reset user password
- `POST /admin/users/toggle-admin` - Toggle admin status
- `POST /admin/clear-memory` - Force garbage collection

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

## Troubleshooting

### Common Issues

**Problem: PDFs not rendering HTML correctly**
- Solution: The application uses html5lib for parsing. Most HTML emails should render correctly, but very complex CSS may not be fully supported.

**Problem: Large MBOX files causing memory issues**
- Solution: The application includes automatic garbage collection after processing. For very large files (>1GB), consider splitting the MBOX file first.

**Problem: Attachments not appearing in PDF**
- Solution: Check that "Embed Attachments" is enabled in settings. Some attachment types (like .exe files) are not supported for security reasons.

**Problem: Can't download files**
- Solution: Ensure the user who created the conversion is logged in. Files are user-specific for security.

**Problem: Docker container fails to start**
- Solution: Check that port 8080 is not already in use. Modify the port mapping in `docker-compose.yml` if needed.

### Logs

View application logs:
```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f mbox-converter
```

## Security Considerations

- Change the default admin password immediately after first login
- Use a strong `SECRET_KEY` in production (set via environment variable)
- Files are user-isolated - users can only access their own conversions
- Uploaded files are processed and deleted immediately after conversion
- Generated files persist until manually deleted by the user

## Performance

- **Small MBOX files** (<10MB): Process in seconds
- **Medium MBOX files** (10-100MB): Process in under a minute
- **Large MBOX files** (100MB-1GB): May take several minutes
- **Very large MBOX files** (>1GB): Consider splitting the file first

The application includes memory optimization:
- Automatic garbage collection after processing
- Temporary file cleanup
- Efficient streaming for large attachments

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is provided as-is for personal and commercial use.