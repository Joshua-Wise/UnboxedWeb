from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
from io import BytesIO
import os
import re
import base64
from bs4 import BeautifulSoup
from app.attachment_handler import get_attachment_summary


def resolve_cid_images_in_html(html_content, inline_images):
    """Replace cid: image references with base64 encoded data URLs"""
    if not html_content or not inline_images:
        return html_content
    
    try:
        soup = BeautifulSoup(html_content, 'html5lib')
        
        # Find all img tags with cid: sources
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '')
            
            # Handle cid: references
            if src.startswith('cid:'):
                cid = src[4:]  # Remove 'cid:' prefix
                
                # Look up the image in inline_images
                if cid in inline_images:
                    attachment = inline_images[cid]
                    if attachment.processed_content:
                        # Convert image to base64 data URL
                        image_data = attachment.processed_content['image_data']
                        image_format = attachment.processed_content.get('format', 'PNG')
                        
                        # Create data URL
                        b64_data = base64.b64encode(image_data).decode('utf-8')
                        mime_type = f'image/{image_format.lower()}'
                        data_url = f'data:{mime_type};base64,{b64_data}'
                        
                        img_tag['src'] = data_url
                        print(f"Resolved CID image: {cid}")
                else:
                    print(f"Warning: CID image not found: {cid}")
        
        return str(soup)
    
    except Exception as e:
        print(f"Error resolving CID images: {str(e)}")
        return html_content


def convert_html_to_reportlab_format(html_content):
    """Convert HTML to ReportLab-friendly format, preserving important tags"""
    if not html_content:
        return ''
    
    try:
        soup = BeautifulSoup(html_content, 'html5lib')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'head']):
            tag.decompose()
        
        # Get body content if exists, otherwise use whole soup
        body = soup.find('body')
        if body:
            content = body
        else:
            content = soup
        
        # Convert to simplified HTML that ReportLab can handle
        # ReportLab supports: b, i, u, br, a, font, strong, em
        result = []
        
        for element in content.descendants:
            if isinstance(element, str):
                # Clean up text
                text = str(element)
                if text.strip():
                    result.append(text)
            elif element.name in ['br', 'p', 'div', 'tr']:
                if element.name != 'br':
                    result.append('<br/>')
        
        # Join and clean up
        html_text = ''.join(result)
        
        # Basic cleanup
        html_text = re.sub(r'\s+', ' ', html_text)  # Collapse whitespace
        html_text = re.sub(r'<br/>\s*<br/>\s*<br/>', '<br/><br/>', html_text)  # Limit consecutive breaks
        
        return html_text.strip()
    
    except Exception as e:
        print(f"Error converting HTML: {str(e)}")
        # Fallback to text extraction
        return BeautifulSoup(html_content, 'html.parser').get_text()


def render_html_content(story, html_content, inline_images, styles):
    """Render HTML content with inline images to PDF story"""
    try:
        # Resolve CID image references
        html_with_images = resolve_cid_images_in_html(html_content, inline_images)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_with_images, 'html5lib')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'head']):
            tag.decompose()
        
        # Get body content
        body = soup.find('body') or soup
        
        # Process content recursively
        process_html_element(story, body, inline_images, styles, quote_level=0)
        
    except Exception as e:
        print(f"Error rendering HTML: {str(e)}")
        # Fallback to plain text
        plain_text = BeautifulSoup(html_content, 'html.parser').get_text()
        paragraphs = plain_text.split('\n')
        body_style = styles['Normal']
        for para in paragraphs[:50]:
            if para.strip():
                story.append(Paragraph(clean_text(para.strip()), body_style))


