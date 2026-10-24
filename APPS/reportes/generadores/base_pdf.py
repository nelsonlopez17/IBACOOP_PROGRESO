"""
reportes/generadores/base_pdf.py

Motor maestro de generación de reportes ejecutivos en PDF con ReportLab.
Provee:
  - NumberedCanvas: Numeración automática de páginas a dos pasadas ("Página X de Y").
  - Paleta institucional IBACOOP.
  - Membrete oficial del Instituto y acreditación MINEDUC.
  - Bloques estandarizados de firmas de conformidad y responsabilidad.
"""
import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

COLOR_VERDE = colors.HexColor('#1E6532')
COLOR_ROJO = colors.HexColor('#7A1C21')
COLOR_AZUL = colors.HexColor('#3C7DA8')
COLOR_TEXT = colors.HexColor('#0F172A')
COLOR_MUTED = colors.HexColor('#64748B')
COLOR_BG_LIGHT = colors.HexColor('#F8FAFC')
COLOR_BORDER = colors.HexColor('#E2E8F0')


class NumberedCanvas(canvas.Canvas):
    """
    Canvas personalizado para calcular y dibujar la numeración de páginas
    en dos pasadas ('Página X de Y') y pie de página institucional inmutable.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColor(COLOR_MUTED)
        
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(36, 28, self._pagesize[0] - 36, 28)

        pie_izq = "IBACOOP EL PROGRESO — Sistema de Gestión Escolar ERP • Documento Oficial Foliado"
        self.drawString(36, 18, pie_izq)

        pie_der = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(self._pagesize[0] - 36, 18, pie_der)

        self.restoreState()


class ReportLabHelper:
    """Utilidades y estilos para la construcción de reportes institucionales."""

    @staticmethod
    def get_styles():
        styles = getSampleStyleSheet()
        return {
            'title': ParagraphStyle('RepTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=15, textColor=COLOR_VERDE),
            'subtitle': ParagraphStyle('RepSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=COLOR_MUTED),
            'badge': ParagraphStyle('RepBadge', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=COLOR_ROJO),
            'section_heading': ParagraphStyle('RepSecH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=COLOR_VERDE),
            'th': ParagraphStyle('RepTH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white, alignment=1),
            'td': ParagraphStyle('RepTD', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, textColor=COLOR_TEXT),
            'td_center': ParagraphStyle('RepTDC', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, textColor=COLOR_TEXT, alignment=1),
            'td_bold': ParagraphStyle('RepTDB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=COLOR_TEXT),
            'td_right': ParagraphStyle('RepTDR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=COLOR_TEXT, alignment=2),
            'notes': ParagraphStyle('RepNotes', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, leading=9, textColor=COLOR_MUTED),
        }

    @classmethod
    def build_header(cls, doc_title, subtitle=None, orientation_landscape=False):
        """Genera el encabezado oficial del Instituto 'El Progreso'."""
        styles = cls.get_styles()
        width = 720 if orientation_landscape else 540

        header_data = [
            [
                Paragraph("<b>INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO' (IBACOOP)</b><br/>"
                          "<font size=7 color='#64748B'>Resolución MINEDUC No. 02-08-0044-45 • Cooperativa de Enseñanza</font><br/>"
                          f"<b>{doc_title.upper()}</b>" + (f"<br/><font size=7 color='#7A1C21'>{subtitle}</font>" if subtitle else ""),
                          styles['title']),
                Paragraph(f"<b>FECHA DE EMISIÓN:</b><br/>{timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
                          f"<b>ESTADO:</b> OFICIAL / VÁLIDO",
                          styles['subtitle'])
            ]
        ]
        
        t_header = Table(header_data, colWidths=[width - 150, 150])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        return t_header

    @classmethod
    def build_signature_block(cls, labels, orientation_landscape=False):
        """Genera un bloque de firmas foliadas para 2 o 3 responsables."""
        styles = cls.get_styles()
        width = 720 if orientation_landscape else 540
        num_cols = len(labels)
        col_w = width / num_cols

        lineas = ["____________________________________" for _ in labels]
        cargos = [Paragraph(f"<b>{lbl}</b>", styles['td_center']) for lbl in labels]

        t_firmas = Table([lineas, cargos], colWidths=[col_w] * num_cols)
        t_firmas.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TEXTCOLOR', (0,0), (-1,0), COLOR_MUTED),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        return t_firmas
