from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
import os
import re


def generate_pdf(emails, output_path):
    """Generate a PDF from a list of email dictionaries"""
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=TA_LEFT
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=6,
        leftIndent=10
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=12,
        leftIndent=10,
        alignment=TA_LEFT
    )
    
    # Add title page
    story.append(Paragraph("MBOX Email Archive", title_style))
    story.append(Paragraph(f"Total Emails: {len(emails)}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Process each email
    for idx, email in enumerate(emails):
        # Add separator line
        if idx > 0:
            story.append(PageBreak())
        
        # Email number and subject
        subject = clean_text(email.get('subject', '(No Subject)'))
        story.append(Paragraph(f"<b>Email {email['index']}: {subject}</b>", title_style))
        
        # Email metadata table
        metadata = []
        
        if email.get('from'):
            metadata.append(['From:', clean_text(email['from'])])
        
        if email.get('to'):
            metadata.append(['To:', clean_text(email['to'])])
        
        if email.get('cc'):
            metadata.append(['Cc:', clean_text(email['cc'])])
        
        if email.get('date'):
            metadata.append(['Date:', clean_text(email['date'])])
        
        if email.get('attachments'):
            attachments_str = ', '.join(email['attachments'])
            metadata.append(['Attachments:', clean_text(attachments_str)])
        
        if metadata:
            metadata_table = Table(metadata, colWidths=[1*inch, 5.5*inch])
            metadata_table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
                ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#000000')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Email body
        body = email.get('body', '(No content)')
        if body:
            story.append(Paragraph('<b>Message:</b>', header_style))
            
            # Split body into paragraphs and add each
            body_paragraphs = body.split('\n')
            for para in body_paragraphs:
                cleaned_para = clean_text(para.strip())
                if cleaned_para:
                    try:
                        story.append(Paragraph(cleaned_para, body_style))
                    except:
                        # Fallback for problematic text
                        story.append(Paragraph(escape_text(cleaned_para), body_style))
        
        story.append(Spacer(1, 0.2*inch))
    
    # Build PDF
    doc.build(story)


def clean_text(text):
    """Clean text for PDF rendering"""
    if not text:
        return ''
    
    # Replace special XML/HTML characters
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Remove or replace problematic characters
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Limit very long lines
    if len(text) > 10000:
        text = text[:10000] + '... [truncated]'
    
    return text


def escape_text(text):
    """More aggressive text escaping for problematic content"""
    if not text:
        return ''

    # Convert to string and escape everything
    result = []
    for char in str(text):
        if ord(char) < 128 and char.isprintable():
            if char in '&<>':
                result.append('&amp;' if char == '&' else '&lt;' if char == '<' else '&gt;')
            else:
                result.append(char)
        elif char in '\n\t':
            result.append(char)
        else:
            result.append(' ')

    return ''.join(result)


def sanitize_filename(text, max_length=50):
    """Sanitize text to be used as a filename"""
    if not text:
        return 'untitled'

    # Remove or replace invalid filename characters
    text = str(text)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text)

    # Remove leading/trailing spaces and dots
    text = text.strip('. ')

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    # If empty after sanitization, use default
    if not text:
        text = 'untitled'

    return text


def generate_single_email_pdf(email, output_path):
    """Generate a PDF for a single email"""

    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Container for PDF elements
    story = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=TA_LEFT
    )

    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=6,
        leftIndent=10
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=12,
        leftIndent=10,
        alignment=TA_LEFT
    )

    # Email subject
    subject = clean_text(email.get('subject', '(No Subject)'))
    story.append(Paragraph(f"<b>{subject}</b>", title_style))

    # Email metadata table
    metadata = []

    if email.get('from'):
        metadata.append(['From:', clean_text(email['from'])])

    if email.get('to'):
        metadata.append(['To:', clean_text(email['to'])])

    if email.get('cc'):
        metadata.append(['Cc:', clean_text(email['cc'])])

    if email.get('date'):
        metadata.append(['Date:', clean_text(email['date'])])

    if email.get('attachments'):
        attachments_str = ', '.join(email['attachments'])
        metadata.append(['Attachments:', clean_text(attachments_str)])

    if metadata:
        metadata_table = Table(metadata, colWidths=[1*inch, 5.5*inch])
        metadata_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#000000')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.2*inch))

    # Email body
    body = email.get('body', '(No content)')
    if body:
        story.append(Paragraph('<b>Message:</b>', header_style))

        # Split body into paragraphs and add each
        body_paragraphs = body.split('\n')
        for para in body_paragraphs:
            cleaned_para = clean_text(para.strip())
            if cleaned_para:
                try:
                    story.append(Paragraph(cleaned_para, body_style))
                except:
                    # Fallback for problematic text
                    story.append(Paragraph(escape_text(cleaned_para), body_style))

    story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)