def process_html_element(story, element, inline_images, styles, quote_level=0):
    """Process HTML element and convert to PDF flowables"""
    # Define styles with quote level indentation
    body_style = ParagraphStyle(
        'HTMLBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=8,
        spaceBefore=2,
        leftIndent=10 + (quote_level * 20),  # Indent quotes
        rightIndent=10,
        alignment=TA_LEFT,
        leading=14  # Increased line spacing
    )
    
    # Quoted text style with different color and subtle left border
    if quote_level > 0:
        body_style = ParagraphStyle(
            'QuotedText',
            parent=body_style,
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            leftIndent=15 + (quote_level * 15),  # Slightly less indentation
            leftBorderColor=colors.HexColor('#CCCCCC'),
            leftBorderWidth=2,
            leftBorderPadding=8,
            spaceAfter=6,
            spaceBefore=4
        )
    
    # Process child elements
    current_paragraph = []
    
    for child in element.children:
        if isinstance(child, str):
            text = str(child).strip()
            if text:
                current_paragraph.append(clean_text(text))
        
        elif child.name == 'blockquote':
            # Handle quoted content with increased quote level
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                if para_text.strip():
                    try:
                        story.append(Paragraph(para_text, body_style))
                    except:
                        story.append(Paragraph(escape_text(para_text), body_style))
                current_paragraph = []
            
            # Add small space before quote
            story.append(Spacer(1, 0.05*inch))
            
            # Process blockquote content with increased quote level
            process_html_element(story, child, inline_images, styles, quote_level + 1)
            
            # Add small space after quote
            story.append(Spacer(1, 0.05*inch))
        
        elif child.name in ['p', 'div', 'br']:
            # End current paragraph and start new one
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                if para_text.strip():
                    try:
                        story.append(Paragraph(para_text, body_style))
                    except:
                        story.append(Paragraph(escape_text(para_text), body_style))
                current_paragraph = []
            
            # Process the element's content
            if child.name != 'br':
                # Check if this div is a Gmail quote or similar
                is_quote = False
                if child.name == 'div':
                    class_attr = child.get('class', [])
                    if isinstance(class_attr, list):
                        class_str = ' '.join(class_attr)
                    else:
                        class_str = str(class_attr)
                    
                    # Check for common quote markers
                    if 'gmail_quote' in class_str.lower() or 'quoted' in class_str.lower():
                        is_quote = True
                
                # Process with appropriate quote level
                if is_quote:
                    story.append(Spacer(1, 0.05*inch))
                    process_html_element(story, child, inline_images, styles, quote_level + 1)
                    story.append(Spacer(1, 0.05*inch))
                else:
                    process_html_element(story, child, inline_images, styles, quote_level)
        
        elif child.name == 'img':
            # Handle inline images
            src = child.get('src', '')
            
            # Flush current paragraph
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                if para_text.strip():
                    try:
                        story.append(Paragraph(para_text, body_style))
                    except:
                        story.append(Paragraph(escape_text(para_text), body_style))
                current_paragraph = []
            
            # Add image
            if src.startswith('data:image'):
                try:
                    # Extract base64 data
                    match = re.search(r'data:image/[^;]+;base64,(.+)', src)
                    if match:
                        image_data = base64.b64decode(match.group(1))
                        img = Image(BytesIO(image_data))
                        
                        # Scale image to fit page
                        max_width = 6 * inch
                        max_height = 4 * inch
                        
                        if img.drawWidth > max_width:
                            aspect = img.drawHeight / img.drawWidth
                            img.drawWidth = max_width
                            img.drawHeight = max_width * aspect
                        
                        if img.drawHeight > max_height:
                            aspect = img.drawWidth / img.drawHeight
                            img.drawHeight = max_height
                            img.drawWidth = max_height * aspect
                        
                        img.hAlign = 'LEFT'
                        story.append(img)
                        story.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    print(f"Error embedding inline image: {str(e)}")
        
        elif child.name in ['b', 'strong']:
            text = child.get_text().strip()
            if text:
                current_paragraph.append(f'<b>{clean_text(text)}</b>')
        
        elif child.name in ['i', 'em']:
            text = child.get_text().strip()
            if text:
                current_paragraph.append(f'<i>{clean_text(text)}</i>')
        
        elif child.name in ['u']:
            text = child.get_text().strip()
            if text:
                current_paragraph.append(f'<u>{clean_text(text)}</u>')
        
        elif child.name == 'a':
            text = child.get_text().strip()
            href = child.get('href', '')
            if text:
                if href:
                    current_paragraph.append(f'<a href="{href}">{clean_text(text)}</a>')
                else:
                    current_paragraph.append(clean_text(text))
        
        elif child.name in ['table', 'ul', 'ol']:
            # Flush current paragraph before special elements
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                if para_text.strip():
                    try:
                        story.append(Paragraph(para_text, body_style))
                    except:
                        story.append(Paragraph(escape_text(para_text), body_style))
                current_paragraph = []
            
            # Simple handling - just extract text
            text = child.get_text('\n').strip()
            if text:
                for line in text.split('\n')[:20]:  # Limit lines
                    if line.strip():
                        try:
                            story.append(Paragraph(clean_text(line.strip()), body_style))
                        except:
                            story.append(Paragraph(escape_text(line.strip()), body_style))
        
        else:
            # Other elements - extract text
            text = child.get_text().strip() if hasattr(child, 'get_text') else str(child).strip()
            if text:
                current_paragraph.append(clean_text(text))
    
    # Flush remaining paragraph
    if current_paragraph:
        para_text = ' '.join(current_paragraph)
        if para_text.strip():
            try:
                story.append(Paragraph(para_text, body_style))
            except:
                story.append(Paragraph(escape_text(para_text), body_style))


