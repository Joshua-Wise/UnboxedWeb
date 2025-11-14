import os
import base64
import mimetypes
import tempfile
import zipfile
import re
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from PIL import Image
import io

# Supported attachment types for embedding
SUPPORTED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'
}

SUPPORTED_TEXT_TYPES = {
    'text/plain', 'text/html', 'text/csv', 'text/xml', 'text/rtf'
}

SUPPORTED_DOCUMENT_TYPES = {
    'application/pdf'
}

ALL_SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_TEXT_TYPES | SUPPORTED_DOCUMENT_TYPES

class AttachmentInfo:
    """Class to hold attachment information and content"""
    def __init__(self, filename, content_type, content_data, size, is_supported=False, embed_type=None):
        self.filename = filename
        self.content_type = content_type
        self.content_data = content_data
        self.size = size
        self.is_supported = is_supported
        self.embed_type = embed_type  # 'image', 'text', 'pdf', 'unsupported'
        self.processed_content = None
        self.error_message = None

def extract_attachments_from_message(message):
    """Extract all attachments from an email message"""
    attachments = []

    if not message.is_multipart():
        return attachments

    for part in message.walk():
        content_disposition = str(part.get('Content-Disposition', ''))

        if 'attachment' in content_disposition:
            filename = part.get_filename()
            if filename:
                try:
                    # Get content type with improved detection
                    content_type = part.get_content_type()

                    # If content type is generic or missing, try to guess from filename
                    if not content_type or content_type in ['application/octet-stream', 'application/binary']:
                        guessed_type = mimetypes.guess_type(filename)[0]
                        if guessed_type:
                            content_type = guessed_type
                        else:
                            content_type = 'application/octet-stream'

                    # Additional fallback: check file extension for common image types
                    if content_type == 'application/octet-stream' and filename:
                        ext = filename.lower().split('.')[-1] if '.' in filename else ''
                        if ext in ['jpg', 'jpeg']:
                            content_type = 'image/jpeg'
                        elif ext in ['png']:
                            content_type = 'image/png'
                        elif ext in ['gif']:
                            content_type = 'image/gif'
                        elif ext in ['bmp']:
                            content_type = 'image/bmp'
                        elif ext in ['tiff', 'tif']:
                            content_type = 'image/tiff'
                        elif ext in ['txt']:
                            content_type = 'text/plain'
                        elif ext in ['html', 'htm']:
                            content_type = 'text/html'
                        elif ext in ['csv']:
                            content_type = 'text/csv'
                        elif ext in ['pdf']:
                            content_type = 'application/pdf'

                    # Get attachment content
                    content_data = part.get_payload(decode=True)
                    if not content_data:
                        continue

                    # Content-based MIME type detection for images
                    if content_type == 'application/octet-stream' and len(content_data) > 10:
                        # Check for image file signatures
                        if content_data.startswith(b'\xff\xd8\xff'):  # JPEG
                            content_type = 'image/jpeg'
                        elif content_data.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                            content_type = 'image/png'
                        elif content_data.startswith(b'GIF87a') or content_data.startswith(b'GIF89a'):  # GIF
                            content_type = 'image/gif'
                        elif content_data.startswith(b'BM'):  # BMP
                            content_type = 'image/bmp'
                        elif content_data.startswith(b'II*\x00') or content_data.startswith(b'MM\x00*'):  # TIFF
                            content_type = 'image/tiff'
                        elif content_data.startswith(b'%PDF'):  # PDF
                            content_type = 'application/pdf'

                    # Debug logging for troubleshooting
                    print(f"Processing attachment: {filename}")
                    print(f"  - Detected content type: {content_type}")
                    print(f"  - File size: {len(content_data)} bytes")

                    # Determine if supported and embedding type
                    is_supported = content_type.lower() in ALL_SUPPORTED_TYPES
                    embed_type = get_embed_type(content_type)

                    print(f"  - Is supported: {is_supported}")
                    print(f"  - Embed type: {embed_type}")

                    attachment = AttachmentInfo(
                        filename=filename,
                        content_type=content_type,
                        content_data=content_data,
                        size=len(content_data),
                        is_supported=is_supported,
                        embed_type=embed_type
                    )

                    # Process the attachment for embedding
                    if is_supported:
                        try:
                            process_attachment_for_embedding(attachment)
                        except Exception as e:
                            print(f"Error processing attachment {filename}: {str(e)}")
                            attachment.error_message = f"Processing error: {str(e)}"
                            attachment.is_supported = False

                    attachments.append(attachment)

                except Exception as e:
                    # Create an error attachment entry
                    error_attachment = AttachmentInfo(
                        filename=filename or 'unknown',
                        content_type='error',
                        content_data=None,
                        size=0,
                        is_supported=False,
                        embed_type='error'
                    )
                    error_attachment.error_message = f"Error extracting attachment: {str(e)}"
                    attachments.append(error_attachment)

    return attachments

