import mailbox
import email
from email.utils import parsedate_to_datetime
from email.header import decode_header
import html
from app.attachment_handler import extract_attachments_from_message


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
    """Extract email body from message"""
    body = ''
    
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            
            # Skip attachments
            if 'attachment' in content_disposition:
                continue
            
            if content_type == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='replace')
                except:
                    pass
            elif content_type == 'text/html' and not body:
                # Use HTML only if no plain text found
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='replace')
                        # Strip HTML tags for plain text version
                        body += strip_html_tags(html_body)
                except:
                    pass
    else:
        try:
            payload = message.get_payload(decode=True)
            if payload:
                charset = message.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
        except:
            body = str(message.get_payload())
    
    return body.strip()


def strip_html_tags(html_text):
    """Simple HTML tag stripper"""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Unescape HTML entities
    text = html.unescape(text)
    return text


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
                
                # Get email body
                body = get_email_body(message)
                
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
                    'body': body,
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