def generate_pdf(emails, output_path, include_attachments=True, separate_attachments_zip=False):
    """Generate a PDF from a list of email dictionaries"""
    import tempfile
    
    # Check if we have PDF attachments that need merging
    has_pdf_attachments = False
    if include_attachments:
        for email in emails:
            if email.get('attachment_objects'):
                for attachment in email['attachment_objects']:
                    if attachment.embed_type == 'pdf' and attachment.processed_content:
                        has_pdf_attachments = True
                        break
            if has_pdf_attachments:
                break
    
    # If we have PDF attachments, generate to temp file first, then merge
    if has_pdf_attachments:
        print(f"PDF attachments detected. Using two-step generation process.")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # Generate base PDF to temp file
            print(f"Generating base PDF to temp file: {temp_path}")
            _generate_pdf_content(emails, temp_path, include_attachments, separate_attachments_zip)
            
            if not os.path.exists(temp_path):
                print(f"ERROR: Base PDF was not created at {temp_path}")
                raise Exception("Base PDF generation failed")
            
            # Merge PDF attachments into final output
            print(f"Merging PDF attachments into final output: {output_path}")
            merge_pdf_attachments_post_build(temp_path, emails, output_path)
            
            if os.path.exists(output_path):
                print(f"SUCCESS: Final PDF created at {output_path}")
            else:
                print(f"ERROR: Final PDF was not created at {output_path}")
        except Exception as e:
            print(f"ERROR in PDF generation with attachments: {str(e)}")
            # If temp file exists but final doesn't, copy it as fallback
            if os.path.exists(temp_path) and not os.path.exists(output_path):
                print(f"Fallback: Copying temp file to output")
                import shutil
                shutil.copy2(temp_path, output_path)
            raise
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"Cleaned up temp file: {temp_path}")
    else:
        # No PDF attachments, generate directly to output
        print(f"No PDF attachments detected. Generating directly to output.")
        _generate_pdf_content(emails, output_path, include_attachments, separate_attachments_zip)