def get_embed_type(content_type):
    """Determine the embedding type based on content type"""
    content_type = content_type.lower()

    if content_type in SUPPORTED_IMAGE_TYPES:
        return 'image'
    elif content_type in SUPPORTED_TEXT_TYPES:
        return 'text'
    elif content_type in SUPPORTED_DOCUMENT_TYPES:
        return 'pdf'
    else:
        return 'unsupported'

def process_attachment_for_embedding(attachment):
    """Process attachment content for embedding into PDF"""
    try:
        if attachment.embed_type == 'image':
            process_image_attachment(attachment)
        elif attachment.embed_type == 'text':
            process_text_attachment(attachment)
        elif attachment.embed_type == 'pdf':
            process_pdf_attachment(attachment)

    except Exception as e:
        attachment.error_message = f"Error processing {attachment.embed_type} attachment: {str(e)}"
        attachment.is_supported = False

def process_image_attachment(attachment):
    """Process image attachment for embedding"""
    try:
        # Check file size limit (max 20MB for images)
        max_file_size = 20 * 1024 * 1024  # 20MB
        if attachment.size > max_file_size:
            raise Exception(f"Image file too large ({attachment.size / (1024*1024):.1f}MB). Maximum size is 20MB.")

        # Open image with PIL
        image = Image.open(io.BytesIO(attachment.content_data))

        # Convert to RGB if necessary (for PDF compatibility)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        # Resize if too large (max 800px width/height)
        max_size = 800
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Convert back to bytes
        img_byte_arr = io.BytesIO()
        format_map = {
            'image/jpeg': 'JPEG',
            'image/jpg': 'JPEG',
            'image/png': 'PNG',
            'image/gif': 'PNG',  # Convert GIF to PNG for PDF
            'image/bmp': 'PNG',  # Convert BMP to PNG for PDF
            'image/tiff': 'PNG'  # Convert TIFF to PNG for PDF
        }

        output_format = format_map.get(attachment.content_type.lower(), 'PNG')
        image.save(img_byte_arr, format=output_format, quality=85)

        attachment.processed_content = {
            'image_data': img_byte_arr.getvalue(),
            'width': image.width,
            'height': image.height,
            'format': output_format
        }

    except Exception as e:
        raise Exception(f"Failed to process image: {str(e)}")

def process_text_attachment(attachment):
    """Process text attachment for embedding"""
    try:
        # Decode text content
        text_content = attachment.content_data.decode('utf-8', errors='replace')

        # Limit text length for PDF (max 10,000 characters)
        max_chars = 10000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + '\n\n... [Content truncated due to length] ...'

        # Basic HTML stripping for HTML files
        if attachment.content_type.lower() == 'text/html':
            text_content = strip_html_tags(text_content)

        attachment.processed_content = {
            'text': text_content,
            'original_length': len(attachment.content_data),
            'truncated': len(attachment.content_data.decode('utf-8', errors='replace')) > max_chars
        }

    except Exception as e:
        raise Exception(f"Failed to process text: {str(e)}")

