import mailbox
import email
from email.utils import parsedate_to_datetime
from email.header import decode_header
import html
import re
from app.attachment_handler import extract_attachments_from_message, process_image_attachment, AttachmentInfo


def decode_email_header(header):
    """Decode email header that might be encoded"""
    if header is None:
        return ''
    
    decoded_parts = decode_header(header)
    decoded_string = ''
    
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                decoded_string += part.decode(encoding or 'utf-8', errors='replace')
            except:
                decoded_string += part.decode('utf-8', errors='replace')
        else:
            decoded_string += str(part)
    
    return decoded_string


def get_email_body(message):
    """Extract email body from message, preferring HTML for better rendering"""
    plain_body = ''
    html_body = ''
    
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            
            # Skip attachments
            if 'attachment' in content_disposition:
                continue
            
            # Skip inline images (they'll be handled separately)
            content_id = part.get('Content-ID')
            if content_id and content_type.startswith('image/'):
                continue
            
            if content_type == 'text/plain' and not plain_body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        plain_body = payload.decode(charset, errors='replace')
                except:
                    pass
            elif content_type == 'text/html' and not html_body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='replace')
                except:
                    pass
    else:
        try:
            payload = message.get_payload(decode=True)
            if payload:
                charset = message.get_content_charset() or 'utf-8'
                content_type = message.get_content_type()
                if content_type == 'text/html':
                    html_body = payload.decode(charset, errors='replace')
                else:
                    plain_body = payload.decode(charset, errors='replace')
        except:
            plain_body = str(message.get_payload())
    
    # Return both HTML and plain text, prefer HTML if available
    return {
        'html': html_body.strip() if html_body else '',
        'plain': plain_body.strip() if plain_body else '',
        'has_html': bool(html_body)
    }


def strip_html_tags(html_text):
    """Simple HTML tag stripper"""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Unescape HTML entities
    text = html.unescape(text)
    return text


def extract_inline_images(message):
    """Extract inline images with Content-ID mappings from email message"""
    inline_images = {}
    
    if not message.is_multipart():
        return inline_images
    
    for part in message.walk():
        content_type = part.get_content_type()
        content_id = part.get('Content-ID')
        content_disposition = str(part.get('Content-Disposition', ''))
        
        # Look for inline images (have Content-ID and are images)
        # NOTE: Even if marked as "attachment", if it has a Content-ID, 
        # it's likely referenced in the HTML and should be treated as inline
        if content_id and content_type.startswith('image/'):
            
            try:
                # Clean up Content-ID (remove < and > brackets)
                cid = content_id.strip('<>')
                
                # Get image data
                image_data = part.get_payload(decode=True)
                if not image_data:
                    continue
                
                # Get filename if available
                filename = part.get_filename() or f'inline_image_{cid}.jpg'
                
                # Create an AttachmentInfo object for the inline image
                attachment = AttachmentInfo(
                    filename=filename,
                    content_type=content_type,
                    content_data=image_data,
                    size=len(image_data),
                    is_supported=True,
                    embed_type='image'
                )
                
                # Process the image (resize, format conversion, etc.)
                try:
                    process_image_attachment(attachment)
                    if attachment.processed_content:
                        inline_images[cid] = attachment
                        print(f"Extracted inline image with CID: {cid} ({filename}, {len(image_data)} bytes)")
                except Exception as e:
                    print(f"Error processing inline image {cid}: {str(e)}")
                    continue
                    
            except Exception as e:
                print(f"Error extracting inline image: {str(e)}")
                continue
    
    return inline_images


def parse_mbox(filepath):
    """Parse MBOX file and extract email data"""
    emails = []
    
    try:
        mbox = mailbox.mbox(filepath)
        
        for idx, message in enumerate(mbox):
            try:
                # Extract basic headers
                subject = decode_email_header(message.get('Subject', '(No Subject)'))
                from_addr = decode_email_header(message.get('From', ''))
                to_addr = decode_email_header(message.get('To', ''))
                cc_addr = decode_email_header(message.get('Cc', ''))
                date_str = message.get('Date', '')
                
                # Parse date
                try:
                    date_obj = parsedate_to_datetime(date_str)
                    date_formatted = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    date_formatted = date_str
                
                # Get email body (returns dict with html and plain text)
                body_data = get_email_body(message)
                
                # Extract inline images with Content-ID mappings
                inline_images = extract_inline_images(message)
                
                # Extract full attachment information including content
                attachment_objects = extract_attachments_from_message(message)

                # Create legacy attachments list for backward compatibility
                attachments = [att.filename for att in attachment_objects]
                
                email_data = {
                    'index': idx + 1,
                    'subject': subject,
                    'from': from_addr,
                    'to': to_addr,
                    'cc': cc_addr,
                    'date': date_formatted,
                    'body': body_data.get('plain', ''),  # Legacy plain text body
                    'body_html': body_data.get('html', ''),  # HTML body
                    'has_html': body_data.get('has_html', False),  # Flag for HTML availability
                    'inline_images': inline_images,  # Inline images with CID mappings
                    'attachments': attachments,  # Legacy list of filenames
                    'attachment_objects': attachment_objects  # Full attachment data with content
                }
                
                emails.append(email_data)
            
            except Exception as e:
                # Skip problematic emails but continue processing
                print(f"Error parsing email {idx + 1}: {str(e)}")
                continue
        
        mbox.close()
    
    except Exception as e:
        raise Exception(f"Error reading MBOX file: {str(e)}")
    
    return emails