def _generate_pdf_content(emails, output_path, include_attachments=True, separate_attachments_zip=False):
    """Internal function to generate PDF content"""
    
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
    
    # Custom styles with improved typography
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=16,
        spaceBefore=8,
        alignment=TA_LEFT,
        leading=22
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=10,
        spaceBefore=8,
        leftIndent=10,
        fontName='Helvetica-Bold',
        leading=14
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10,
        spaceBefore=2,
        leftIndent=10,
        rightIndent=10,
        alignment=TA_LEFT,
        leading=14
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
        
        # Email metadata table with enhanced styling
        metadata = []
        
        if email.get('from'):
            metadata.append(['From:', Paragraph(clean_text_for_table(email['from']), styles['Normal'])])
        
        if email.get('to'):
            metadata.append(['To:', Paragraph(clean_text_for_table(email['to']), styles['Normal'])])
        
        if email.get('cc'):
            metadata.append(['Cc:', Paragraph(clean_text_for_table(email['cc']), styles['Normal'])])
        
        if email.get('date'):
            metadata.append(['Date:', Paragraph(clean_text_for_table(email['date']), styles['Normal'])])
        
        if email.get('attachments'):
            if include_attachments:
                # When attachments are embedded, just show count
                attachment_count = len(email['attachments'])
                metadata.append(['Attachments:', Paragraph(f'{attachment_count} file(s) - see embedded content below', styles['Normal'])])
            else:
                # When attachments are not embedded, show full list
                attachments_str = ', '.join(email['attachments'])
                metadata.append(['Attachments:', Paragraph(clean_text_for_table(attachments_str), styles['Normal'])])
        
        if metadata:
            metadata_table = Table(metadata, colWidths=[1*inch, 5.5*inch])
            metadata_table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
                ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2C3E50')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#E8E8E8')),
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Email body
        story.append(Paragraph('<b>Message:</b>', header_style))
        
        # Check if HTML body is available
        has_html = email.get('has_html', False)
        body_html = email.get('body_html', '')
        inline_images = email.get('inline_images', {})
        
        if has_html and body_html:
            # Render HTML content with inline images
            try:
                render_html_content(story, body_html, inline_images, styles)
            except Exception as e:
                print(f"Error rendering HTML, falling back to plain text: {str(e)}")
                # Fallback to plain text
                body = email.get('body', '(No content)')
                if body:
                    body_paragraphs = body.split('\n')
                    for para in body_paragraphs:
                        cleaned_para = clean_text(para.strip())
                        if cleaned_para:
                            try:
                                story.append(Paragraph(cleaned_para, body_style))
                            except:
                                story.append(Paragraph(escape_text(cleaned_para), body_style))
        else:
            # Use plain text body
            body = email.get('body', '(No content)')
            if body:
                body_paragraphs = body.split('\n')
                for para in body_paragraphs:
                    cleaned_para = clean_text(para.strip())
                    if cleaned_para:
                        try:
                            story.append(Paragraph(cleaned_para, body_style))
                        except:
                            story.append(Paragraph(escape_text(cleaned_para), body_style))

        story.append(Spacer(1, 0.2*inch))

        # Embed attachments if present and enabled
        if include_attachments:
            embed_attachments_in_story(story, email, styles, separate_attachments_zip)

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


def clean_text_for_table(text):
    """Clean text for table cells (no XML escaping needed)"""
    if not text:
        return ''
    
    text = str(text)
    # Only escape ampersand to prevent issues
    text = text.replace('&', '&amp;')
    
    # Remove problematic line breaks
    text = text.replace('\r\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\n', ' ')
    
    # Limit length
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


def embed_attachments_in_story(story, email, styles, separate_attachments_zip=False):
    """Embed supported attachments into the PDF story"""
    attachment_objects = email.get('attachment_objects', [])

    if not attachment_objects:
        return

    # Get attachment summary
    attachment_summary = get_attachment_summary(attachment_objects)

    # Create attachment header style
    attachment_header_style = ParagraphStyle(
        'AttachmentHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=8,
        leftIndent=10,
        fontName='Helvetica-Bold'
    )

    attachment_text_style = ParagraphStyle(
        'AttachmentText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        leftIndent=20,
        fontName='Helvetica'
    )

    # Add attachments header
    story.append(Paragraph('<b>Attachments:</b>', attachment_header_style))

    # Display attachment summary table
    if attachment_summary:
        summary_data = [['Filename', 'Size', 'Type', 'Status']]
        for att in attachment_summary:
            summary_data.append([
                clean_text(att['filename'][:30] + '...' if len(att['filename']) > 30 else att['filename']),
                att['size'],
                clean_text(att['type'][:20] + '...' if len(att['type']) > 20 else att['type']),
                att['status']
            ])

        summary_table = Table(summary_data, colWidths=[2.5*inch, 0.8*inch, 1.5*inch, 1.7*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.1*inch))

    # Embed supported attachments
    embedded_count = 0
    for attachment in attachment_objects:
        if not attachment.is_supported or attachment.error_message:
            continue

        # Skip non-text attachments if they will be saved to a separate ZIP
        if separate_attachments_zip and attachment.embed_type != 'text':
            continue

        try:
            if attachment.embed_type == 'image' and attachment.processed_content:
                embed_image_attachment(story, attachment, attachment_text_style)
                embedded_count += 1

            elif attachment.embed_type == 'text' and attachment.processed_content:
                embed_text_attachment(story, attachment, attachment_text_style)
                embedded_count += 1

            elif attachment.embed_type == 'pdf' and attachment.processed_content:
                embed_pdf_attachment(story, attachment, attachment_text_style)
                embedded_count += 1

        except Exception as e:
            # Add error message for failed embeddings
            story.append(Paragraph(
                f'<b>Error embedding {attachment.filename}:</b> {str(e)}',
                attachment_text_style
            ))

    if embedded_count > 0:
        story.append(Spacer(1, 0.1*inch))