def process_pdf_attachment(attachment):
    """Process PDF attachment for embedding"""
    try:
        # Check file size limit (max 50MB for PDFs)
        max_file_size = 50 * 1024 * 1024  # 50MB
        if attachment.size > max_file_size:
            raise Exception(f"PDF file too large ({attachment.size / (1024*1024):.1f}MB). Maximum size is 50MB.")
        
        # Validate PDF format by checking header
        if not attachment.content_data.startswith(b'%PDF'):
            raise Exception("Invalid PDF file format - missing PDF header")
        
        # Try to validate PDF is readable using pypdf
        try:
            from pypdf import PdfReader
            import io
            
            pdf_reader = PdfReader(io.BytesIO(attachment.content_data))
            page_count = len(pdf_reader.pages)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                raise Exception("Encrypted PDFs are not supported")
            
        except Exception as e:
            if "Encrypted" in str(e):
                raise
            raise Exception(f"PDF validation failed: {str(e)}")
        
        # Store PDF data for later embedding
        attachment.processed_content = {
            'pdf_data': attachment.content_data,
            'size': len(attachment.content_data),
            'page_count': page_count
        }

    except Exception as e:
        raise Exception(f"Failed to process PDF: {str(e)}")

def strip_html_tags(html_text):
    """Simple HTML tag stripper"""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Unescape HTML entities
    import html
    text = html.unescape(text)
    return text

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

def get_attachment_summary(attachments):
    """Get a summary of attachments for display"""
    if not attachments:
        return []

    summary = []
    for attachment in attachments:
        status = "✓ Embedded" if attachment.is_supported and not attachment.error_message else "⚠ Listed only"
        if attachment.error_message:
            status = "✗ Error"

        summary.append({
            'filename': attachment.filename,
            'size': format_file_size(attachment.size),
            'type': attachment.content_type,
            'status': status,
            'embed_type': attachment.embed_type,
            'error': attachment.error_message
        })

    return summary

def is_non_text_attachment(attachment):
    """Determine if an attachment is non-text (image or document)"""
    return attachment.embed_type in ['image', 'pdf']

def sanitize_filename(filename):
    """Sanitize filename for safe file system operations"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length to 200 characters
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename

def create_attachments_zip(emails, output_path):
    """
    Create a ZIP file containing all non-text attachments from emails

    Args:
        emails: List of email dictionaries containing attachments
        output_path: Path where the ZIP file should be created

    Returns:
        tuple: (success: bool, attachment_count: int, error_message: str or None)
    """
    try:
        attachment_count = 0

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for email_idx, email in enumerate(emails, start=1):
                attachments = email.get('attachments', [])

                if not attachments:
                    continue

                # Create a folder name for this email
                email_subject = email.get('subject', 'No Subject')
                # Sanitize subject for use in folder name
                safe_subject = sanitize_filename(email_subject)
                # Truncate subject to reasonable length for folder name
                if len(safe_subject) > 50:
                    safe_subject = safe_subject[:50]

                folder_name = f"email_{email_idx:05d}_{safe_subject}"

                # Track attachment filenames in this email to handle duplicates
                used_filenames = {}

                for attachment in attachments:
                    # Only include non-text attachments (images and PDFs)
                    if not is_non_text_attachment(attachment):
                        continue

                    # Skip attachments with errors
                    if attachment.error_message:
                        continue

                    # Get the original filename
                    filename = attachment.filename
                    safe_filename = sanitize_filename(filename)

                    # Handle duplicate filenames within the same email
                    if safe_filename in used_filenames:
                        used_filenames[safe_filename] += 1
                        name, ext = os.path.splitext(safe_filename)
                        safe_filename = f"{name}_{used_filenames[safe_filename]}{ext}"
                    else:
                        used_filenames[safe_filename] = 0

                    # Create the path in the ZIP file
                    zip_path = f"{folder_name}/{safe_filename}"

                    # Write the attachment to the ZIP
                    zipf.writestr(zip_path, attachment.content_data)
                    attachment_count += 1

                    print(f"Added attachment to ZIP: {zip_path} ({format_file_size(attachment.size)})")

        if attachment_count == 0:
            # No attachments were added, remove the empty ZIP file
            if os.path.exists(output_path):
                os.remove(output_path)
            return False, 0, "No non-text attachments found to save"

        print(f"Created attachments ZIP with {attachment_count} attachments at {output_path}")
        return True, attachment_count, None

    except Exception as e:
        error_msg = f"Error creating attachments ZIP: {str(e)}"
        print(error_msg)
        # Clean up partial ZIP file if it exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return False, 0, error_msg