def build_custom_filename(email, idx, naming_config):
    """Build custom filename based on naming configuration with order support"""
    # Start with 6-digit index (always included)
    parts = [f"{idx+1:06d}"]

    # Get naming items (supports both old and new format)
    items = naming_config.get('items', [])

    # Fallback to old format if items not present
    if not items:
        # Convert old format to new format for backward compatibility
        items = []
        if naming_config.get('includeSubject', True):
            items.append({'id': 'subject', 'enabled': True})
        if naming_config.get('includeDate', False):
            items.append({'id': 'date', 'enabled': True})
        if naming_config.get('includeSender', False):
            items.append({'id': 'sender', 'enabled': True})

    # Process items in order
    for item in items:
        if not item.get('enabled', False):
            continue

        item_id = item.get('id', '')

        if item_id == 'subject':
            subject = email.get('subject', 'No Subject')
            safe_subject = sanitize_filename(subject, max_length=50)
            parts.append(safe_subject)

        elif item_id == 'date':
            date_str = email.get('date', '')
            if date_str:
                # Try to extract just the date part (YYYY-MM-DD)
                try:
                    # If it's already formatted as YYYY-MM-DD HH:MM:SS, just take the date part
                    if ' ' in date_str:
                        date_part = date_str.split(' ')[0]
                    else:
                        date_part = date_str[:10]  # First 10 chars should be the date
                    safe_date = sanitize_filename(date_part, max_length=20)
                    parts.append(safe_date)
                except:
                    # Fallback: sanitize the entire date string
                    safe_date = sanitize_filename(date_str, max_length=20)
                    parts.append(safe_date)

        elif item_id == 'sender':
            sender = email.get('from', '')
            if sender:
                # Extract email address or name from "Name <email@example.com>" format
                # If it contains <, extract the part before it; otherwise use as-is
                if '<' in sender:
                    sender_part = sender.split('<')[0].strip()
                    if not sender_part:  # If name is empty, use email
                        sender_part = sender.split('<')[1].split('>')[0].strip()
                else:
                    sender_part = sender
                safe_sender = sanitize_filename(sender_part, max_length=30)
                parts.append(safe_sender)

    # Join all parts with underscores
    filename = '_'.join(parts) + '.pdf'
    return filename


def generate_separate_pdfs(emails, output_dir, base_filename, naming_config=None):
    """Generate separate PDF files for each email and return list of filenames"""

    # Default naming config if not provided
    if naming_config is None:
        naming_config = {
            'items': [
                {'id': 'subject', 'enabled': True},
                {'id': 'date', 'enabled': False},
                {'id': 'sender', 'enabled': False}
            ]
        }

    pdf_files = []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for idx, email in enumerate(emails):
        # Create filename based on naming configuration
        filename = build_custom_filename(email, idx, naming_config)
        output_path = os.path.join(output_dir, filename)

        try:
            generate_single_email_pdf(email, output_path)
            pdf_files.append(filename)
        except Exception as e:
            print(f"Error generating PDF for email {idx + 1}: {str(e)}")
            continue

    return pdf_files