def embed_image_attachment(story, attachment, text_style):
    """Embed an image attachment into the PDF story"""
    try:
        # Add filename header
        story.append(Paragraph(f'<b>📷 {clean_text(attachment.filename)}</b>', text_style))

        # Create image from processed content
        image_data = attachment.processed_content['image_data']
        width = attachment.processed_content['width']
        height = attachment.processed_content['height']

        # Calculate display size (max 6 inches wide, maintain aspect ratio)
        max_width = 6 * inch
        max_height = 4 * inch

        aspect_ratio = width / height
        if width > height:
            display_width = min(max_width, width * 72 / 96)  # Convert pixels to points
            display_height = display_width / aspect_ratio
        else:
            display_height = min(max_height, height * 72 / 96)
            display_width = display_height * aspect_ratio

        # Create ReportLab Image from bytes
        img = Image(BytesIO(image_data), width=display_width, height=display_height)
        img.hAlign = 'LEFT'

        story.append(img)
        story.append(Spacer(1, 0.1*inch))

    except Exception as e:
        story.append(Paragraph(f'Error displaying image {attachment.filename}: {str(e)}', text_style))


def embed_text_attachment(story, attachment, text_style):
    """Embed a text attachment into the PDF story"""
    try:
        # Add filename header
        story.append(Paragraph(f'<b>📄 {clean_text(attachment.filename)}</b>', text_style))

        # Get processed text content
        text_content = attachment.processed_content['text']
        truncated = attachment.processed_content.get('truncated', False)

        # Add truncation notice if applicable
        if truncated:
            story.append(Paragraph('<i>[Content truncated due to length]</i>', text_style))

        # Split into paragraphs and add each
        paragraphs = text_content.split('\n')
        for para in paragraphs[:50]:  # Limit to 50 paragraphs to prevent huge documents
            cleaned_para = clean_text(para.strip())
            if cleaned_para:
                try:
                    story.append(Paragraph(cleaned_para, text_style))
                except:
                    story.append(Paragraph(escape_text(cleaned_para), text_style))

        if len(paragraphs) > 50:
            story.append(Paragraph('<i>[Additional content truncated for PDF size]</i>', text_style))

        story.append(Spacer(1, 0.1*inch))

    except Exception as e:
        story.append(Paragraph(f'Error displaying text file {attachment.filename}: {str(e)}', text_style))


def embed_pdf_attachment(story, attachment, text_style):
    """Add a note that PDF attachment will be merged"""
    try:
        # Add filename header with page count info
        page_count = attachment.processed_content.get('page_count', '?')
        size_mb = attachment.processed_content["size"] / (1024 * 1024)
        
        story.append(Paragraph(
            f'<b>{clean_text_for_table(attachment.filename)}</b> (PDF - {size_mb:.1f} MB, {page_count} page{"s" if page_count != 1 else ""})',
            text_style
        ))
        story.append(Paragraph(
            '<i>PDF attachment will be appended at the end of this document.</i>',
            text_style
        ))
        story.append(Spacer(1, 0.05*inch))

    except Exception as e:
        story.append(Paragraph(f'Error processing PDF {attachment.filename}: {str(e)}', text_style))


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


