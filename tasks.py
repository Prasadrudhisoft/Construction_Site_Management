"""
tasks.py  —  Celery task definitions for background PDF generation.
Place this file alongside app.py (same folder).

Run worker (separate terminal):
    cd D:\\Github\\Construction_Site_Management
    venv\\Scripts\\activate
    celery -A tasks worker --loglevel=info --pool=solo
"""


import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
# ─────────────────────────────────────────────────────────────

import pymysql
from datetime import datetime
from io import BytesIO
from celery import Celery
from celery.utils.log import get_task_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=180,
    task_max_retries=3,
)


def _get_connection():
    """Always import fresh — guarantees sys.path is set before import."""
    from config import get_connection
    return get_connection()


def _notify(cur, conn, *, user_id, org_id, notification_type, reference_id, message):
    """Safe notification insert — never raises, so it cannot abort a task."""
    if not user_id:
        return
    try:
        cur.execute("""
            INSERT INTO notifications
                (user_id, org_id, notification_type, reference_id, message, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, org_id, notification_type, reference_id, message))
        conn.commit()
    except Exception as e:
        logger.warning("Notification insert failed: %s", e)



# TASK 1 — INVOICE PDF

@celery.task(bind=True, name="tasks.generate_invoice_pdf", max_retries=3)
def generate_invoice_pdf_task(self, invoice_id: int, org_id: int,
                               invoice_number: str, project_name: str,
                               grand_total: float, engineer_name: str):
    conn = None
    cur  = None
    try:
        logger.info("[invoice] Starting task invoice_id=%s org_id=%s", invoice_id, org_id)
        logger.info("[invoice] BASE_DIR=%s", BASE_DIR)

        conn = _get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT i.*, om.company_name, om.company_address, om.company_phone,
                   om.company_email, om.gst_number, om.bank_name, om.bank_account,
                   om.ifsc_code, om.terms_conditions
            FROM invoices i
            LEFT JOIN organization_master om ON i.org_id = om.org_id
            WHERE i.id = %s AND i.org_id = %s
        """, (invoice_id, org_id))
        invoice = cur.fetchone()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        cur.execute(
            "SELECT * FROM invoice_items WHERE invoice_id = %s AND org_id = %s",
            (invoice_id, org_id)
        )
        items = cur.fetchall()

        subtotal      = float(invoice["subtotal"] or 0)
        gst_amount    = float(invoice["gst_amount"] or 0)
        grand_total_v = float(invoice["total_amount"] or 0)
        gst_pct       = (gst_amount / subtotal * 100) if subtotal > 0 else 0

        raw = invoice["generated_on"]
        if raw:
            invoice_date = raw.strftime("%Y-%m-%d") if hasattr(raw, "strftime") else str(raw)[:10]
        else:
            invoice_date = ""

       
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle)
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import A4

       
        black      = colors.HexColor('#000000')
        dark       = colors.HexColor('#222222')
        mid_gray   = colors.HexColor('#666666')
        light_gray = colors.HexColor('#f5f5f5')
        border     = colors.HexColor('#bbbbbb')
        white      = colors.white

        styles = getSampleStyleSheet()

   
        def ps(name, **kw):
            return ParagraphStyle(name, parent=styles['Normal'], **kw)

        company_name_style = ps(
            'company_name',
            fontSize=16, textColor=black,
            fontName='Helvetica-Bold', alignment=0, spaceAfter=3
        )
        company_info_style = ps(
            'company_info',
            fontSize=9, textColor=mid_gray,
            fontName='Helvetica', alignment=0, spaceAfter=2
        )
        invoice_title_style = ps(
            'invoice_title',
            fontSize=28, textColor=black,
            fontName='Helvetica-Bold', alignment=2
        )
        section_label_style = ps(
            'section_label',
            fontSize=8, textColor=mid_gray,
            fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=4
        )
        body_style = ps(
            'body',
            fontSize=10, textColor=dark,
            fontName='Helvetica', spaceAfter=3
        )
        footer_style = ps(
            'footer',
            fontSize=9, textColor=mid_gray,
            fontName='Helvetica-Oblique', alignment=1, spaceBefore=8
        )

        
        buffer = BytesIO()
        PAGE_W = 495  # A4 usable width = 595 - 50 - 50

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=50, rightMargin=50,
            topMargin=40, bottomMargin=40
        )
        elements = []

       
        header_data = [[
            [
                Paragraph(invoice['company_name'] or 'Company Name', company_name_style),
                Paragraph(invoice['company_address'] or '', company_info_style),
                Paragraph(f"Phone: {invoice['company_phone'] or 'N/A'}", company_info_style),
                Paragraph(f"Email: {invoice['company_email'] or 'N/A'}", company_info_style),
                Paragraph(f"GST: {invoice['gst_number'] or 'N/A'}", company_info_style),
            ],
            Paragraph("INVOICE", invoice_title_style)
        ]]
        header_table = Table(header_data, colWidths=[PAGE_W * 0.6, PAGE_W * 0.4])
        header_table.setStyle(TableStyle([
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING',   (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        
        rule = Table([['']], colWidths=[PAGE_W])
        rule.setStyle(TableStyle([
            ('LINEBELOW',    (0, 0), (-1, -1), 0.75, black),
            ('TOPPADDING',   (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ]))
        elements.append(rule)
        elements.append(Spacer(1, 12))

       
        col = PAGE_W / 4
        meta_data = [['Invoice Number:', invoice['invoice_number'],
                      'Invoice Date:', invoice_date]]
        meta_table = Table(meta_data, colWidths=[col, col, col, col])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, -1), light_gray),
            ('BOX',          (0, 0), (-1, -1), 0.5, border),
            ('INNERGRID',    (0, 0), (-1, -1), 0.5, border),
            ('FONTNAME',     (0, 0), (0,  -1), 'Helvetica-Bold'),
            ('FONTNAME',     (2, 0), (2,  -1), 'Helvetica-Bold'),
            ('FONTNAME',     (1, 0), (1,  -1), 'Helvetica'),
            ('FONTNAME',     (3, 0), (3,  -1), 'Helvetica'),
            ('FONTSIZE',     (0, 0), (-1, -1), 10),
            ('TEXTCOLOR',    (0, 0), (-1, -1), dark),
            ('TOPPADDING',   (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
            ('LEFTPADDING',  (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        
        elements.append(Paragraph("BILL TO", section_label_style))
        bill_to_data = [[
            [
                Paragraph(f"<b>{invoice['bill_to_name'] or ''}</b>", body_style),
                Paragraph(invoice['bill_to_address'] or '', body_style),
                Paragraph(f"Phone: {invoice['bill_to_phone']}"
                          if invoice.get('bill_to_phone') else "", body_style),
            ]
        ]]
        bill_to_table = Table(bill_to_data, colWidths=[PAGE_W])
        bill_to_table.setStyle(TableStyle([
            ('BOX',          (0, 0), (-1, -1), 0.5, border),
            ('LEFTPADDING',  (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING',   (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(bill_to_table)
        elements.append(Spacer(1, 16))

        
        item_col_widths = [30, 235, 90, 50, 90]
        item_data = [['#', 'Description', 'Rate', 'Qty', 'Amount']]
        for i, it in enumerate(items, start=1):
            item_data.append([
                str(i),
                it['description'],
                f"Rs.{float(it['rate']):,.2f}",
                str(it['quantity']),
                f"Rs.{float(it['subtotal']):,.2f}"
            ])

        item_table = Table(item_data, colWidths=item_col_widths)
        item_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND',    (0, 0),  (-1, 0),  black),
            ('TEXTCOLOR',     (0, 0),  (-1, 0),  white),
            ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0),  (-1, 0),  10),
            ('ALIGN',         (0, 0),  (-1, 0),  'CENTER'),
            ('TOPPADDING',    (0, 0),  (-1, 0),  9),
            ('BOTTOMPADDING', (0, 0),  (-1, 0),  9),
            # Data rows
            ('FONTNAME',      (0, 1),  (-1, -1), 'Helvetica'),
            ('FONTSIZE',      (0, 1),  (-1, -1), 10),
            ('TEXTCOLOR',     (0, 1),  (-1, -1), dark),
            ('ALIGN',         (0, 1),  (0,  -1), 'CENTER'),
            ('ALIGN',         (2, 1),  (-1, -1), 'RIGHT'),
            ('ALIGN',         (1, 1),  (1,  -1), 'LEFT'),
            ('VALIGN',        (0, 0),  (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS',(0, 1),  (-1, -1), [white, light_gray]),
            # Borders
            ('BOX',           (0, 0),  (-1, -1), 0.75, black),
            ('INNERGRID',     (0, 0),  (-1, -1), 0.4,  border),
            # Padding
            ('TOPPADDING',    (0, 1),  (-1, -1), 7),
            ('BOTTOMPADDING', (0, 1),  (-1, -1), 7),
            ('LEFTPADDING',   (0, 0),  (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0),  (-1, -1), 8),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 14))

        
        totals_data = [['Subtotal', f'Rs.{subtotal:,.2f}']]
        if gst_amount > 0:
            sgst = gst_amount / 2
            cgst = gst_amount / 2
            totals_data.extend([
                [f'GST ({gst_pct:.2f}%)',      f'Rs.{gst_amount:,.2f}'],
                [f'SGST ({gst_pct/2:.2f}%)',   f'Rs.{sgst:,.2f}'],
                [f'CGST ({gst_pct/2:.2f}%)',   f'Rs.{cgst:,.2f}'],
            ])
        totals_data.append(['TOTAL AMOUNT', f'Rs.{grand_total_v:,.2f}'])

        totals_table = Table(totals_data, colWidths=[PAGE_W - 130, 130])
        totals_table.setStyle(TableStyle([
            ('ALIGN',         (0, 0),  (0,  -1), 'LEFT'),
            ('ALIGN',         (1, 0),  (1,  -1), 'RIGHT'),
            ('FONTNAME',      (0, 0),  (-1, -2), 'Helvetica'),
            ('FONTSIZE',      (0, 0),  (-1, -2), 10),
            ('TEXTCOLOR',     (0, 0),  (-1, -2), dark),
            # Total row
            ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, -1), (-1, -1), 11),
            ('TEXTCOLOR',     (0, -1), (-1, -1), white),
            ('BACKGROUND',    (0, -1), (-1, -1), black),
            # Borders
            ('BOX',           (0, 0),  (-1, -1), 0.75, black),
            ('LINEABOVE',     (0, -1), (-1, -1), 0.75, black),
            ('INNERGRID',     (0, 0),  (-1, -2), 0.4,  border),
            # Padding
            ('TOPPADDING',    (0, 0),  (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0),  (-1, -1), 7),
            ('LEFTPADDING',   (0, 0),  (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0),  (-1, -1), 10),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 20))

       
        elements.append(Paragraph("BANK ACCOUNT DETAILS", section_label_style))
        bank_text = (
            f"Account Holder: {invoice['company_name'] or ''}\n"
            f"Bank Name: {invoice['bank_name'] or 'N/A'}\n"
            f"Account Number: {invoice['bank_account'] or 'N/A'}\n"
            f"IFSC Code: {invoice['ifsc_code'] or 'N/A'}"
        )
        bank_table = Table([[bank_text]], colWidths=[PAGE_W])
        bank_table.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, -1), light_gray),
            ('BOX',          (0, 0), (-1, -1), 0.5, border),
            ('LEFTPADDING',  (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING',   (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
            ('FONTSIZE',     (0, 0), (-1, -1), 10),
            ('TEXTCOLOR',    (0, 0), (-1, -1), dark),
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(bank_table)
        elements.append(Spacer(1, 16))

        footer_rule = Table([['']], colWidths=[PAGE_W])
        footer_rule.setStyle(TableStyle([
            ('LINEABOVE',    (0, 0), (-1, -1), 0.5, border),
            ('TOPPADDING',   (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ]))
        elements.append(footer_rule)
        elements.append(Paragraph(
            "Thank you for your business! We appreciate your trust in our services.",
            footer_style
        ))

        # ── Build PDF ──
        doc.build(elements)
        buffer.seek(0)

        pdf_dir      = os.path.join(BASE_DIR, "static", "invoice_pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"{invoice['invoice_number']}.pdf"
        pdf_path     = os.path.join(pdf_dir, pdf_filename)

        with open(pdf_path, "wb") as fh:
            fh.write(buffer.getvalue())

        logger.info("[invoice] PDF written to %s", pdf_path)

        cur.execute("UPDATE invoices SET pdf_filename = %s WHERE id = %s",
                    (pdf_filename, invoice_id))
        conn.commit()

        if invoice.get("site_engineer_id"):
            _notify(cur, conn,
                    user_id=invoice["site_engineer_id"], org_id=org_id,
                    notification_type="invoice_ready", reference_id=invoice_id,
                    message=f'Invoice #{invoice["invoice_number"]} PDF is ready for download.')

        logger.info("[invoice] Done: %s", pdf_filename)
        return {"status": "ok", "pdf_filename": pdf_filename}

    except Exception as exc:
        logger.error("[invoice] Task failed (id=%s): %s", invoice_id, exc, exc_info=True)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise self.retry(exc=exc)
    finally:
        if cur:  cur.close()
        if conn: conn.close()

# TASK 2 — SALARY SLIP PDF

@celery.task(bind=True, name="tasks.generate_salary_slip", max_retries=3)
def generate_salary_slip_task(self, salary_id: int, org_id: int):
    conn = None
    cur  = None
    try:
        logger.info("[salary_slip] Starting task salary_id=%s org_id=%s", salary_id, org_id)

        conn = _get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT s.*,
                   p.project_name,
                   r.name       AS employee_name,
                   r.email      AS employee_email,
                   r.contact_no AS employee_contact,
                   r.role       AS employee_role,
                   om.company_name, om.company_address,
                   om.company_phone, om.company_email, om.gst_number
            FROM salaries s
            JOIN projects p  ON s.project_id = p.id
            JOIN register r  ON s.user_id    = r.id
            LEFT JOIN organization_master om ON s.org_id = om.org_id
            WHERE s.id = %s AND s.org_id = %s
        """, (salary_id, org_id))
        salary = cur.fetchone()
        if not salary:
            raise ValueError(f"Salary {salary_id} not found")

        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import A4

        # ── Professional Corporate Color Palette ─────────────────────────────
        primary     = colors.HexColor("#1B3A6B")   # deep navy
        primary_mid = colors.HexColor("#2D5FA0")   # mid-blue for earnings header
        accent      = colors.HexColor("#C8A84B")   # gold accent rule
        txt_d       = colors.HexColor("#1F2937")   # near-black body text
        txt_m       = colors.HexColor("#4B5563")   # mid-grey labels
        bg_l        = colors.HexColor("#F3F6FB")   # light blue-grey row alt
        bg_alt      = colors.HexColor("#EAF0F8")   # summary rows
        green       = colors.HexColor("#0A7C59")   # net salary
        red         = colors.HexColor("#B91C1C")   # deductions
        border_lt   = colors.HexColor("#CBD5E1")   # light grid lines
        white       = colors.white

        styles = getSampleStyleSheet()

        def ps(n, **kw):
            return ParagraphStyle(n, parent=styles["Normal"], **kw)

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=30, rightMargin=30,
                                topMargin=25, bottomMargin=25)
        elems = []

        # ── HEADER ───────────────────────────────────────────────────────────
        #   LEFT  → company name, address, phone, email, GST (each on own line)
        #   RIGHT → "Payslip For the Month" + bold month name
        # ─────────────────────────────────────────────────────────────────────
        month_name = datetime.strptime(salary["month_year"], "%Y-%m").strftime("%B %Y")

        # LEFT column — each detail a separate row for clean left-alignment
        left_tbl = Table([
            [Paragraph(salary["company_name"] or "",
                       ps("cn", fontSize=15, textColor=primary,
                          fontName="Helvetica-Bold"))],
            [Paragraph(salary["company_address"] or "",
                       ps("ca", fontSize=8.5, textColor=txt_m,
                          fontName="Helvetica", leading=13))],
            [Paragraph(f"Phone  :  {salary['company_phone'] or 'N/A'}",
                       ps("cph", fontSize=8.5, textColor=txt_m, fontName="Helvetica"))],
            [Paragraph(f"Email    :  {salary['company_email'] or 'N/A'}",
                       ps("cem", fontSize=8.5, textColor=txt_m, fontName="Helvetica"))],
            [Paragraph(f"GST     :  {salary['gst_number'] or 'N/A'}",
                       ps("cgst", fontSize=8.5, textColor=txt_m, fontName="Helvetica"))],
        ], colWidths=[310])
        left_tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        # RIGHT column — "Payslip For the Month" label + bold month, right-aligned
        right_tbl = Table([
            [Paragraph("Payslip For the Month",
                       ps("pftm", fontSize=9, textColor=txt_m,
                          fontName="Helvetica", alignment=2))],
            [Paragraph(month_name,
                       ps("mn", fontSize=17, textColor=primary,
                          fontName="Helvetica-Bold", alignment=2))],
            [Spacer(1, 8)],
            [Paragraph(f"Slip #  :  {salary_id:05d}",
                       ps("sid", fontSize=8, textColor=txt_m,
                          fontName="Helvetica", alignment=2))],
        ], colWidths=[215])
        right_tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        hdr_table = Table([[left_tbl, right_tbl]], colWidths=[315, 215])
        hdr_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elems.append(hdr_table)
        elems.append(Spacer(1, 6))

        # Gold divider rule
        elems.append(HRFlowable(width="100%", thickness=2,
                                color=accent, spaceAfter=10))

        # ── Section header helper ─────────────────────────────────────────────
        def sec_header(title):
            t = Table([[title]], colWidths=[515])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), primary),
                ("TEXTCOLOR",     (0, 0), (-1, -1), white),
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ]))
            return t

        # ── EMPLOYEE DETAILS ─────────────────────────────────────────────────
        elems.append(sec_header("EMPLOYEE DETAILS"))

        lbl = ps("lbl", fontSize=8.5, textColor=txt_m,  fontName="Helvetica-Bold")
        val = ps("val", fontSize=8.5, textColor=txt_d,   fontName="Helvetica")

        def lv(label, value):
            return [Paragraph(label, lbl), Paragraph(str(value or "N/A"), val)]

        emp_rows = [
            lv("Employee Name",  salary["employee_name"]) +
            lv("Employee ID",    salary["user_id"]),

            lv("Designation",    salary["employee_role"]) +
            lv("Project",        salary["project_name"]),

            lv("Email",          salary["employee_email"]   or "N/A") +
            lv("Contact",        salary["employee_contact"] or "N/A"),

            lv("Payment Mode",   salary["payment_mode"].upper()) +
            (lv("Cheque No.",    salary.get("cheque_number", "—"))
             if salary["payment_mode"] == "cheque"
             else ["", ""]),
        ]

        et = Table(emp_rows, colWidths=[95, 165, 95, 160])
        et.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, bg_l]),
            ("FONTSIZE",       (0, 0), (-1, -1), 8.5),
            ("GRID",           (0, 0), (-1, -1), 0.5, border_lt),
            ("BOX",            (0, 0), (-1, -1), 1,   primary),
            ("TOPPADDING",     (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
            ("LEFTPADDING",    (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        elems.append(et)
        elems.append(Spacer(1, 10))

        # ── SALARY BREAKDOWN ─────────────────────────────────────────────────
        elems.append(sec_header("SALARY BREAKDOWN"))
        elems.append(Spacer(1, 4))

        # EARNINGS — full width, stacked
        earn = Table([
            ["EARNINGS",     "AMOUNT (\u20b9)"],
            ["Basic Salary", f"{float(salary['base_salary'] or 0):,.2f}"],
            ["Allowances",   f"{float(salary['allowance']   or 0):,.2f}"],
        ], colWidths=[385, 130])
        earn.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  primary_mid),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("ALIGN",         (1, 0), (1,  -1), "RIGHT"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [white, bg_l]),
            ("GRID",          (0, 0), (-1, -1), 0.5, border_lt),
            ("BOX",           (0, 0), (-1, -1), 1,   primary_mid),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        elems.append(earn)
        elems.append(Spacer(1, 8))

        # DEDUCTIONS — full width, stacked
        ded = Table([
            ["DEDUCTIONS",        "AMOUNT (\u20b9)"],
            ["PF Deduction",      f"{float(salary['pf']              or 0):,.2f}"],
            ["Advance Deduction", f"{float(salary['advance']          or 0):,.2f}"],
            ["Other Deductions",  f"{float(salary['other_deductions'] or 0):,.2f}"],
        ], colWidths=[385, 130])
        ded.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  red),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("ALIGN",         (1, 0), (1,  -1), "RIGHT"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [white, bg_l]),
            ("GRID",          (0, 0), (-1, -1), 0.5, border_lt),
            ("BOX",           (0, 0), (-1, -1), 1,   red),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        elems.append(ded)
        elems.append(Spacer(1, 10))

        # ── NET SALARY SUMMARY ───────────────────────────────────────────────
        gross     = float(salary["base_salary"] or 0) + float(salary["allowance"] or 0)
        total_ded = (float(salary["pf"] or 0) + float(salary["advance"] or 0)
                     + float(salary["other_deductions"] or 0))
        net       = float(salary["net_salary"] or 0)

        summary = Table([
            [Paragraph("Gross Salary",
                       ps("s1",  fontSize=9,  textColor=txt_d,  fontName="Helvetica")),
             Paragraph(f"\u20b9{gross:,.2f}",
                       ps("s1v", fontSize=9,  textColor=txt_d,  fontName="Helvetica",
                          alignment=2))],
            [Paragraph("Total Deductions",
                       ps("s2",  fontSize=9,  textColor=red,    fontName="Helvetica-Bold")),
             Paragraph(f"\u20b9{total_ded:,.2f}",
                       ps("s2v", fontSize=9,  textColor=red,    fontName="Helvetica-Bold",
                          alignment=2))],
            [Paragraph("NET SALARY",
                       ps("s3",  fontSize=12, textColor=white,  fontName="Helvetica-Bold")),
             Paragraph(f"\u20b9{net:,.2f}",
                       ps("s3v", fontSize=12, textColor=white,  fontName="Helvetica-Bold",
                          alignment=2))],
        ], colWidths=[400, 115])
        summary.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0),  (-1, 1),  bg_alt),
            ("BACKGROUND",    (0, 2),  (-1, 2),  green),
            ("LINEBELOW",     (0, 0),  (-1, 1),  0.5, border_lt),
            ("BOX",           (0, 0),  (-1, -1), 1.5, primary),
            ("TOPPADDING",    (0, 0),  (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0),  (-1, -1), 7),
            ("LEFTPADDING",   (0, 0),  (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0),  (-1, -1), 8),
        ]))
        elems.append(summary)
        elems.append(Spacer(1, 14))

        # ── FOOTER ───────────────────────────────────────────────────────────
        elems.append(HRFlowable(width="100%", thickness=1,
                                color=border_lt, spaceAfter=6))
        ft = Table([[
            Paragraph("This is a system-generated salary slip and does not require a signature.",
                      ps("ft", fontSize=7.5, textColor=txt_m,
                         fontName="Helvetica", alignment=1)),
        ]], colWidths=[515])
        ft.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elems.append(ft)

        # ── Build PDF ────────────────────────────────────────────────────────
        doc.build(elems)
        buf.seek(0)

        pdf_dir      = os.path.join(BASE_DIR, "static", "salary_slips")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"salary_slip_{salary_id}.pdf"
        pdf_path     = os.path.join(pdf_dir, pdf_filename)

        with open(pdf_path, "wb") as fh:
            fh.write(buf.getvalue())

        logger.info("[salary_slip] PDF written to %s", pdf_path)

        cur.execute("UPDATE salaries SET pdf_filename = %s WHERE id = %s",
                    (pdf_filename, salary_id))
        conn.commit()

        logger.info("[salary_slip] Done: %s", pdf_filename)
        return {"status": "ok", "pdf_filename": pdf_filename}

    except Exception as exc:
        logger.error("[salary_slip] Task failed (id=%s): %s", salary_id, exc, exc_info=True)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise self.retry(exc=exc)
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# ─────────────────────────────────────────────────────────────
# TASK 3 — SALARY REPORT PDF (landscape)
# ─────────────────────────────────────────────────────────────
@celery.task(bind=True, name="tasks.generate_salary_report", max_retries=3)
def generate_salary_report_task(self, task_id: int, month_year: str,
                                 org_id: int, user_id: int):
    conn = None
    cur  = None
    try:
        logger.info("[salary_report] Starting task_id=%s month=%s", task_id, month_year)

        conn = _get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("UPDATE salary_report_tasks SET status='processing' WHERE id=%s",
                    (task_id,))
        conn.commit()

        cur.execute("""
            SELECT company_name, company_address, company_phone, company_email, gst_number
            FROM organization_master WHERE org_id=%s
        """, (org_id,))
        org = cur.fetchone()
        if not org:
            raise ValueError("Organization not found")

        cur.execute("""
            SELECT s.*, p.project_name,
                   r.name AS employee_name,
                   r.role AS employee_role
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            WHERE s.month_year=%s AND s.org_id=%s AND s.net_salary > 0
            ORDER BY p.project_name, r.name
        """, (month_year, org_id))
        salaries = cur.fetchall()
        if not salaries:
            raise ValueError("No salary records for selected month")

        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import landscape, A4

        primary   = colors.HexColor("#1e3a8a")
        accent    = colors.HexColor("#f59e0b")
        txt_dark  = colors.HexColor("#1f2937")
        txt_light = colors.HexColor("#6b7280")
        bg_light  = colors.HexColor("#f8fafc")
        styles    = getSampleStyleSheet()

        def ps(n, **kw):
            return ParagraphStyle(n, parent=styles["Normal"], **kw)

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                                leftMargin=20, rightMargin=20,
                                topMargin=20, bottomMargin=20)
        elems = []

        # ── Company Name ─────────────────────────────────────────────────────
        elems.append(Paragraph(
            org["company_name"],
            ps("cn", fontSize=20, textColor=primary,
               fontName="Helvetica-Bold", alignment=1)))

        elems.append(Spacer(1, 6))

        # ── Company Address ───────────────────────────────────────────────────
        elems.append(Paragraph(
            org["company_address"] or "",
            ps("ca", fontSize=9, textColor=txt_dark,
               fontName="Helvetica", alignment=1, leading=13)))

        # ── Phone | Email ─────────────────────────────────────────────────────
        contact_parts = []
        if org.get("company_phone"):
            contact_parts.append(org["company_phone"])
        if org.get("company_email"):
            contact_parts.append(org["company_email"])
        if contact_parts:
            elems.append(Spacer(1, 4))
            elems.append(Paragraph(
                "  |  ".join(contact_parts),
                ps("ci", fontSize=8, textColor=txt_light,
                   fontName="Helvetica", alignment=1)))

        elems.append(Spacer(1, 10))

        # ── Divider ───────────────────────────────────────────────────────────
        elems.append(HRFlowable(width="100%", thickness=1.5,
                                color=primary, spaceAfter=8))

        # ── Report Title ──────────────────────────────────────────────────────
        month_name = datetime.strptime(month_year, "%Y-%m").strftime("%B %Y")
        elems.append(Paragraph(
            f"SALARY DISBURSEMENT REPORT \u2014 {month_name.upper()}",
            ps("ti", fontSize=16, textColor=accent,
               fontName="Helvetica-Bold", alignment=1)))
        elems.append(Spacer(1, 12))

        headers    = ["S.No", "Employee", "Role", "Project",
                      "Base Salary", "Allowance", "PF",
                      "Advance", "Other Ded.", "Net Salary", "Mode"]
        table_data = [headers]
        totals     = [0.0] * 6

        for idx, s in enumerate(salaries, 1):
            vals = [float(s[k] or 0) for k in
                    ["base_salary", "allowance", "pf",
                     "advance", "other_deductions", "net_salary"]]
            for i, v in enumerate(vals):
                totals[i] += v
            table_data.append([
                str(idx),
                s["employee_name"][:20],
                s["employee_role"][:15],
                s["project_name"][:20],
                f"\u20b9{vals[0]:,.2f}", f"\u20b9{vals[1]:,.2f}",
                f"\u20b9{vals[2]:,.2f}", f"\u20b9{vals[3]:,.2f}",
                f"\u20b9{vals[4]:,.2f}", f"\u20b9{vals[5]:,.2f}",
                s["payment_mode"].upper()[:6],
            ])
        table_data.append(["", "", "", "TOTAL:",
                           *[f"\u20b9{t:,.2f}" for t in totals], ""])

        col_w = [30, 80, 60, 80, 70, 60, 50, 55, 55, 75, 55]
        stbl  = Table(table_data, colWidths=col_w)
        stbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0),  (-1,  0),  primary),
            ("TEXTCOLOR",     (0, 0),  (-1,  0),  colors.white),
            ("FONTNAME",      (0, 0),  (-1,  0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0),  (-1,  0),  9),
            ("ALIGN",         (0, 0),  (-1,  0),  "CENTER"),
            ("FONTNAME",      (0, 1),  (-1, -2),  "Helvetica"),
            ("FONTSIZE",      (0, 1),  (-1, -2),  8),
            ("ALIGN",         (4, 1),  (-2, -1),  "RIGHT"),
            ("BACKGROUND",    (0, -1), (-1, -1),  bg_light),
            ("FONTNAME",      (0, -1), (-1, -1),  "Helvetica-Bold"),
            ("GRID",          (0, 0),  (-1, -1),  0.5, colors.HexColor("#e5e7eb")),
            ("BOX",           (0, 0),  (-1, -1),  2, primary),
            ("TOPPADDING",    (0, 0),  (-1, -1),  6),
            ("BOTTOMPADDING", (0, 0),  (-1, -1),  6),
            ("LEFTPADDING",   (0, 0),  (-1, -1),  5),
            ("RIGHTPADDING",  (0, 0),  (-1, -1),  5),
            ("ROWBACKGROUNDS",(0, 1),  (-1, -2),  [colors.white, bg_light]),
        ]))
        elems.append(stbl)
        elems.append(Spacer(1, 20))
        elems.append(Paragraph(
            f"<b>Total Employees:</b> {len(salaries)}  |  "
            f"<b>Total Disbursement:</b> \u20b9{totals[5]:,.2f}",
            ps("sum", fontSize=11, textColor=primary,
               fontName="Helvetica-Bold", alignment=1)))
        elems.append(Spacer(1, 15))
        elems.append(Paragraph(
            f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
            ps("ft", fontSize=8, textColor=txt_light,
               fontName="Helvetica-Oblique", alignment=1)))

        doc.build(elems)
        buf.seek(0)

        pdf_dir      = os.path.join(BASE_DIR, "static", "salary_reports")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"salary_report_{month_year}_{task_id}.pdf"
        pdf_path     = os.path.join(pdf_dir, pdf_filename)

        with open(pdf_path, "wb") as fh:
            fh.write(buf.getvalue())

        logger.info("[salary_report] PDF written to %s", pdf_path)

        cur.execute("""
            UPDATE salary_report_tasks
            SET status='completed', pdf_filename=%s, completed_at=NOW()
            WHERE id=%s
        """, (pdf_filename, task_id))
        conn.commit()

        logger.info("[salary_report] Done: %s", pdf_filename)
        return {"status": "ok", "pdf_filename": pdf_filename}

    except Exception as exc:
        logger.error("[salary_report] Task %s failed: %s", task_id, exc, exc_info=True)
        if conn:
            try:
                conn.rollback()
                cur.execute("""
                    UPDATE salary_report_tasks
                    SET status='failed', error_message=%s WHERE id=%s
                """, (str(exc), task_id))
                conn.commit()
            except Exception:
                pass
        raise self.retry(exc=exc)
    finally:
        if cur:  cur.close()
        if conn: conn.close()



# TASK 4 — COST ESTIMATION PDF

@celery.task(bind=True, name="tasks.generate_cost_estimation_pdf", max_retries=3)
def generate_cost_estimation_pdf_task(self, project_id: int, org_id: int):
    conn = None
    cur  = None
    try:
        logger.info("[cost_est] Starting project_id=%s org_id=%s", project_id, org_id)

        conn = _get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT ce.*, p.project_name
            FROM cost_estimation ce
            JOIN projects p ON ce.project_id = p.id
            WHERE ce.project_id=%s AND ce.org_id=%s
        """, (project_id, org_id))
        cost_data = cur.fetchone()
        if not cost_data:
            raise ValueError("Cost estimation not found")

        from fpdf import FPDF
        import uuid

        upload_folder = os.path.join(BASE_DIR, "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        filename      = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
        filepath      = os.path.join(upload_folder, filename)
        relative_path = f"uploads/{filename}"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(41, 128, 185)
        pdf.rect(0, 0, 210, 40, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 24)
        pdf.ln(10)
        pdf.cell(0, 10, "COST ESTIMATION REPORT", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, "Construction Cost Analysis", ln=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(15)

        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, "Project Information", ln=True, fill=True)
        pdf.ln(5)
        for label, value in [
            ("Project ID:",    str(project_id)),
            ("Project Name:",  cost_data["project_name"]),
            ("Generated On:",  datetime.now().strftime("%B %d, %Y")),
            ("BOQ Reference:", str(cost_data["boq_reference"])),
        ]:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(50, 8, label, border=0)
            pdf.set_font("Arial", size=11)
            pdf.cell(90, 8, value, border=0, ln=True)
        pdf.ln(10)

        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, "Cost Breakdown", ln=True, fill=True)
        pdf.ln(5)
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(120, 10, "Description", border=1, fill=True)
        pdf.cell(70,  10, "Amount (Rs.)", border=1, fill=True, align="R", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=11)

        arch   = float(cost_data["architectural_design_cost"] or 0)
        struct = float(cost_data["structural_design_cost"]    or 0)
        cpsfq  = float(cost_data["cost_per_sqft"]             or 0)
        total  = arch + struct

        for row_label, row_val, fill in [
            ("Architectural Design Cost", f"{arch:,.2f}",   True),
            ("Structural Design Cost",    f"{struct:,.2f}", False),
            ("Cost per Sq.ft",            f"{cpsfq:,.2f}",  True),
        ]:
            if fill:
                pdf.set_fill_color(245, 245, 245)
            pdf.cell(120, 10, row_label, border=1, fill=fill)
            pdf.cell(70,  10, row_val,   border=1, align="R", fill=fill, ln=True)

        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(120, 12, "TOTAL ESTIMATED COST", border=1, fill=True)
        pdf.cell(70,  12, f"{total:,.2f}", border=1, fill=True, align="R", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)

        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, "Estimation Summary", ln=True, fill=True)
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, cost_data["estimation_summary"] or "", border=1)
        pdf.ln(10)

        pdf.set_y(-30)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5,
                 "This is a computer-generated document and does not require a signature.",
                 ln=True, align="C")
        pdf.output(filepath)

        logger.info("[cost_est] PDF written to %s", filepath)

        cur.execute("""
            UPDATE cost_estimation SET report_pdf_path=%s, generated_on=NOW()
            WHERE project_id=%s AND org_id=%s
        """, (relative_path, project_id, org_id))
        conn.commit()

        cur.execute("SELECT architect_id FROM projects WHERE id=%s AND org_id=%s",
                    (project_id, org_id))
        proj = cur.fetchone()
        if proj and proj.get("architect_id"):
            _notify(cur, conn,
                    user_id=proj["architect_id"], org_id=org_id,
                    notification_type="cost_estimation_ready",
                    reference_id=project_id,
                    message=f"Cost estimation PDF for project #{project_id} is ready.")

        logger.info("[cost_est] Done: %s", relative_path)
        return {"status": "ok", "relative_path": relative_path}

    except Exception as exc:
        logger.error("[cost_est] Task failed (project=%s): %s",
                     project_id, exc, exc_info=True)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise self.retry(exc=exc)
    finally:
        if cur:  cur.close()
        if conn: conn.close()



# TASK 5 — BILL PDF

@celery.task(bind=True, name="tasks.generate_bill_pdf", max_retries=3)
def generate_bill_pdf_task(self, bill_id: int, org_id: int):
    conn = None
    cur  = None
    try:
        logger.info("[bill] Starting bill_id=%s org_id=%s", bill_id, org_id)

        conn = _get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT bp.*, r.name AS created_by_name,
                   om.company_name, om.company_address
            FROM bills_and_payments bp
            JOIN register r ON bp.created_by = r.id
            LEFT JOIN organization_master om ON bp.org_id = om.org_id
            WHERE bp.id=%s AND bp.org_id=%s
        """, (bill_id, org_id))
        bill = cur.fetchone()
        if not bill:
            raise ValueError(f"Bill {bill_id} not found")

        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle)
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm

        styles = getSampleStyleSheet()
        W = 170 * mm

        C_PRIMARY  = colors.HexColor("#1e3a8a")
        C_ROW_ALT  = colors.HexColor("#eef2ff")
        C_BORDER   = colors.HexColor("#c7d2fe")
        C_LABEL_BG = colors.HexColor("#dbe4ff")
        C_TEXT     = colors.HexColor("#1e293b")
        C_GREY     = colors.HexColor("#64748b")
        C_GREEN    = colors.HexColor("#059669")
        C_RED      = colors.HexColor("#dc2626")
        C_SUBTOTAL = colors.HexColor("#1e4d8c")

        BT_COLOR = {
            "Advance Bill":         colors.HexColor("#1e3a8a"),
            "Running Account Bill": colors.HexColor("#1d4ed8"),
            "Final Bill":           colors.HexColor("#1e40af"),
        }.get(bill["bill_type"], C_PRIMARY)

        PAD = [
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 9),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 9),
        ]

        def ps(name, **kw):
            return ParagraphStyle(name, parent=styles["Normal"], **kw)

        def sec_hdr(title):
            t = Table([[title]], colWidths=[W])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), C_PRIMARY),
                ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 10),
                ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ]))
            return t

        def kv_table(data, col_w):
            t = Table(data, colWidths=col_w)
            style = [
                ("FONTNAME",   (0, 0), (0, -1),  "Helvetica-Bold"),
                ("FONTNAME",   (1, 0), (1, -1),  "Helvetica"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("TEXTCOLOR",  (0, 0), (-1, -1), C_TEXT),
                ("BACKGROUND", (0, 0), (0, -1),  C_LABEL_BG),
                ("GRID",       (0, 0), (-1, -1), 0.5, C_BORDER),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ] + PAD
            for i in range(len(data)):
                bg = colors.white if i % 2 == 0 else C_ROW_ALT
                style.append(("BACKGROUND", (1, i), (1, i), bg))
            t.setStyle(TableStyle(style))
            return t

        def fin_table(data, col_w, subtotal_row=None):
            t = Table(data, colWidths=col_w)
            style = [
                ("BACKGROUND", (0, 0),  (-1, 0),  C_PRIMARY),
                ("TEXTCOLOR",  (0, 0),  (-1, 0),  colors.white),
                ("FONTNAME",   (0, 0),  (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0),  (-1, 0),  9),
                ("FONTNAME",   (0, 1),  (-1, -1), "Helvetica"),
                ("FONTSIZE",   (0, 1),  (-1, -1), 9),
                ("ALIGN",      (1, 0),  (1,  -1), "RIGHT"),
                ("GRID",       (0, 0),  (-1, -1), 0.5, C_BORDER),
                ("VALIGN",     (0, 0),  (-1, -1), "MIDDLE"),
            ] + PAD
            for i in range(1, len(data)):
                bg = colors.white if i % 2 == 1 else C_ROW_ALT
                style.append(("BACKGROUND", (0, i), (-1, i), bg))
            if subtotal_row is not None:
                style += [
                    ("BACKGROUND", (0, subtotal_row), (-1, subtotal_row), C_SUBTOTAL),
                    ("TEXTCOLOR",  (0, subtotal_row), (-1, subtotal_row), colors.white),
                    ("FONTNAME",   (0, subtotal_row), (-1, subtotal_row), "Helvetica-Bold"),
                ]
            t.setStyle(TableStyle(style))
            return t

        elems = []

        hdr_data = [
            [Paragraph(bill.get("company_name") or "Company Name",
                       ps("cn", fontSize=22, textColor=C_PRIMARY,
                          fontName="Helvetica-Bold", alignment=1))],
            [Paragraph(bill.get("company_address") or "",
                       ps("ca", fontSize=9, textColor=C_GREY,
                          fontName="Helvetica", alignment=1))],
        ]
        hdr_tbl = Table(hdr_data, colWidths=[W])
        hdr_tbl.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW",     (0, 1), (-1,  1), 1.5, C_PRIMARY),
        ]))
        elems.append(hdr_tbl)
        elems.append(Spacer(1, 5 * mm))

        title_tbl = Table([["BILL & PAYMENT DETAILS"]], colWidths=[W])
        title_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_PRIMARY),
            ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 14),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ]))
        elems.append(title_tbl)
        elems.append(Spacer(1, 2 * mm))

        bt = Table([[bill["bill_type"]]], colWidths=[W])
        bt.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BT_COLOR),
            ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 11),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        elems.append(bt)
        elems.append(Spacer(1, 4 * mm))

        c1, c2, c3, c4 = W * 0.22, W * 0.28, W * 0.22, W * 0.28
        info = Table([
            ["Bill No",       bill["bill_no"],
             "Bill Date",     bill["bill_date"].strftime("%d-%m-%Y")],
            ["Work Order No", bill["work_order_number"],
             "Work Order Date", bill["work_order_date"].strftime("%d-%m-%Y")],
        ], colWidths=[c1, c2, c3, c4])
        info.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), C_LABEL_BG),
            ("BACKGROUND", (2, 0), (2, -1), C_LABEL_BG),
            ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ("BACKGROUND", (3, 0), (3, -1), C_ROW_ALT),
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",   (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_BORDER),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ] + PAD))
        elems.append(info)
        elems.append(Spacer(1, 2 * mm))

        work_data = [
            ["Work Name",     bill["work_name"]],
            ["Tender Name",   bill.get("tender_name")   or "N/A"],
            ["Tender Number", bill.get("tender_number") or "N/A"],
        ]
        elems.append(kv_table(work_data, [W * 0.30, W * 0.70]))
        elems.append(Spacer(1, 4 * mm))

        elems.append(sec_hdr("AMOUNT DETAILS"))
        elems.append(Spacer(1, 1 * mm))
        elems.append(fin_table([
            ["Description",            "Amount (\u20b9)"],
            ["Advance Amount",         f"\u20b9{float(bill['advance_amount']):,.2f}"],
            ["Running Account Amount", f"\u20b9{float(bill['running_account_amount']):,.2f}"],
            ["Final Amount",           f"\u20b9{float(bill['final_amount']):,.2f}"],
        ], [W * 0.70, W * 0.30]))
        elems.append(Spacer(1, 4 * mm))

        elems.append(sec_hdr("FINANCIAL BREAKDOWN"))
        elems.append(Spacer(1, 1 * mm))
        subtotal = float(bill["gross_amount"]) + float(bill["gst_amount"])
        elems.append(fin_table([
            ["Description",              "Amount (\u20b9)"],
            ["Gross Amount",              f"\u20b9{float(bill['gross_amount']):,.2f}"],
            [f"(+) GST @ {float(bill['gst_percentage'])}%",
             f"\u20b9{float(bill['gst_amount']):,.2f}"],
            ["Sub Total",                 f"\u20b9{subtotal:,.2f}"],
            ["(-) Security Deposit",      f"\u20b9{float(bill['security_deposit']):,.2f}"],
            ["(-) Labour Charges (1.1%)", f"\u20b9{float(bill['labour_charges']):,.2f}"],
        ], [W * 0.70, W * 0.30], subtotal_row=3))
        elems.append(Spacer(1, 2 * mm))

        net_tbl = Table(
            [["NET PAYABLE AMOUNT", f"\u20b9{float(bill['net_amount']):,.2f}"]],
            colWidths=[W * 0.70, W * 0.30]
        )
        net_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_GREEN),
            ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 13),
            ("ALIGN",         (1, 0), (1,  -1), "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        elems.append(net_tbl)
        elems.append(Spacer(1, 3 * mm))

        status_color = C_GREEN if bill["payment_status"] == "Paid" else C_RED
        status_text  = "PAID"  if bill["payment_status"] == "Paid" else "UNPAID"
        st = Table([[f"Payment Status :  {status_text}"]], colWidths=[W])
        st.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), status_color),
            ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 11),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        elems.append(st)
        elems.append(Spacer(1, 5 * mm))

        elems.append(Paragraph(
            f"Created by: {bill['created_by_name']} "
            f"({bill['created_by_role'].title()})   |   "
            f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
            ps("ft", fontSize=8, textColor=C_GREY, alignment=1)
        ))

        # ── Single buf + doc built once ──
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=20 * mm, rightMargin=20 * mm,
                                topMargin=15 * mm, bottomMargin=15 * mm)
        doc.build(elems)
        buf.seek(0)

        pdf_dir      = os.path.join(BASE_DIR, "static", "bill_pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"bill_{bill_id}.pdf"
        pdf_path     = os.path.join(pdf_dir, pdf_filename)

        with open(pdf_path, "wb") as fh:
            fh.write(buf.getvalue())

        logger.info("[bill] PDF written to %s", pdf_path)

        cur.execute("UPDATE bills_and_payments SET pdf_filename=%s WHERE id=%s",
                    (pdf_filename, bill_id))
        conn.commit()

        logger.info("[bill] Done: %s", pdf_filename)
        return {"status": "ok", "pdf_filename": pdf_filename}

    except Exception as exc:
        logger.error("[bill] Task failed (bill=%s): %s", bill_id, exc, exc_info=True)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise self.retry(exc=exc)
    finally:
        if cur:  cur.close()
        if conn: conn.close()