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


def generate_separate_pdfs(emails, output_dir, base_filename):
    """Generate separate PDF files for each email and return list of filenames"""

    pdf_files = []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for idx, email in enumerate(emails):
        # Create filename based on email subject
        subject = email.get('subject', 'No Subject')
        safe_subject = sanitize_filename(subject)

        # Create unique filename with index to avoid duplicates
        filename = f"{idx+1:03d}_{safe_subject}.pdf"
        output_path = os.path.join(output_dir, filename)

        try:
            generate_single_email_pdf(email, output_path)
            pdf_files.append(filename)
        except Exception as e:
            print(f"Error generating PDF for email {idx + 1}: {str(e)}")
            continue

    return pdf_files