def generate_single_email_pdf(email, output_path, include_attachments=True, separate_attachments_zip=False):
    """Generate a PDF for a single email"""
    import tempfile

    # Check if we have PDF attachments that need merging
    has_pdf_attachments = False
    if include_attachments and email.get('attachment_objects'):
        for attachment in email['attachment_objects']:
            if attachment.embed_type == 'pdf' and attachment.processed_content:
                has_pdf_attachments = True
                break

    # If we have PDF attachments, generate to temp file first, then merge
    if has_pdf_attachments:
        print(f"PDF attachment detected in single email. Using two-step generation.")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            # Generate base PDF to temp file
            print(f"Generating base PDF to temp file: {temp_path}")
            _generate_single_email_pdf_content(email, temp_path, include_attachments, separate_attachments_zip)
            
            if not os.path.exists(temp_path):
                print(f"ERROR: Base PDF was not created at {temp_path}")
                raise Exception("Base PDF generation failed")
            
            # Merge PDF attachments into final output
            print(f"Merging PDF attachments into: {output_path}")
            merge_pdf_attachments_post_build(temp_path, [email], output_path)
            
            if os.path.exists(output_path):
                print(f"SUCCESS: Final PDF created at {output_path}")
            else:
                print(f"ERROR: Final PDF was not created at {output_path}")
        except Exception as e:
            print(f"ERROR in single email PDF generation: {str(e)}")
            # If temp file exists but final doesn't, copy it as fallback
            if os.path.exists(temp_path) and not os.path.exists(output_path):
                print(f"Fallback: Copying temp file to output")
                import shutil
                shutil.copy2(temp_path, output_path)
            raise
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"Cleaned up temp file")
    else:
        # No PDF attachments, generate directly to output
        _generate_single_email_pdf_content(email, output_path, include_attachments, separate_attachments_zip)


def _generate_single_email_pdf_content(email, output_path, include_attachments=True, separate_attachments_zip=False):
    """Internal function to generate single email PDF content"""

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

    # Custom styles with improved typography
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=16,
        spaceBefore=8,
        alignment=TA_LEFT,
        leading=22
    )

    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=10,
        spaceBefore=8,
        leftIndent=10,
        fontName='Helvetica-Bold',
        leading=14
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10,
        spaceBefore=2,
        leftIndent=10,
        rightIndent=10,
        alignment=TA_LEFT,
        leading=14
    )

    # Email subject
    subject = clean_text(email.get('subject', '(No Subject)'))
    story.append(Paragraph(f"<b>{subject}</b>", title_style))

    # Email metadata table
    metadata = []

    if email.get('from'):
        metadata.append(['From:', Paragraph(clean_text_for_table(email['from']), styles['Normal'])])

    if email.get('to'):
        metadata.append(['To:', Paragraph(clean_text_for_table(email['to']), styles['Normal'])])

    if email.get('cc'):
        metadata.append(['Cc:', Paragraph(clean_text_for_table(email['cc']), styles['Normal'])])

    if email.get('date'):
        metadata.append(['Date:', Paragraph(clean_text_for_table(email['date']), styles['Normal'])])

    if email.get('attachments'):
        if include_attachments:
            # When attachments are embedded, just show count
            attachment_count = len(email['attachments'])
            metadata.append(['Attachments:', Paragraph(f'{attachment_count} file(s) - see embedded content below', styles['Normal'])])
        else:
            # When attachments are not embedded, show full list
            attachments_str = ', '.join(email['attachments'])
            metadata.append(['Attachments:', Paragraph(clean_text_for_table(attachments_str), styles['Normal'])])

    if metadata:
        metadata_table = Table(metadata, colWidths=[1*inch, 5.5*inch])
        metadata_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2C3E50')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#E8E8E8')),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.2*inch))

    # Email body
    story.append(Paragraph('<b>Message:</b>', header_style))
    
    # Check if HTML body is available
    has_html = email.get('has_html', False)
    body_html = email.get('body_html', '')
    inline_images = email.get('inline_images', {})
    
    if has_html and body_html:
        # Render HTML content with inline images
        try:
            render_html_content(story, body_html, inline_images, styles)
        except Exception as e:
            print(f"Error rendering HTML, falling back to plain text: {str(e)}")
            # Fallback to plain text
            body = email.get('body', '(No content)')
            if body:
                body_paragraphs = body.split('\n')
                for para in body_paragraphs:
                    cleaned_para = clean_text(para.strip())
                    if cleaned_para:
                        try:
                            story.append(Paragraph(cleaned_para, body_style))
                        except:
                            story.append(Paragraph(escape_text(cleaned_para), body_style))
    else:
        # Use plain text body
        body = email.get('body', '(No content)')
        if body:
            body_paragraphs = body.split('\n')
            for para in body_paragraphs:
                cleaned_para = clean_text(para.strip())
                if cleaned_para:
                    try:
                        story.append(Paragraph(cleaned_para, body_style))
                    except:
                        story.append(Paragraph(escape_text(cleaned_para), body_style))

    story.append(Spacer(1, 0.2*inch))

    # Embed attachments if present and enabled
    if include_attachments:
        embed_attachments_in_story(story, email, styles)

    story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)


