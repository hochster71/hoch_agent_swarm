import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class PdfExporter:
    def export_pdf(self, title: str, paragraphs: list, filepath: str) -> str:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Dark Theme styling
        title_style = ParagraphStyle(
            'DarkTitle',
            parent=styles['Title'],
            textColor=colors.HexColor('#10b981'),
            fontSize=24,
            leading=28,
            spaceAfter=15
        )
        body_style = ParagraphStyle(
            'DarkBody',
            parent=styles['BodyText'],
            textColor=colors.HexColor('#1f2937'),
            fontSize=11,
            leading=14,
            spaceAfter=10
        )
        
        story = [Paragraph(title, title_style), Spacer(1, 10)]
        for p in paragraphs:
            story.append(Paragraph(p, body_style))
            
        doc.build(story)
        return filepath
