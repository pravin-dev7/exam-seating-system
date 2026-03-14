# pdf_generator.py - ReportLab PDF Generator for Seating Plans

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, Image, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


# Brand colors
PRIMARY_COLOR = HexColor('#1a3c5e')
ACCENT_COLOR = HexColor('#e8a020')
HEADER_BG = HexColor('#1a3c5e')
ALT_ROW_BG = HexColor('#f0f4f8')
WHITE = colors.white
LIGHT_GRAY = HexColor('#e2e8f0')


def _build_styles():
    """Create paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    college_style = ParagraphStyle(
        'CollegeName',
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    exam_style = ParagraphStyle(
        'ExamName',
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=ACCENT_COLOR,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    info_style = ParagraphStyle(
        'InfoLine',
        fontSize=10,
        fontName='Helvetica',
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=2,
    )

    hall_style = ParagraphStyle(
        'HallTitle',
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=WHITE,
        alignment=TA_CENTER,
    )

    footer_style = ParagraphStyle(
        'Footer',
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.gray,
        alignment=TA_CENTER,
    )

    return {
        'college': college_style,
        'exam': exam_style,
        'info': info_style,
        'hall': hall_style,
        'footer': footer_style,
    }


def _add_page_number(canvas_obj, doc):
    """Add page number footer to each page."""
    canvas_obj.saveState()
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(colors.gray)
    canvas_obj.drawRightString(
        A4[0] - 1.5*cm,
        1*cm,
        f"Page {canvas_obj.getPageNumber()}"
    )
    canvas_obj.restoreState()


def generate_hall_pdf(hall_data, exam_info, output_path):
    """
    Generate a single hall seating PDF.

    Args:
        hall_data (dict): Hall info with 'hall_number', 'benches', 'total_students'
        exam_info (dict): College/exam metadata
        output_path (str): Full path for the output PDF file
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=2*cm,
    )

    styles = _build_styles()
    story = []

    # ---- Header: Logo + College Info ----
    logo_path = exam_info.get('logo_path', '')
    logo_available = logo_path and os.path.exists(logo_path)

    if logo_available:
        try:
            logo = Image(logo_path, width=2.5*cm, height=2.5*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.3*cm))
        except Exception:
            pass  # Skip logo if it fails to load

    story.append(Paragraph(exam_info.get('college_name', 'College Name'), styles['college']))
    story.append(Paragraph(exam_info.get('exam_name', 'Examination'), styles['exam']))
    story.append(Paragraph(f"Date: {exam_info.get('exam_date', 'N/A')}", styles['info']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_COLOR, spaceAfter=6))

    # ---- Hall Banner ----
    hall_num = hall_data['hall_number']
    hall_banner_data = [[Paragraph(f"HALL - {hall_num}", styles['hall'])]]
    hall_banner = Table(hall_banner_data, colWidths=['100%'])
    hall_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(hall_banner)
    story.append(Spacer(1, 0.3*cm))

    # Stats row
    total_students = hall_data['total_students']
    total_benches = len(hall_data['benches'])
    stats_text = (f"Total Students: {total_students}  |  "
                  f"Total Benches: {total_benches}  |  "
                  f"Hall Capacity: {exam_info.get('seats_per_bench', 3) * total_benches}")
    story.append(Paragraph(stats_text, styles['info']))
    story.append(Spacer(1, 0.4*cm))

    # ---- Seating Table ----
    benches = hall_data['benches']
    seats_per_bench = exam_info.get('seats_per_bench', 3)

    # Build table header
    header = ['Bench'] + [f'Seat {i+1}' for i in range(seats_per_bench)]
    table_data = [header]

    # Build table rows
    for bench_idx, bench in enumerate(benches, start=1):
        row = [str(bench_idx)]
        for seat in bench:
            cell = f"{seat['roll_no']}\n({seat['department']})"
            row.append(cell)
        # Pad if bench is not full
        while len(row) < seats_per_bench + 1:
            row.append('—')
        table_data.append(row)

    # Calculate column widths
    available_width = A4[0] - 3*cm
    bench_col_width = 1.5*cm
    seat_col_width = (available_width - bench_col_width) / seats_per_bench

    col_widths = [bench_col_width] + [seat_col_width] * seats_per_bench

    seating_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Table styles
    table_style = TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

        # Bench column
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_GRAY),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, ACCENT_COLOR),
    ])

    # Alternating row colors
    for row_idx in range(1, len(table_data)):
        if row_idx % 2 == 0:
            table_style.add('BACKGROUND', (1, row_idx), (-1, row_idx), ALT_ROW_BG)

    seating_table.setStyle(table_style)
    story.append(seating_table)
    story.append(Spacer(1, 1*cm))

    # ---- Footer ----
    footer_text = (f"{exam_info.get('college_name', '')}  |  "
                   f"{exam_info.get('exam_name', '')}  |  Confidential - For Invigilator Use Only")
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(footer_text, styles['footer']))

    # Build PDF
    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return output_path


def generate_all_pdfs(halls, exam_info, pdf_folder):
    """
    Generate PDF files for all halls.

    Args:
        halls: List of hall dicts from seating algorithm
        exam_info: Dict with college/exam metadata
        pdf_folder: Directory to save PDFs

    Returns:
        List of generated PDF file paths
    """
    os.makedirs(pdf_folder, exist_ok=True)
    generated_files = []

    for hall in halls:
        hall_num = hall['hall_number']
        filename = f"Hall_{hall_num}_Seating_Plan.pdf"
        output_path = os.path.join(pdf_folder, filename)

        generate_hall_pdf(hall, exam_info, output_path)
        generated_files.append({
            'hall_number': hall_num,
            'filename': filename,
            'path': output_path
        })

    return generated_files