def merge_pdf_attachments_post_build(base_pdf_path, emails, output_path):
    """Merge PDF attachments after main PDF is built"""
    from pypdf import PdfReader, PdfWriter
    import tempfile
    import shutil
    
    try:
        # Check if there are any PDF attachments to merge
        has_pdf_attachments = False
        for email in emails:
            if email.get('attachment_objects'):
                for attachment in email['attachment_objects']:
                    if attachment.embed_type == 'pdf' and attachment.processed_content:
                        has_pdf_attachments = True
                        break
            if has_pdf_attachments:
                break
        
        # If no PDF attachments, just copy the base file
        if not has_pdf_attachments:
            shutil.copy2(base_pdf_path, output_path)
            return
        
        writer = PdfWriter()
        
        # Add base PDF pages
        try:
            base_reader = PdfReader(base_pdf_path)
            for page in base_reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"Error reading base PDF: {str(e)}")
            # Fall back to copying the base file
            shutil.copy2(base_pdf_path, output_path)
            return
        
        # Add PDF attachment pages after the main content
        for email in emails:
            if email.get('attachment_objects'):
                for attachment in email['attachment_objects']:
                    if attachment.embed_type == 'pdf' and attachment.processed_content:
                        try:
                            pdf_data = attachment.processed_content['pdf_data']
                            # Create temp file for attachment
                            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                                tmp.write(pdf_data)
                                tmp_path = tmp.name
                            
                            try:
                                att_reader = PdfReader(tmp_path)
                                for page in att_reader.pages:
                                    writer.add_page(page)
                            finally:
                                os.unlink(tmp_path)
                        except Exception as e:
                            print(f"Warning: Failed to merge PDF attachment {attachment.filename}: {str(e)}")
                            continue
        
        # Write final merged PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
            
    except Exception as e:
        print(f"Critical error in PDF merge process: {str(e)}")
        # Emergency fallback: copy base file if it exists
        if os.path.exists(base_pdf_path):
            try:
                shutil.copy2(base_pdf_path, output_path)
                print(f"Fallback: Copied base PDF without merged attachments")
            except Exception as copy_error:
                print(f"Failed to copy base PDF: {str(copy_error)}")
                raise


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


def generate_separate_pdfs(emails, output_dir, base_filename, naming_config=None, include_attachments=True, separate_attachments_zip=False):
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
            generate_single_email_pdf(email, output_path, include_attachments, separate_attachments_zip)
            pdf_files.append(filename)
        except Exception as e:
            print(f"Error generating PDF for email {idx + 1}: {str(e)}")
            continue

    return pdf_files
