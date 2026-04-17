from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, make_response, abort
import pymysql
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid
from flask import render_template_string
from xhtml2pdf import pisa
from flask_moment import Moment
import time
from flask import make_response
import smtplib
from email.mime.text import MIMEText
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
from flask import render_template, request, redirect, url_for, session, flash, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_from_directory
from reportlab.lib.styles import ParagraphStyle
from config import get_connection
from dotenv import load_dotenv
from decimal import Decimal
from PIL import Image as PILImage
from reportlab.platypus import Image as RLImage
import requests
from reportlab.lib.pagesizes import A4 ,landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from flask import send_file
import threading

def generate_invoice_pdf_async(invoice_id, org_id, invoice_number, project_name, grand_total, engineer_name):
    """
    Background task: generate PDF and update invoice record.
    Runs in a separate thread.
    """
    from config import get_connection
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from io import BytesIO
    import os
    from datetime import datetime  # Add this import

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch invoice data (including organization details)
        cur.execute("""
            SELECT i.*, om.company_name, om.company_address, om.company_phone, om.company_email,
                   om.gst_number, om.bank_name, om.bank_account, om.ifsc_code, om.terms_conditions
            FROM invoices i
            LEFT JOIN organization_master om ON i.org_id = om.org_id
            WHERE i.id = %s AND i.org_id = %s
        """, (invoice_id, org_id))
        invoice = cur.fetchone()
        if not invoice:
            raise Exception("Invoice not found")

        cur.execute("SELECT * FROM invoice_items WHERE invoice_id = %s AND org_id = %s", (invoice_id, org_id))
        items = cur.fetchall()

        # Prepare data for PDF
        subtotal = float(invoice['subtotal'])
        gst_amount = float(invoice['gst_amount'])
        grand_total = float(invoice['total_amount'])
        gst_percentage = (gst_amount / subtotal * 100) if subtotal > 0 else 0
        
        # ✅ FIXED: Handle both string and datetime for generated_on
        if invoice['generated_on']:
            if isinstance(invoice['generated_on'], str):
                # If it's a string, try to parse it or just use as is
                try:
                    invoice_date = datetime.strptime(invoice['generated_on'], '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    # If parsing fails, just use the string as is (assuming it's already in correct format)
                    invoice_date = invoice['generated_on'][:10] if len(invoice['generated_on']) >= 10 else invoice['generated_on']
            else:
                # It's a datetime object, use strftime
                invoice_date = invoice['generated_on'].strftime('%Y-%m-%d')
        else:
            invoice_date = ''

        # ========== PDF GENERATION (exact copy from original route) ==========
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()

        # Professional Color Scheme
        primary_color = colors.HexColor('#1e3a8a')      # Deep Blue
        secondary_color = colors.HexColor('#3b82f6')    # Bright Blue
        accent_color = colors.HexColor('#f59e0b')       # Golden Yellow
        text_dark = colors.HexColor('#1f2937')          # Dark Gray
        text_light = colors.HexColor('#6b7280')         # Light Gray
        bg_light = colors.HexColor('#f8fafc')           # Very Light Gray
        success_color = colors.HexColor('#059669')      # Green

        # Enhanced Custom Styles
        company_name_style = ParagraphStyle(
            'company_name',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            alignment=0,
            spaceAfter=5
        )
        
        company_info_style = ParagraphStyle(
            'company_info',
            parent=styles['Normal'],
            fontSize=11,
            textColor=text_light,
            fontName='Helvetica',
            alignment=0,
            spaceAfter=3
        )
        
        invoice_title_style = ParagraphStyle(
            'invoice_title',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=accent_color,
            fontName='Helvetica-Bold',
            alignment=2,
            spaceAfter=10
        )
        
        section_header_style = ParagraphStyle(
            'section_header',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            spaceBefore=15,
            spaceAfter=8,
            borderWidth=0,
            borderColor=primary_color,
            backColor=bg_light,
            leftIndent=10,
            rightIndent=10,
            topPadding=8,
            bottomPadding=8
        )
        
        client_info_style = ParagraphStyle(
            'client_info',
            parent=styles['Normal'],
            fontSize=11,
            textColor=text_dark,
            fontName='Helvetica',
            spaceAfter=4
        )
        
        footer_style = ParagraphStyle(
            'footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=text_light,
            fontName='Helvetica-Oblique',
            alignment=1,
            spaceBefore=20
        )

        elements = []

        # Professional Header with Company Branding
        header_table_data = [
            [
                [
                    Paragraph(invoice['company_name'] or 'Company Name', company_name_style),
                    Paragraph(invoice['company_address'] or '', company_info_style),
                    Paragraph(f"Phone: {invoice['company_phone'] or 'N/A'}", company_info_style),
                    Paragraph(f"Email: {invoice['company_email'] or 'N/A'}", company_info_style),
                    Paragraph(f"GST: {invoice['gst_number'] or 'N/A'}", company_info_style)
                ],
                Paragraph("INVOICE", invoice_title_style)
            ]
        ]
        
        header_table = Table(header_table_data, colWidths=[300, 250])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))

        # Invoice Details with Professional Styling
        invoice_details_data = [
            ['Invoice Number:', invoice['invoice_number'], 'Invoice Date:', invoice_date]
        ]
        
        invoice_details_table = Table(invoice_details_data, colWidths=[100, 150, 100, 150])
        invoice_details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels bold
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),       # Values normal
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Labels bold
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),       # Values normal
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, primary_color),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(invoice_details_table)
        elements.append(Spacer(1, 20))

        # The rest of your PDF generation code continues here...
        # (Keep all the remaining code from line 97 onwards exactly as it is)
        
        # Bill To Section with Enhanced Design
        elements.append(Paragraph("BILL TO", section_header_style))
        bill_to_data = [
            [
                [
                    Paragraph(f"<b>{invoice['bill_to_name']}</b>", client_info_style),
                    Paragraph(invoice['bill_to_address'] or '', client_info_style),
                    Paragraph(f"Phone: {invoice['bill_to_phone']}" if invoice['bill_to_phone'] else "", client_info_style)
                ]
            ]
        ]
        
        bill_to_table = Table(bill_to_data, colWidths=[470])
        bill_to_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(bill_to_table)
        elements.append(Spacer(1, 25))

        # Professional Line Items Table
        item_data = [['#', 'Description', 'Rate', 'Qty', 'Amount']]
        for i, it in enumerate(items, start=1):
            item_data.append([
                str(i), 
                it['description'], 
                f"₹{float(it['rate']):,.2f}", 
                str(it['quantity']), 
                f"₹{float(it['subtotal']):,.2f}"
            ])

        item_table = Table(item_data, colWidths=[30, 220, 80, 50, 90])
        item_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Serial number center
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Description left-aligned
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            
            # Grid and borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            
            # Padding
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 20))

        # Professional Totals Section
        totals_data = [['Subtotal', f'₹{subtotal:,.2f}']]

        if gst_amount > 0:
            sgst = gst_amount / 2
            cgst = gst_amount / 2
            totals_data.extend([
                [f'GST ({gst_percentage:.2f}%)', f'₹{gst_amount:,.2f}'],
                [f'SGST ({gst_percentage/2:.2f}%)', f'₹{sgst:,.2f}'],
                [f'CGST ({gst_percentage/2:.2f}%)', f'₹{cgst:,.2f}']
            ])

        totals_data.append(['TOTAL AMOUNT', f'₹{grand_total:,.2f}'])
        
        totals_table = Table(totals_data, colWidths=[350, 120])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 11),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (0, 0), (-1, -2), text_dark),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), success_color),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
            ('INNERGRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))

        # Bank Details Section
        elements.append(Paragraph("BANK ACCOUNT DETAILS", section_header_style))
        bank_details = [
            f"Account Holder: {invoice['company_name'] or ''}",
            f"Bank Name: {invoice['bank_name'] or 'N/A'}",
            f"Account Number: {invoice['bank_account'] or 'N/A'}",
            f"IFSC Code: {invoice['ifsc_code'] or 'N/A'}"
        ]
        
        bank_info_data = [['\n'.join(bank_details)]]
        bank_info_table = Table(bank_info_data, colWidths=[470])
        bank_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(bank_info_table)
        elements.append(Spacer(1, 25))

        # Terms and Conditions Section
        elements.append(Paragraph("TERMS & CONDITIONS", section_header_style))
        if invoice['terms_conditions']:
            terms_text = invoice['terms_conditions'].replace('\n', '<br/>')
        else:
            terms_text = "• Payment due within 14 days from invoice date<br/>• Late payments subject to 4% monthly interest<br/>• All disputes subject to local jurisdiction"
        
        terms_data = [[Paragraph(terms_text, client_info_style)]]
        terms_table = Table(terms_data, colWidths=[470])
        terms_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ]))
        elements.append(terms_table)
        elements.append(Spacer(1, 30))

        # Professional Footer
        elements.append(Paragraph(
            "Thank you for your business! We appreciate your trust in our services.",
            footer_style
        ))
        
        # Add a subtle line above footer
        footer_line = Table([['']], colWidths=[470])
        footer_line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, accent_color),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(footer_line)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Save PDF to static folder
        pdf_filename = f"{invoice['invoice_number']}.pdf"
        pdf_dir = os.path.join(app.static_folder, 'invoice_pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        # Update invoice record with pdf_filename
        cur.execute("UPDATE invoices SET pdf_filename = %s WHERE id = %s", (pdf_filename, invoice_id))
        conn.commit()

        # Notify user that PDF is ready
        create_notification(
            user_id=invoice['site_engineer_id'],
            org_id=org_id,
            notification_type='invoice_ready',
            reference_id=invoice_id,
            message=f'Your invoice #{invoice["invoice_number"]} PDF is ready for download.'
        )

    except Exception as e:
        print(f"Background PDF generation failed for invoice {invoice_id}: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        cur.close()
        conn.close()

def generate_cost_estimation_pdf_async(project_id, org_id):
    """
    Background task: generate cost estimation PDF and update cost_estimation table.
    Runs in a separate thread.
    """
    from config import get_connection
    from fpdf import FPDF
    from datetime import datetime
    import os
    import uuid

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch cost estimation data
        cur.execute("""
            SELECT ce.*, p.project_name
            FROM cost_estimation ce
            JOIN projects p ON ce.project_id = p.id
            WHERE ce.project_id = %s AND ce.org_id = %s
        """, (project_id, org_id))
        cost_data = cur.fetchone()
        if not cost_data:
            raise Exception("Cost estimation not found")

        # Generate PDF using FPDF (same as original route)
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(upload_folder, filename)
        relative_path = f"uploads/{filename}"

        pdf = FPDF()
        pdf.add_page()

        # Header
        pdf.set_fill_color(41, 128, 185)
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 24)
        pdf.ln(10)
        pdf.cell(0, 10, txt="COST ESTIMATION REPORT", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, txt="A to Z Construction Cost Analysis", ln=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(15)

        # Project Information
        pdf.set_font("Arial", 'B', 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, txt="Project Information", ln=True, fill=True)
        pdf.ln(5)
        pdf.set_font("Arial", size=11)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, txt="Project ID:", border=0)
        pdf.set_font("Arial", size=11)
        pdf.cell(90, 8, txt=str(project_id), border=0, ln=True)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, txt="Project Name:", border=0)
        pdf.set_font("Arial", size=11)
        pdf.cell(90, 8, txt=cost_data['project_name'], border=0, ln=True)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, txt="Generated On:", border=0)
        pdf.set_font("Arial", size=11)
        pdf.cell(90, 8, txt=datetime.now().strftime("%B %d, %Y"), border=0, ln=True)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, txt="BOQ Reference:", border=0)
        pdf.set_font("Arial", size=11)
        pdf.cell(90, 8, txt=str(cost_data['boq_reference']), border=0, ln=True)
        pdf.ln(10)

        # Cost Breakdown
        pdf.set_font("Arial", 'B', 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, txt="Cost Breakdown", ln=True, fill=True)
        pdf.ln(5)
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(120, 10, txt="Description", border=1, fill=True)
        pdf.cell(70, 10, txt="Amount (Rs.)", border=1, fill=True, align='R', ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=11)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(120, 10, txt="Architectural Design Cost", border=1, fill=True)
        pdf.cell(70, 10, txt=f"{float(cost_data['architectural_design_cost'] or 0):,.2f}", border=1, fill=True, align='R', ln=True)
        pdf.cell(120, 10, txt="Structural Design Cost", border=1)
        pdf.cell(70, 10, txt=f"{float(cost_data['structural_design_cost'] or 0):,.2f}", border=1, align='R', ln=True)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(120, 10, txt="Cost per Sq.ft", border=1, fill=True)
        pdf.cell(70, 10, txt=f"{float(cost_data['cost_per_sqft'] or 0):,.2f}", border=1, fill=True, align='R', ln=True)
        total_cost = float(cost_data['architectural_design_cost'] or 0) + float(cost_data['structural_design_cost'] or 0)
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(120, 12, txt="TOTAL ESTIMATED COST", border=1, fill=True)
        pdf.cell(70, 12, txt=f"{total_cost:,.2f}", border=1, fill=True, align='R', ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)

        # Estimation Summary
        pdf.set_font("Arial", 'B', 14)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(0, 10, txt="Estimation Summary", ln=True, fill=True)
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, txt=cost_data['estimation_summary'] or '', border=1, fill=False)
        pdf.ln(10)

        # Footer
        pdf.set_y(-30)
        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, txt="This is a computer-generated document and does not require a signature.", ln=True, align="C")
        pdf.output(filepath)

        # Update cost_estimation table with PDF path
        cur.execute("""
            UPDATE cost_estimation 
            SET report_pdf_path = %s, generated_on = NOW()
            WHERE project_id = %s AND org_id = %s
        """, (relative_path, project_id, org_id))
        conn.commit()

        # Notify the architect (or user) that PDF is ready
        # Get architect ID from project
        cur.execute("SELECT architect_id FROM projects WHERE id = %s AND org_id = %s", (project_id, org_id))
        proj = cur.fetchone()
        if proj and proj['architect_id']:
            create_notification(
                user_id=proj['architect_id'],
                org_id=org_id,
                notification_type='cost_estimation_ready',
                reference_id=project_id,
                message=f'Cost estimation PDF for project #{project_id} is ready for download.'
            )

    except Exception as e:
        print(f"Background cost estimation PDF failed for project {project_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        cur.close()
        conn.close()


def generate_salary_slip_async(salary_id, org_id):
    """
    Background task: generate salary slip PDF and update salaries table.
    Runs in a separate thread.
    """
    from config import get_connection
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from io import BytesIO
    import os
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch salary details (same as original download_salary_slip)
        cur.execute("""
            SELECT s.*, 
                   p.project_name, 
                   r.name AS employee_name,
                   r.email AS employee_email,
                   r.contact_no AS employee_contact,
                   r.role AS employee_role,
                   om.company_name, om.company_address, om.company_phone, om.company_email, om.gst_number
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            LEFT JOIN organization_master om ON s.org_id = om.org_id
            WHERE s.id = %s AND s.org_id = %s
        """, (salary_id, org_id))
        salary = cur.fetchone()
        if not salary:
            raise Exception("Salary record not found")

        # Generate PDF with optimized margins for single page
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()

        # Professional Color Scheme
        primary_color = colors.HexColor('#1e3a8a')
        accent_color = colors.HexColor('#f59e0b')
        text_dark = colors.HexColor('#1f2937')
        text_light = colors.HexColor('#6b7280')
        bg_light = colors.HexColor('#f8fafc')

        # Compact styles (same as your original)
        company_name_style = ParagraphStyle(
            'company_name',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=3
        )
        
        title_style = ParagraphStyle(
            'title',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=accent_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=10
        )
        
        section_header_style = ParagraphStyle(
            'section_header',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            spaceBefore=8,
            spaceAfter=5,
            backColor=bg_light,
            leftIndent=8,
            rightIndent=8,
            topPadding=5,
            bottomPadding=5
        )
        
        normal_style = ParagraphStyle(
            'normal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=text_dark,
            fontName='Helvetica',
            spaceAfter=2
        )

        elements = []

        # Header
        elements.append(Paragraph(salary['company_name'] or 'Company Name', company_name_style))
        elements.append(Paragraph(salary['company_address'] or '', normal_style))
        elements.append(Paragraph(f"Phone: {salary['company_phone'] or ''}", normal_style))
        elements.append(Paragraph(f"Email: {salary['company_email'] or ''}", normal_style))
        if salary.get('gst_number'):
            elements.append(Paragraph(f"GST: {salary['gst_number']}", normal_style))
        elements.append(Spacer(1, 10))

        # Title
        elements.append(Paragraph("SALARY SLIP", title_style))
        elements.append(Spacer(1, 5))

        # Salary Period
        month_year = salary['month_year']
        month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')
        period_data = [[f'For the month of: {month_name}']]
        period_table = Table(period_data, colWidths=[515])
        period_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ]))
        elements.append(period_table)
        elements.append(Spacer(1, 10))

        # Employee Details
        elements.append(Paragraph("EMPLOYEE DETAILS", section_header_style))
        emp_data = [
            ['Employee Name:', salary['employee_name'], 'Employee ID:', str(salary['user_id'])],
            ['Role:', salary['employee_role'], 'Project:', salary['project_name']],
            ['Email:', salary['employee_email'] or 'N/A', 'Contact:', salary['employee_contact'] or 'N/A'],
            ['Payment Mode:', salary['payment_mode'].upper(), '', '']
        ]
        if salary['payment_mode'] == 'cheque' and salary['cheque_number']:
            emp_data.append(['Cheque Number:', salary['cheque_number'], '', ''])
        
        emp_table = Table(emp_data, colWidths=[120, 150, 100, 145])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(emp_table)
        elements.append(Spacer(1, 10))

        # Salary Breakdown
        elements.append(Paragraph("SALARY BREAKDOWN", section_header_style))
        earnings_data = [
            ['EARNINGS', 'AMOUNT (₹)'],
            ['Basic Salary', f"{float(salary['base_salary'] or 0):,.2f}"],
            ['Allowances', f"{float(salary['allowance'] or 0):,.2f}"],
        ]
        earnings_table = Table(earnings_data, colWidths=[385, 130])
        earnings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(earnings_table)
        elements.append(Spacer(1, 8))

        deductions_data = [
            ['DEDUCTIONS', 'AMOUNT (₹)'],
            ['PF Deduction', f"{float(salary['pf'] or 0):,.2f}"],
            ['Advance Deduction', f"{float(salary['advance'] or 0):,.2f}"],
            ['Other Deductions', f"{float(salary['other_deductions'] or 0):,.2f}"],
        ]
        deductions_table = Table(deductions_data, colWidths=[385, 130])
        deductions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#dc3545')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(deductions_table)
        elements.append(Spacer(1, 10))

        # Net Salary Summary
        gross_salary = float(salary['base_salary'] or 0) + float(salary['allowance'] or 0)
        total_deductions = float(salary['pf'] or 0) + float(salary['advance'] or 0) + float(salary['other_deductions'] or 0)
        net_salary = float(salary['net_salary'] or 0)
        summary_data = [
            ['Gross Salary', f'₹{gross_salary:,.2f}'],
            ['Total Deductions', f'₹{total_deductions:,.2f}'],
            ['NET SALARY', f'₹{net_salary:,.2f}']
        ]
        summary_table = Table(summary_data, colWidths=[385, 130])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -2), bg_light),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, -2), text_dark),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Save PDF to static/salary_slips/
        pdf_dir = os.path.join(app.static_folder, 'salary_slips')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"salary_slip_{salary_id}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        # Update salaries table with pdf_filename
        cur.execute("UPDATE salaries SET pdf_filename = %s WHERE id = %s", (pdf_filename, salary_id))
        conn.commit()

    except Exception as e:
        print(f"Background salary slip generation failed for salary {salary_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        cur.close()
        conn.close()


def generate_salary_report_async(task_id, month_year, org_id, user_id):
    """
    Background task: generate salary disbursement report PDF.
    """
    from config import get_connection
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import landscape, A4
    from io import BytesIO
    import os
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Update task status to processing
        cur.execute("UPDATE salary_report_tasks SET status = 'processing' WHERE id = %s", (task_id,))
        conn.commit()

        # Get organization details
        cur.execute("""
            SELECT company_name, company_address, company_phone, company_email, gst_number
            FROM organization_master 
            WHERE org_id = %s
        """, (org_id,))
        org = cur.fetchone()
        if not org:
            raise Exception("Organization not found")

        # Get all salaries for the month
        cur.execute("""
            SELECT s.*, 
                   p.project_name, 
                   r.name AS employee_name,
                   r.role AS employee_role
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            WHERE s.month_year = %s AND s.org_id = %s AND s.base_salary > 0
            ORDER BY p.project_name, r.name
        """, (month_year, org_id))
        salaries = cur.fetchall()

        if not salaries:
            raise Exception("No salary records found for the selected month")

        # Generate PDF (same code as original download_salary_report)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()

        primary_color = colors.HexColor('#1e3a8a')
        accent_color = colors.HexColor('#f59e0b')
        text_dark = colors.HexColor('#1f2937')
        text_light = colors.HexColor('#6b7280')
        bg_light = colors.HexColor('#f8fafc')

        company_name_style = ParagraphStyle(
            'company_name', parent=styles['Heading1'], fontSize=22,
            textColor=primary_color, fontName='Helvetica-Bold', alignment=1, spaceAfter=5
        )
        title_style = ParagraphStyle(
            'title', parent=styles['Heading2'], fontSize=18,
            textColor=accent_color, fontName='Helvetica-Bold', alignment=1, spaceAfter=15
        )
        normal_style = ParagraphStyle(
            'normal', parent=styles['Normal'], fontSize=9,
            textColor=text_dark, fontName='Helvetica', spaceAfter=3
        )

        elements = []

        # Header
        elements.append(Paragraph(org['company_name'], company_name_style))
        elements.append(Paragraph(org['company_address'], normal_style))
        elements.append(Paragraph(f"Phone: {org['company_phone']} | Email: {org['company_email']}", normal_style))
        if org.get('gst_number'):
            elements.append(Paragraph(f"GST: {org['gst_number']}", normal_style))
        elements.append(Spacer(1, 15))

        # Title
        month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')
        elements.append(Paragraph(f"SALARY DISBURSEMENT REPORT - {month_name.upper()}", title_style))
        elements.append(Spacer(1, 10))

        # Salary Table
        table_data = [
            ['S.No', 'Employee Name', 'Role', 'Project', 'Base Salary', 
             'Allowance', 'PF', 'Advance', 'Other Ded.', 'Net Salary', 'Payment Mode']
        ]

        total_base = 0
        total_allowance = 0
        total_pf = 0
        total_advance = 0
        total_other_ded = 0
        total_net = 0

        for idx, s in enumerate(salaries, 1):
            base_salary = float(s['base_salary'] or 0)
            allowance = float(s['allowance'] or 0)
            pf = float(s['pf'] or 0)
            advance = float(s['advance'] or 0)
            other_ded = float(s['other_deductions'] or 0)
            net_salary = float(s['net_salary'] or 0)

            total_base += base_salary
            total_allowance += allowance
            total_pf += pf
            total_advance += advance
            total_other_ded += other_ded
            total_net += net_salary

            table_data.append([
                str(idx),
                s['employee_name'][:20],
                s['employee_role'][:15],
                s['project_name'][:20],
                f"₹{base_salary:,.2f}",
                f"₹{allowance:,.2f}",
                f"₹{pf:,.2f}",
                f"₹{advance:,.2f}",
                f"₹{other_ded:,.2f}",
                f"₹{net_salary:,.2f}",
                s['payment_mode'].upper()[:6]
            ])

        # Totals row
        table_data.append([
            '', '', '', 'TOTAL:',
            f"₹{total_base:,.2f}", f"₹{total_allowance:,.2f}", f"₹{total_pf:,.2f}",
            f"₹{total_advance:,.2f}", f"₹{total_other_ded:,.2f}", f"₹{total_net:,.2f}", ''
        ])

        col_widths = [30, 80, 60, 80, 70, 60, 50, 55, 55, 75, 55]
        salary_table = Table(table_data, colWidths=col_widths)

        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,1), (-1,-2), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-2), 8),
            ('ALIGN', (0,1), (0,-1), 'CENTER'),
            ('ALIGN', (4,1), (-2,-1), 'RIGHT'),
            ('ALIGN', (-1,1), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,-1), (-1,-1), bg_light),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 9),
            ('TEXTCOLOR', (0,-1), (-1,-1), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOX', (0,0), (-1,-1), 2, primary_color),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, bg_light]),
        ])
        salary_table.setStyle(table_style)
        elements.append(salary_table)
        elements.append(Spacer(1, 20))

        # Summary
        summary_text = f"<b>Total Employees:</b> {len(salaries)} | <b>Total Disbursement:</b> ₹{total_net:,.2f}"
        summary_para = Paragraph(summary_text, ParagraphStyle(
            'summary', parent=styles['Normal'], fontSize=11,
            textColor=primary_color, fontName='Helvetica-Bold', alignment=1
        ))
        elements.append(summary_para)
        elements.append(Spacer(1, 15))

        # Footer
        footer_text = f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}"
        footer_para = Paragraph(footer_text, ParagraphStyle(
            'footer', parent=styles['Normal'], fontSize=8,
            textColor=text_light, fontName='Helvetica-Oblique', alignment=1
        ))
        elements.append(footer_para)

        doc.build(elements)
        buffer.seek(0)

        # Save PDF to static/salary_reports/
        pdf_dir = os.path.join(app.static_folder, 'salary_reports')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"salary_report_{month_year}_{task_id}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        # Update task status
        cur.execute("""
            UPDATE salary_report_tasks 
            SET status = 'completed', pdf_filename = %s, completed_at = NOW() 
            WHERE id = %s
        """, (pdf_filename, task_id))
        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.execute("""
            UPDATE salary_report_tasks 
            SET status = 'failed', error_message = %s 
            WHERE id = %s
        """, (str(e), task_id))
        conn.commit()
        print(f"Salary report generation failed for task {task_id}: {e}")
    finally:
        cur.close()
        conn.close()


def generate_bill_pdf_async(bill_id, org_id):
    """
    Background task: generate bill PDF and update bills_and_payments table.
    """
    from config import get_connection
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from io import BytesIO
    import os
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Fetch bill details with company info
        cur.execute("""
            SELECT bp.*, r.name AS created_by_name,
                   om.company_name, om.company_address
            FROM bills_and_payments bp
            JOIN register r ON bp.created_by = r.id
            LEFT JOIN organization_master om ON bp.org_id = om.org_id
            WHERE bp.id = %s AND bp.org_id = %s
        """, (bill_id, org_id))
        bill = cur.fetchone()
        if not bill:
            raise Exception("Bill not found")

        # Generate PDF (use the same code as your original download_bill_pdf)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )
        styles = getSampleStyleSheet()
        W = 170 * mm

        # Color palette (same as original)
        C_PRIMARY    = colors.HexColor('#1e3a8a')
        C_ROW_ALT    = colors.HexColor('#eef2ff')
        C_ROW_WHITE  = colors.white
        C_BORDER     = colors.HexColor('#c7d2fe')
        C_LABEL_BG   = colors.HexColor('#dbe4ff')
        C_TEXT       = colors.HexColor('#1e293b')
        C_GREY       = colors.HexColor('#64748b')
        C_GREEN      = colors.HexColor('#059669')
        C_RED        = colors.HexColor('#dc2626')
        C_SUBTOTAL   = colors.HexColor('#1e4d8c')

        BT_COLOR = {
            'Advance Bill':        colors.HexColor('#1e3a8a'),
            'Running Account Bill':colors.HexColor('#1d4ed8'),
            'Final Bill':          colors.HexColor('#1e40af'),
        }.get(bill['bill_type'], C_PRIMARY)

        PAD = [
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LEFTPADDING',   (0,0),(-1,-1), 9),
            ('RIGHTPADDING',  (0,0),(-1,-1), 9),
        ]

        def sec_hdr(title):
            t = Table([[title]], colWidths=[W])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,-1), C_PRIMARY),
                ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
                ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,-1), 10),
                ('ALIGN',         (0,0),(-1,-1), 'LEFT'),
                ('TOPPADDING',    (0,0),(-1,-1), 7),
                ('BOTTOMPADDING', (0,0),(-1,-1), 7),
                ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ]))
            return t

        def kv_table(data, col_w):
            t = Table(data, colWidths=col_w)
            style = [
                ('FONTNAME',      (0,0),(0,-1),  'Helvetica-Bold'),
                ('FONTNAME',      (1,0),(1,-1),  'Helvetica'),
                ('FONTSIZE',      (0,0),(-1,-1), 9),
                ('TEXTCOLOR',     (0,0),(-1,-1), C_TEXT),
                ('BACKGROUND',    (0,0),(0,-1),  C_LABEL_BG),
                ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ] + PAD
            for i in range(len(data)):
                bg = C_ROW_WHITE if i % 2 == 0 else C_ROW_ALT
                style.append(('BACKGROUND', (1,i),(1,i), bg))
            t.setStyle(TableStyle(style))
            return t

        def fin_table(data, col_w, subtotal_row=None):
            t = Table(data, colWidths=col_w)
            style = [
                ('BACKGROUND',    (0,0),(-1,0),  C_PRIMARY),
                ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
                ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,0),  9),
                ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
                ('FONTSIZE',      (0,1),(-1,-1), 9),
                ('TEXTCOLOR',     (0,1),(-1,-1), C_TEXT),
                ('ALIGN',         (1,0),(1,-1),  'RIGHT'),
                ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ] + PAD
            for i in range(1, len(data)):
                bg = C_ROW_WHITE if i % 2 == 1 else C_ROW_ALT
                style.append(('BACKGROUND', (0,i),(-1,i), bg))
            if subtotal_row is not None:
                style += [
                    ('BACKGROUND', (0,subtotal_row),(-1,subtotal_row), C_SUBTOTAL),
                    ('TEXTCOLOR',  (0,subtotal_row),(-1,subtotal_row), colors.white),
                    ('FONTNAME',   (0,subtotal_row),(-1,subtotal_row), 'Helvetica-Bold'),
                ]
            t.setStyle(TableStyle(style))
            return t

        elems = []

        # Header
        company_name    = bill.get('company_name') or 'Company Name'
        company_address = bill.get('company_address') or ''
        s_name = ParagraphStyle('cn', parent=styles['Normal'],
                                 fontSize=22, textColor=C_PRIMARY,
                                 fontName='Helvetica-Bold', alignment=1,
                                 spaceBefore=0, spaceAfter=3)
        s_addr = ParagraphStyle('ca', parent=styles['Normal'],
                                 fontSize=9,  textColor=C_GREY,
                                 fontName='Helvetica', alignment=1,
                                 spaceBefore=0, spaceAfter=0)
        hdr_data = [[Paragraph(company_name, s_name)],
                    [Paragraph(company_address, s_addr)]]
        hdr_tbl  = Table(hdr_data, colWidths=[W])
        hdr_tbl.setStyle(TableStyle([
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LINEBELOW',     (0,1),(-1,1),  1.5, C_PRIMARY),
        ]))
        elems.append(hdr_tbl)
        elems.append(Spacer(1, 5*mm))

        # Title
        title_tbl = Table([['BILL & PAYMENT DETAILS']], colWidths=[W])
        title_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), C_PRIMARY),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 14),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 11),
            ('BOTTOMPADDING', (0,0),(-1,-1), 11),
        ]))
        elems.append(title_tbl)
        elems.append(Spacer(1, 2*mm))

        # Bill Type Banner
        bt_tbl = Table([[bill['bill_type']]], colWidths=[W])
        bt_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), BT_COLOR),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 11),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ]))
        elems.append(bt_tbl)
        elems.append(Spacer(1, 4*mm))

        # Bill & Work Order Info
        c1, c2, c3, c4 = W*0.22, W*0.28, W*0.22, W*0.28
        info_data = [
            ['Bill No',       bill['bill_no'],
             'Bill Date',     bill['bill_date'].strftime('%d-%m-%Y')],
            ['Work Order No', bill['work_order_number'],
             'Work Order Date', bill['work_order_date'].strftime('%d-%m-%Y')],
        ]
        info_tbl = Table(info_data, colWidths=[c1, c2, c3, c4])
        info_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(0,-1),  C_LABEL_BG),
            ('BACKGROUND',    (2,0),(2,-1),  C_LABEL_BG),
            ('BACKGROUND',    (1,0),(1,-1),  C_ROW_WHITE),
            ('BACKGROUND',    (3,0),(3,-1),  C_ROW_ALT),
            ('FONTNAME',      (0,0),(0,-1),  'Helvetica-Bold'),
            ('FONTNAME',      (2,0),(2,-1),  'Helvetica-Bold'),
            ('FONTNAME',      (1,0),(1,-1),  'Helvetica'),
            ('FONTNAME',      (3,0),(3,-1),  'Helvetica'),
            ('FONTSIZE',      (0,0),(-1,-1), 9),
            ('TEXTCOLOR',     (0,0),(-1,-1), C_TEXT),
            ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ] + PAD))
        elems.append(info_tbl)
        elems.append(Spacer(1, 2*mm))

        # Work Details
        work_data = [
            ['Work Name',     bill['work_name']],
            ['Tender Name',   bill.get('tender_name') or 'N/A'],
            ['Tender Number', bill.get('tender_number') or 'N/A'],
        ]
        elems.append(kv_table(work_data, [W*0.30, W*0.70]))
        elems.append(Spacer(1, 4*mm))

        # Amount Details
        elems.append(sec_hdr('AMOUNT DETAILS'))
        elems.append(Spacer(1, 1*mm))
        amt_data = [
            ['Description',           'Amount (₹)'],
            ['Advance Amount',         f"₹{float(bill['advance_amount']):,.2f}"],
            ['Running Account Amount', f"₹{float(bill['running_account_amount']):,.2f}"],
            ['Final Amount',           f"₹{float(bill['final_amount']):,.2f}"],
        ]
        elems.append(fin_table(amt_data, [W*0.70, W*0.30]))
        elems.append(Spacer(1, 4*mm))

        # Financial Breakdown
        elems.append(sec_hdr('FINANCIAL BREAKDOWN'))
        elems.append(Spacer(1, 1*mm))
        subtotal = float(bill['gross_amount']) + float(bill['gst_amount'])
        fin_data = [
            ['Description',                    'Amount (₹)'],
            ['Gross Amount',                    f"₹{float(bill['gross_amount']):,.2f}"],
            [f"(+) GST @ {float(bill['gst_percentage'])}%", f"₹{float(bill['gst_amount']):,.2f}"],
            ['Sub Total',                       f"₹{subtotal:,.2f}"],
            ['(−) Security Deposit',            f"₹{float(bill['security_deposit']):,.2f}"],
            ['(−) Labour Charges (1.1%)',        f"₹{float(bill['labour_charges']):,.2f}"],
        ]
        elems.append(fin_table(fin_data, [W*0.70, W*0.30], subtotal_row=3))
        elems.append(Spacer(1, 2*mm))

        # Net Payable
        net_tbl = Table([['NET PAYABLE AMOUNT', f"₹{float(bill['net_amount']):,.2f}"]],
                         colWidths=[W*0.70, W*0.30])
        net_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), C_GREEN),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 13),
            ('ALIGN',         (1,0),(1,-1),  'RIGHT'),
            ('TOPPADDING',    (0,0),(-1,-1), 11),
            ('BOTTOMPADDING', (0,0),(-1,-1), 11),
            ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ('RIGHTPADDING',  (0,0),(-1,-1), 10),
        ]))
        elems.append(net_tbl)
        elems.append(Spacer(1, 3*mm))

        # Payment Status Banner
        status_color = C_GREEN if bill['payment_status'] == 'Paid' else C_RED
        status_text  = 'PAID' if bill['payment_status'] == 'Paid' else 'UNPAID'
        st_tbl = Table([[f"Payment Status :  {status_text}"]], colWidths=[W])
        st_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), status_color),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 11),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 9),
            ('BOTTOMPADDING', (0,0),(-1,-1), 9),
        ]))
        elems.append(st_tbl)
        elems.append(Spacer(1, 5*mm))

        # Footer
        footer_txt = (f"Created by: {bill['created_by_name']} ({bill['created_by_role'].title()})   |   "
                      f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
        elems.append(Paragraph(footer_txt,
            ParagraphStyle('ft', parent=styles['Normal'],
                           fontSize=8, textColor=C_GREY, alignment=1)))

        doc.build(elems)
        buffer.seek(0)

        # Save PDF to static/bill_pdfs/
        pdf_dir = os.path.join(app.static_folder, 'bill_pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"bill_{bill_id}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        # Update bill record
        cur.execute("UPDATE bills_and_payments SET pdf_filename = %s WHERE id = %s", (pdf_filename, bill_id))
        conn.commit()

    except Exception as e:
        print(f"Background bill PDF generation failed for bill {bill_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        cur.close()
        conn.close()

load_dotenv()

UPLOAD_FOLDER_INVOICES = 'static/invoices'
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

moment = Moment(app)

ZEPTOMAIL_API_URL = "https://api.zeptomail.in/v1.1/email"
ZEPTOMAIL_API_TOKEN = os.environ.get("ZEPTO_TOKEN")
ZEPTOMAIL_FROM_EMAIL = "contact@rudhisoft.com"
ZEPTOMAIL_FROM_NAME = "Rudhiarch"

from werkzeug.security import generate_password_hash, check_password_hash

UPLOAD_FOLDER = 'static/uploads'
UPLOAD_FOLDER_INVOICES = 'static/invoices'
UPLOAD_FOLDER_VENDOR = 'static/vendor_quotes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VENDOR, exist_ok=True)
UPLOAD_FOLDER_PROGRESS = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_otp():
    """Generate a random 6-digit OTP"""
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp):
    """
    Send OTP email using ZeptoMail
    Returns: (success: bool, error_message: str or None)
    """
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Zoho-enczapikey {ZEPTOMAIL_API_TOKEN}"
        }
        
        payload = {
            "from": {
                "address": ZEPTOMAIL_FROM_EMAIL,
                "name": ZEPTOMAIL_FROM_NAME
            },
            "to": [
                {
                    "email_address": {
                        "address": email
                    }
                }
            ],
            "subject": "Your OTP Code for Verification",
            "htmlbody": f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                            <h2 style="color: #1e3a8a; text-align: center;">OTP Verification</h2>
                            <p>Hello,</p>
                            <p>Your One-Time Password (OTP) for verification is:</p>
                            <div style="text-align: center; margin: 30px 0;">
                                <span style="font-size: 32px; font-weight: bold; color: #1e3a8a; letter-spacing: 5px; padding: 15px 30px; border: 2px dashed #1e3a8a; border-radius: 8px; display: inline-block;">
                                    {otp}
                                </span>
                            </div>
                            <p style="color: #e74c3c; font-weight: bold;">⚠️ This code will expire in 5 minutes.</p>
                            <p>If you didn't request this code, please ignore this email.</p>
                            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                            <p style="font-size: 12px; color: #666;">
                                Best regards,<br>
                                <strong>Rudhiarch Team</strong>
                            </p>
                        </div>
                    </body>
                </html>
            """
        }
        
        response = requests.post(ZEPTOMAIL_API_URL, headers=headers, json=payload, timeout=10)
        
        # Log response for debugging
        print(f"ZeptoMail Status Code: {response.status_code}")
        print(f"ZeptoMail Response: {response.text}")
        
        response.raise_for_status()
        return True, None
        
    except requests.exceptions.Timeout:
        return False, "Email service timeout. Please try again."
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to send email: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" - {e.response.text}"
        return False, error_msg
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
    



    ################################### NOTIFICATION HELPER FUNCTIONS ###################################

"""
FIXED NOTIFICATION HELPER FUNCTIONS
Replace lines 206-285 in your app.py with these functions
"""

def create_notification(user_id, org_id, notification_type, 
                        reference_id, message, cur=None):
    """
    If `cur` is passed, reuses the caller's transaction (no commit here).
    If `cur` is None, opens its own connection and commits itself.
    """
    _own_conn = cur is None
    _conn = None
    _cur = cur

    try:
        if _own_conn:
            _conn = get_connection()
            _cur = _conn.cursor()

        _cur.execute("""
            INSERT INTO notifications 
                (user_id, org_id, notification_type, reference_id, message, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, org_id, notification_type, reference_id, message))

        if _own_conn:
            _conn.commit()

    except Exception as e:
        print(f"Error creating notification: {e}")
        if _own_conn and _conn:
            _conn.rollback()
    finally:
        if _own_conn:
            if _cur: _cur.close()
            if _conn: _conn.close()


def get_unread_notifications_count(user_id, org_id, notification_type=None):
    """Get count of unread notifications for a user"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if notification_type:
            query = """
                SELECT COUNT(*) 
                FROM notifications 
                WHERE user_id = %s AND org_id = %s 
                AND notification_type = %s AND is_read = 0
            """
            params = (user_id, org_id, notification_type)
        else:
            query = """
                SELECT COUNT(*) 
                FROM notifications 
                WHERE user_id = %s AND org_id = %s AND is_read = 0
            """
            params = (user_id, org_id)
        
        # print(f"🔍 QUERY: user_id={user_id}, org_id={org_id}, type={notification_type}")
        
        cur.execute(query, params)
        result = cur.fetchone()
        count = result[0] if result else 0  # ✅ Now this will work
        
        # print(f"📊 RESULT: Found {count} notifications")
        
        return count
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cur.close()
        conn.close()

def mark_notifications_as_read(user_id, org_id, notification_type):
    """
    Mark notifications as read when user visits a page
    
    Args:
        user_id: User ID
        org_id: Organization ID
        notification_type: Type of notification to mark as read
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications 
            SET is_read = 1 
            WHERE user_id = %s AND org_id = %s 
            AND notification_type = %s AND is_read = 0
        """, (user_id, org_id, notification_type))
        conn.commit()
    except Exception as e:
        print(f"Error marking notifications as read: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def get_recent_notifications(user_id, org_id, limit=10):
    """
    Get recent notifications for a user (both read and unread)
    
    Args:
        user_id: User ID
        org_id: Organization ID
        limit: Maximum number of notifications to return
    
    Returns:
        list: List of notification dictionaries
    """
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("""
            SELECT id, notification_type, reference_id, message, is_read, created_at
            FROM notifications 
            WHERE user_id = %s AND org_id = %s 
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, org_id, limit))
        
        notifications = cur.fetchall()
        
        # Convert datetime to string for JSON serialization
        for notif in notifications:
            if notif['created_at']:
                notif['created_at'] = notif['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return notifications
    except Exception as e:
        print(f"Error getting recent notifications: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def delete_old_notifications(days=30):
    """
    Delete read notifications older than specified days
    Can be called from a scheduled task
    
    Args:
        days: Number of days to keep notifications
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM notifications 
            WHERE is_read = 1 
            AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        deleted_count = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} old notifications")
        return deleted_count
    except Exception as e:
        print(f"Error deleting old notifications: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()
 ######################forgot password routes######################################   
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM register WHERE email = %s", (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user:
            otp = generate_otp()  # Generate random 6-digit OTP
            success, error = send_otp_email(email, otp)

            if success:
                session['reset_email'] = email
                session['reset_otp'] = otp
                session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=5)).timestamp()

                flash('OTP sent to your email. Please check your inbox.')
                return redirect(url_for('verify_reset_otp'))
            else:
                flash(f"Error sending OTP: {error}")
        else:
            flash("Email not registered.")
    
    return render_template('forgot_password.html')

##############################verify reset OTP######################################

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        
        if 'reset_otp' not in session or 'reset_email' not in session:
            flash("Session expired. Please try again.")
            return redirect(url_for('forgot_password'))

        # Check if OTP has expired
        if time.time() > session.get('reset_otp_expiry', 0):
            flash("OTP expired. Please request a new one.")
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session.pop('reset_otp_expiry', None)
            return redirect(url_for('forgot_password'))

        # Verify OTP
        if otp_input == session['reset_otp']:
            flash("OTP verified successfully. Please set a new password.")
            return redirect(url_for('reset_password'))
        else:
            flash("Invalid OTP. Please try again.")
    
    return render_template("verify_reset_otp.html")
##################################### reset password ######################################

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Ensure user has verified OTP first
    if 'reset_email' not in session:
        flash("Unauthorized access. Please start the password reset process again.")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('reset_password'))

        hashed_pw = generate_password_hash(new_password)
        email = session.get('reset_email')
        
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("UPDATE register SET password_hash = %s WHERE email = %s", (hashed_pw, email))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        # Clear all reset session values
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('reset_otp_expiry', None)

        flash("Password reset successful. You can now login with your new password.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')



######################################registration routes######################################
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'role' not in session or session['role'] != 'admin':
        flash("Only admin can register new users.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role'].strip().lower()

        # Only collect license/contact if architect
        license_number = request.form.get('license_number') if role == 'architect' else None
        contact_no = request.form.get('contact_no', '').strip()

        # Check if email already exists
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("SELECT email FROM register WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Email already exists.', 'error')
                return redirect(url_for('register'))

            # Generate OTP
            otp = generate_otp()
            
            # Send OTP email
            success, error = send_otp_email(email, otp)
            
            if success:
                # Store registration data in session temporarily
                session['pending_registration'] = {
                    'name': name,
                    'email': email,
                    'password': password,
                    'role': role,
                    'license_number': license_number,
                    'contact_no': contact_no,
                    'otp': otp,
                    'otp_expiry': (datetime.now() + timedelta(minutes=5)).timestamp()
                }
                
                flash('OTP sent to the user\'s email. Please verify to complete registration.', 'success')
                return redirect(url_for('verify_registration_otp'))
            else:
                flash(f"Error sending OTP: {error}", 'error')
                return redirect(url_for('register'))

        except Exception as e:
            flash(f'Registration failed: {e}', 'error')
            return redirect(url_for('register'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('register.html')
#######################################login routes######################################
@app.route('/login', methods=['GET', 'POST'])

def login():

    if request.method == 'GET':
        session.pop('_flashes', None) 
  
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM register WHERE email=%s", (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user['password_hash'], password):
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['org_id'] = user['org_id']
            
            flash('Login successful!')
            
            role = session['role']
            if role == 'admin':
                response = redirect(url_for('admin_dashboard'))
            elif role == 'site_engineer':
                response =redirect(url_for('site_engineer_dashboard'))
            elif role == 'architect':
                response = redirect(url_for('architect_dashboard'))
            elif role == 'accountant':
                response = redirect(url_for('accountant_dashboard'))
            else:
                flash('Invalid user role.')
                return redirect(url_for('login'))
            
        
            session.pop('_flashes', None)
            return response
        else:
            flash('Invalid email or password.')

    return render_template('login.html')

##########################################verify OTP######################################
# @app.route('/verify_otp', methods=['GET', 'POST'])
# def verify_otp():
#     if request.method == 'POST':
#         user_otp = request.form.get('otp', '').strip()
#         pending_user = session.get('pending_user')

#         if not pending_user:
#             flash("Session expired or invalid. Please login again.")
#             return redirect(url_for('login'))

#         # Check if OTP has expired
#         if time.time() > pending_user['otp_expiry']:
#             flash("OTP expired. Please login again.")
#             session.pop('pending_user', None)
#             return redirect(url_for('login'))

#         # Verify OTP
#         if user_otp == pending_user['otp']:
#             # OTP correct: promote to logged-in user
#             session['user_id'] = pending_user['id']
#             session['role'] = pending_user['role']
#             session['name'] = pending_user['name']
#             session['org_id'] = pending_user['org_id']
#             session.pop('pending_user', None)

#             flash('Login successful!')
            
#             # Redirect based on role
#             role = session['role']
#             if role == 'admin':
#                 response = redirect(url_for('admin_dashboard'))
#             elif role == 'site_engineer':
#                 response = redirect(url_for('site_engineer_dashboard'))
#             elif role == 'architect':
#                 response = redirect(url_for('architect_dashboard'))
#             elif role == 'accountant':
#                 response = redirect(url_for('accountant_dashboard'))
#             else:
#                 flash('Invalid user role.')
#                 return redirect(url_for('login'))
            
#             # Clear flash messages before redirecting
#             session.pop('_flashes', None)
#             return response
#         else:
#             flash("Invalid OTP. Please try again.")
            
#     return render_template("verify.html")
@app.route('/verify_registration_otp', methods=['GET', 'POST'])
def verify_registration_otp():
    if 'role' not in session or session['role'] != 'admin':
        flash("Only admin can register new users.")
        return redirect(url_for('login'))
    
    if 'pending_registration' not in session:
        flash("No pending registration found. Please start registration again.")
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        pending_data = session.get('pending_registration')
        
        if not pending_data:
            flash("Session expired. Please try again.")
            return redirect(url_for('register'))

        # Check if OTP has expired
        if time.time() > pending_data.get('otp_expiry', 0):
            flash("OTP expired. Please register again.")
            session.pop('pending_registration', None)
            return redirect(url_for('register'))

        # Verify OTP
        if otp_input == pending_data['otp']:
            # OTP is correct, proceed with registration
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # Get admin's org_id
                admin_id = session['user_id']
                cursor.execute("SELECT org_id FROM register WHERE id = %s", (admin_id,))
                admin_data = cursor.fetchone()
                
                if not admin_data:
                    flash("Unable to retrieve admin's organization.")
                    return redirect(url_for('register'))
                
                org_id = admin_data['org_id']

                # Hash password
                password_hash = generate_password_hash(pending_data['password'])

                # Insert user with org_id
                cursor.execute("""
                    INSERT INTO register (name, email, password_hash, role, contact_no, org_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    pending_data['name'], 
                    pending_data['email'], 
                    password_hash, 
                    pending_data['role'], 
                    pending_data['contact_no'],
                    org_id
                ))
                register_id = cursor.lastrowid
                conn.commit()

                # If architect, insert into architects table
                if pending_data['role'] == 'architect':
                    cursor.execute("""
                        INSERT INTO architects (name, email, license_number, contact_no, register_id, org_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        pending_data['name'], 
                        pending_data['email'], 
                        pending_data['license_number'], 
                        pending_data['contact_no'], 
                        register_id, 
                        org_id
                    ))
                    conn.commit()

                # Clear pending registration data
                session.pop('pending_registration', None)
                
                flash('User registered successfully!', 'success')
                return redirect(url_for('register'))

            except pymysql.err.IntegrityError:
                if conn:
                    conn.rollback()
                session.pop('pending_registration', None)
                flash('Email already exists.', 'error')
                return redirect(url_for('register'))

            except Exception as e:
                if conn:
                    conn.rollback()
                session.pop('pending_registration', None)
                flash(f'Registration failed: {e}', 'error')
                return redirect(url_for('register'))
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        else:
            flash("Invalid OTP. Please try again.", 'error')
    
    # Show OTP verification form
    return render_template("verify_registration_otp.html", email=session.get('pending_registration', {}).get('email'))
########################################admin routes######################################
@app.route('/admin1')

def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        # Clear any lingering flash messages
        session.pop('_flashes', None)
        admin_name = session.get('name')
        return render_template('admin_dashboard.html', admin_name=admin_name)
    return redirect('/')


#########################################site engineer routes######################################

@app.route('/siteengineer/dashboard')

def site_engineer_dashboard():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']

    # Fetch site engineer's name
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT name FROM register WHERE id = %s", (site_engineer_id,))
    engineer = cur.fetchone()

    # Fetch sites assigned to this engineer
    cur.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (site_engineer_id,))
    assigned_sites = cur.fetchall()

    # You can also fetch other dashboard data here if needed

    cur.close()
    conn.close()

    return render_template(
        'site_engineer_dashboard.html',
        engineer=engineer,
        assigned_sites=assigned_sites
    )

##########################################architect routes######################################

@app.route('/architect_dashboard', methods=['GET', 'POST'])
def architect_dashboard():
    if 'role' not in session or session['role'] != 'architect':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get architect details
        cur.execute("SELECT * FROM architects WHERE register_id = %s", (user_id,))
        architect = cur.fetchone()
        if not architect:
            return "Architect profile not found.", 404

        # Get projects for this architect
        cur.execute("SELECT id, project_name FROM projects WHERE architect_id = %s AND org_id = %s", (user_id, session['org_id']))
        project_list = cur.fetchall()

        selected_project = None
        project_details = {
            'design_details': None,
            'structural_details': None,
            'material_specifications': None,
            'site_conditions': None,
            'utilities_services': None,
            'cost_estimation': None,
            'drawing_documents': []
        }

        selected_project_id = request.form.get('selected_project_id') or request.args.get('project_id')
        if selected_project_id:
            # One big JOIN to fetch all details at once
            cur.execute("""
                SELECT 
                    p.id, p.project_name, p.architect_id, p.site_id,
                    dd.building_usage, dd.num_floors, dd.area_sqft, dd.plot_area, dd.fsi,
                    sd.foundation_type, sd.framing_system, sd.slab_type, sd.beam_details, sd.load_calculation,
                    ms.primary_material, ms.wall_material, ms.roofing_material, ms.flooring_material, ms.fire_safety_materials,
                    sc.soil_report_path, sc.water_table_level, sc.topo_counter_map_path,
                    us.water_supply_source, us.drainage_system_type, us.power_supply_source,
                    ce.architectural_design_cost, ce.structural_design_cost, ce.estimation_summary,
                    ce.boq_reference, ce.cost_per_sqft, ce.report_pdf_path
                FROM projects p
                LEFT JOIN design_details dd ON p.id = dd.project_id AND dd.org_id = %s
                LEFT JOIN structural_details sd ON p.id = sd.project_id AND sd.org_id = %s
                LEFT JOIN material_specifications ms ON p.id = ms.project_id AND ms.org_id = %s
                LEFT JOIN site_conditions sc ON p.id = sc.project_id AND sc.org_id = %s
                LEFT JOIN utilities_services us ON p.id = us.project_id AND us.org_id = %s
                LEFT JOIN cost_estimation ce ON p.id = ce.project_id AND ce.org_id = %s
                WHERE p.id = %s AND p.architect_id = %s AND p.org_id = %s
            """, (
                session['org_id'], session['org_id'], session['org_id'],
                session['org_id'], session['org_id'], session['org_id'],
                selected_project_id, user_id, session['org_id']
            ))
            selected_project = cur.fetchone()

            if selected_project:
                # --- Populate nested details from the flat row ---
                project_details['design_details'] = {
                    'building_usage': selected_project.get('building_usage'),
                    'num_floors': selected_project.get('num_floors'),
                    'area_sqft': selected_project.get('area_sqft'),
                    'plot_area': selected_project.get('plot_area'),
                    'fsi': selected_project.get('fsi'),
                } if any([selected_project.get('building_usage'), selected_project.get('num_floors')]) else None

                project_details['structural_details'] = {
                    'foundation_type': selected_project.get('foundation_type'),
                    'framing_system': selected_project.get('framing_system'),
                    'slab_type': selected_project.get('slab_type'),
                    'beam_details': selected_project.get('beam_details'),
                    'load_calculation': selected_project.get('load_calculation'),
                } if any([selected_project.get('foundation_type'), selected_project.get('framing_system')]) else None

                project_details['material_specifications'] = {
                    'primary_material': selected_project.get('primary_material'),
                    'wall_material': selected_project.get('wall_material'),
                    'roofing_material': selected_project.get('roofing_material'),
                    'flooring_material': selected_project.get('flooring_material'),
                    'fire_safety_materials': selected_project.get('fire_safety_materials'),
                } if any([selected_project.get('primary_material'), selected_project.get('wall_material')]) else None

                project_details['site_conditions'] = {
                    'soil_report_path': selected_project.get('soil_report_path'),
                    'water_table_level': selected_project.get('water_table_level'),
                    'topo_counter_map_path': selected_project.get('topo_counter_map_path'),
                } if selected_project.get('soil_report_path') or selected_project.get('water_table_level') else None

                project_details['utilities_services'] = {
                    'water_supply_source': selected_project.get('water_supply_source'),
                    'drainage_system_type': selected_project.get('drainage_system_type'),
                    'power_supply_source': selected_project.get('power_supply_source'),
                } if any([selected_project.get('water_supply_source'), selected_project.get('drainage_system_type')]) else None

                project_details['cost_estimation'] = {
                    'architectural_design_cost': selected_project.get('architectural_design_cost'),
                    'structural_design_cost': selected_project.get('structural_design_cost'),
                    'estimation_summary': selected_project.get('estimation_summary'),
                    'boq_reference': selected_project.get('boq_reference'),
                    'cost_per_sqft': selected_project.get('cost_per_sqft'),
                    'report_pdf_path': selected_project.get('report_pdf_path'),
                } if selected_project.get('architectural_design_cost') is not None else None

                # Fetch drawing documents separately (can be multiple)
                cur.execute("SELECT * FROM drawing_documents WHERE project_id = %s AND org_id = %s", (selected_project_id, session['org_id']))
                project_details['drawing_documents'] = cur.fetchall()

        return render_template(
            "architect_dashboard.html",
            architect=architect,
            project_list=project_list,
            selected_project=selected_project,
            details=project_details
        )

    except Exception as e:
        flash(f"Database error: {str(e)}", "error")
        return redirect(url_for('login'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ✅ Additional helper function to clean up duplicate architects
@app.route('/cleanup_architects', methods=['POST'])
def cleanup_architects():
    """
    Helper function to clean up duplicate architect entries
    Call this once to fix your database
    """
    if 'role' in session and session['role'] == 'architect':
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            # Find duplicate architects by email
            cur.execute("""
                SELECT email, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
                FROM architects 
                WHERE email IS NOT NULL 
                GROUP BY email 
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            
            for dup in duplicates:
                email = dup['email']
                keep_id = dup['keep_id']
                all_ids = dup['all_ids'].split(',')
                
                # Update all projects to use the kept architect ID
                for old_id in all_ids:
                    if int(old_id) != keep_id:
                        cur.execute("""
                            UPDATE projects 
                            SET architect_id = %s 
                            WHERE architect_id = %s
                        """, (keep_id, old_id))
                
                # Delete duplicate architect entries
                cur.execute("""
                    DELETE FROM architects 
                    WHERE email = %s AND id != %s
                """, (email, keep_id))
            
            conn.commit()
            return "Cleanup completed successfully!"
            
        except Exception as e:
            conn.rollback()
            return f"Error during cleanup: {e}"
        finally:
            conn.close()
    
    return "Unauthorized"

############################################## accountant routes ######################################
@app.route('/accountant_dashboard')
def accountant_dashboard():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))

    accountant_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT DISTINCT
            p.id AS project_id,
            p.project_name,
            i.id AS invoice_id,
            i.invoice_number,
            i.vendor_name,
            i.total_amount,
            i.gst_amount,
            i.generated_on,
            i.status,
            i.pdf_filename,
            i.bill_to_name,
            i.bill_to_address,
            i.subtotal,
            se.name AS site_engineer_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        LEFT JOIN invoices i ON i.project_id = p.id AND i.status = 'Approved'
        LEFT JOIN register se ON i.site_engineer_id = se.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        ORDER BY p.project_name, i.generated_on DESC
    """, (accountant_id, session['org_id']))
    results = cur.fetchall()

    # Organize the data by project
    projects_with_invoices = {}
    for row in results:
        project_id = row['project_id']
        if project_id not in projects_with_invoices:
            projects_with_invoices[project_id] = {
                'project_name': row['project_name'],
                'invoices': [],
                'seen_invoice_ids': set()
            }
        if row['invoice_id'] and row['invoice_id'] not in projects_with_invoices[project_id]['seen_invoice_ids']:
            projects_with_invoices[project_id]['invoices'].append(row)
            projects_with_invoices[project_id]['seen_invoice_ids'].add(row['invoice_id'])

    # Clean up helper set before passing to template
    for project in projects_with_invoices.values():
        project.pop('seen_invoice_ids', None)

    cur.close()
    conn.close()

    return render_template(
        'accountant_dashboard.html',
        projects_with_invoices=projects_with_invoices
    )
@app.route('/accountant/invoices')
def accountant_view_invoices():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    mark_notifications_as_read(accountant_id, org_id, 'invoice_approved')
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ✅ FIXED: Only fetch invoices strictly linked to assigned projects
    cur.execute("""
        SELECT DISTINCT
            p.id AS project_id,
            p.project_name,
            i.id AS invoice_id,
            i.invoice_number,
            i.vendor_name,
            i.total_amount,
            i.gst_amount,
            i.generated_on,
            i.status,
            i.pdf_filename,
            i.bill_to_name,
            i.bill_to_address,
            i.subtotal,
            se.name AS site_engineer_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        LEFT JOIN invoices i ON i.project_id = p.id AND i.status = 'Approved'
        LEFT JOIN register se ON i.site_engineer_id = se.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        ORDER BY p.project_name, i.generated_on DESC
    """, (accountant_id, org_id))
    results = cur.fetchall()

    projects_with_invoices = {}
    for row in results:
        project_id = row['project_id']
        if project_id not in projects_with_invoices:
            projects_with_invoices[project_id] = {
                'project_name': row['project_name'],
                'invoices': [],
                'seen_invoice_ids': set()
            }
        if row['invoice_id'] and row['invoice_id'] not in projects_with_invoices[project_id]['seen_invoice_ids']:
            projects_with_invoices[project_id]['invoices'].append(row)
            projects_with_invoices[project_id]['seen_invoice_ids'].add(row['invoice_id'])

    for project in projects_with_invoices.values():
        project.pop('seen_invoice_ids', None)

    cur.close()
    conn.close()

    return render_template(
        'accountant_view_invoices.html',
        projects_with_invoices=projects_with_invoices
    )
############################### Architect Project Management Routes ######################################
@app.route('/add_design_details', methods=['POST'])
def add_design_details():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        building_usage = request.form['building_usage']
        num_floors = request.form['num_floors']
        area_sqft = request.form['area_sqft']
        plot_area = request.form['plot_area']
        fsi = request.form['fsi']

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # Check if design details already exist for this project
            cur.execute("SELECT id FROM design_details WHERE project_id = %s AND org_id = %s",
                        (project_id, session['org_id']))
            existing = cur.fetchone()

            if existing:
                # Update existing record
                cur.execute("""
                    UPDATE design_details
                    SET building_usage = %s,
                        num_floors = %s,
                        area_sqft = %s,
                        plot_area = %s,
                        fsi = %s
                    WHERE project_id = %s AND org_id = %s
                """, (building_usage, num_floors, area_sqft, plot_area, fsi, project_id, session['org_id']))
                flash("Design details updated successfully.")
            else:
                # Insert new record if not present
                cur.execute("""
                    INSERT INTO design_details (project_id, building_usage, num_floors, area_sqft, plot_area, fsi, org_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (project_id, building_usage, num_floors, area_sqft, plot_area, fsi, session['org_id']))
                flash("Design details added successfully.")

            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
        
        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))

########################################### Add Structural Details ######################################

@app.route('/add_structural_details', methods=['POST'])
def add_structural_details():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        foundation_type = request.form['foundation_type']
        framing_system = request.form['framing_system']
        slab_type = request.form['slab_type']
        beam_details = request.form['beam_details']
        load_calculation = request.form['load_calculation']

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # Check if structural details already exist for this project and org
            cur.execute("SELECT id FROM structural_details WHERE project_id = %s AND org_id = %s",
                        (project_id, session['org_id']))
            existing = cur.fetchone()

            if existing:
                # Update existing record
                cur.execute("""
                    UPDATE structural_details
                    SET foundation_type = %s,
                        framing_system = %s,
                        slab_type = %s,
                        beam_details = %s,
                        load_calculation = %s
                    WHERE project_id = %s AND org_id = %s
                """, (foundation_type, framing_system, slab_type, beam_details, load_calculation, project_id, session['org_id']))
                flash("Structural details updated successfully.")
            else:
                # Insert new record
                cur.execute("""
                    INSERT INTO structural_details (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation, org_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation, session['org_id']))
                flash("Structural details added successfully.")

            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))


########################################## Add Material Specifications ######################################

@app.route('/add_material_specification', methods=['POST'])
def add_material_specification():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        primary_material = request.form['primary_material']
        wall_material = request.form['wall_material']
        roofing_material = request.form['roofing_material']
        flooring_material = request.form['flooring_material']
        fire_safety_materials = request.form['fire_safety_materials']

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # Check if material specification already exists for this project and org
            cur.execute("SELECT id FROM material_specifications WHERE project_id = %s AND org_id = %s",
                        (project_id, session['org_id']))
            existing = cur.fetchone()

            if existing:
                # Update existing record
                cur.execute("""
                    UPDATE material_specifications
                    SET primary_material = %s,
                        wall_material = %s,
                        roofing_material = %s,
                        flooring_material = %s,
                        fire_safety_materials = %s
                    WHERE project_id = %s AND org_id = %s
                """, (primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, project_id, session['org_id']))
                flash("Material specifications updated successfully.")
            else:
                # Insert new record
                cur.execute("""
                    INSERT INTO material_specifications (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, org_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, session['org_id']))
                flash("Material specifications added successfully.")

            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))

    
import os
from werkzeug.utils import secure_filename
from flask import request, redirect, flash, url_for, session

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

############################### Upload Drawing Documents ######################################

@app.route('/upload_layout', methods=['POST'])
def upload_layout():
    if 'role' in session and session['role'] == 'architect':
        file = request.files.get('layout_file')
        layout_type = request.form.get('layout_type')
        document_title = request.form.get('document_title')
        project_id = request.form.get('project_id')
        uploaded_by = session.get('user_id')

        required_types = ['Architectural Layout', 'Elevation Drawing', 'Section/Structural', 'Electrical', 'Plumbing/Sanitation']

        if layout_type in required_types and (not file or not allowed_file(file.filename)):
            flash("PDF file is required for selected layout type.")
            return redirect(url_for('architect_dashboard', project_id=project_id))

        file_path = ""
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            file_path = os.path.join('uploads', filename).replace("\\", "/")
        elif layout_type in required_types:
            flash("File upload failed or missing.")
            return redirect(url_for('architect_dashboard', project_id=project_id))

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM drawing_documents
                WHERE project_id = %s AND layout_type = %s
            """, (project_id, layout_type))
            existing = cur.fetchone()

            if existing:
                # Update existing document
                cur.execute("""
                    UPDATE drawing_documents
                    SET document_title = %s,
                        file_path = %s,
                        uploaded_by = %s,
                        uploaded_on = NOW()
                    WHERE project_id = %s AND layout_type = %s
                """, (document_title, file_path, uploaded_by, project_id, layout_type))
            else:
                # Insert new document
                cur.execute("""
                    INSERT INTO drawing_documents (
                        project_id, layout_type, document_title, file_path, uploaded_by, org_id
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (project_id, layout_type, document_title, file_path, uploaded_by, session['org_id']))

            conn.commit()
            flash("Drawing document uploaded successfully.")
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))


################################# site conditions #######################################
@app.route('/upload_site_conditions', methods=['POST'])
def upload_site_conditions():
    if 'role' in session and session['role'] == 'architect':
        soil_file = request.files.get('soil_report')
        topo_file = request.files.get('topo_map')
        water_table_level = request.form.get('water_table_level')
        project_id = request.form.get('project_id')

        soil_path = ""
        topo_path = ""

        if soil_file and allowed_file(soil_file.filename):
            soil_filename = secure_filename("soil_" + soil_file.filename)
            soil_save_path = os.path.join(app.config['UPLOAD_FOLDER'], soil_filename)
            soil_file.save(soil_save_path)
            soil_path = os.path.join('uploads', soil_filename).replace("\\", "/")

        if topo_file and allowed_file(topo_file.filename):
            topo_filename = secure_filename("topo_" + topo_file.filename)
            topo_save_path = os.path.join(app.config['UPLOAD_FOLDER'], topo_filename)
            topo_file.save(topo_save_path)
            topo_path = os.path.join('uploads', topo_filename).replace("\\", "/")

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO site_conditions (project_id, soil_report_path, water_table_level, topo_counter_map_path, org_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    soil_report_path = VALUES(soil_report_path),
                    water_table_level = VALUES(water_table_level),
                    topo_counter_map_path = VALUES(topo_counter_map_path)
            """, (project_id, soil_path, water_table_level, topo_path, session['org_id']))
            conn.commit()
            flash("Site condition documents uploaded successfully.")
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))


#############################################logout route######################################

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


############################# Submit Worker Report ######################################
@app.route('/submit_worker_report', methods=['GET', 'POST'])
def submit_worker_report():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']
    org_id = session['org_id']
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Handle POST submission
    if request.method == 'POST':
        project_id = request.form['project_id']
        worker_count = request.form['worker_count']
        report_date = request.form['report_date']

        try:
            cur.execute("""
                INSERT INTO daily_worker_report (site_engineer_id, project_id, worker_count, report_date, org_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (site_engineer_id, project_id, worker_count, report_date, org_id))
            
            report_id = cur.lastrowid
            conn.commit()
            
            # ========== NOTIFICATION CODE ==========
            # Get project name for notification message
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            project = cur.fetchone()
            project_name = project['project_name'] if project else 'Unknown Project'
            
            # Get all admins in the organization
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()
            
            # Create notification for each admin
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='worker_report_new',
                    reference_id=report_id,
                    message=f'Worker report submitted: {worker_count} workers at {project_name} on {report_date} by {session.get("name")}',
                    cur=cur
                )
            conn.commit()
            # ========================================
            
            flash('Worker report submitted successfully.')
            
        except Exception as e:
            conn.rollback()
            flash(f'Error submitting report: {str(e)}')
        finally:
            cur.close()
            conn.close()
            
        return redirect(url_for('submit_worker_report'))

    # Fetch only projects assigned to this site engineer (by admin)
    cur.execute("""
        SELECT p.*
        FROM projects p
        JOIN sites s ON p.project_name = s.site_name
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (site_engineer_id, org_id))
    projects = cur.fetchall()
    
    cur.close()
    conn.close()

    return render_template('submit_worker_report.html', projects=projects)

########################################## View Worker Reports ######################################
@app.route('/view_worker_reports')
def view_worker_reports():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    org_id = session.get('org_id')

    if session['role'] == 'admin':
        mark_notifications_as_read(user_id, org_id, 'worker_report_new')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        
        if not org_id:
            flash("User organization not found.", "danger")
            return redirect(url_for('login'))

        if session['role'] == 'admin':
            cur.execute("""
                SELECT 
                    dr.id, 
                    r.name AS site_engineer, 
                    p.project_name, 
                    dr.worker_count, 
                    dr.report_date,
                    dr.org_id
                FROM daily_worker_report dr
                JOIN projects p ON dr.project_id = p.id
                JOIN register r ON dr.site_engineer_id = r.id
                WHERE dr.org_id = %s
                ORDER BY dr.report_date DESC
            """, (org_id,))
            reports = cur.fetchall()

        else:
            cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
            engineer = cur.fetchone()
            engineer_name = engineer['name'] if engineer else 'Unknown'

            cur.execute("""
                SELECT 
                    dr.id, 
                    p.project_name, 
                    dr.worker_count, 
                    dr.report_date
                FROM daily_worker_report dr
                JOIN projects p ON dr.project_id = p.id
                WHERE dr.site_engineer_id = %s AND dr.org_id = %s
                ORDER BY dr.report_date DESC
            """, (user_id, org_id))
            reports = cur.fetchall()

            for report in reports:
                report['site_engineer'] = engineer_name

        return render_template('view_worker_reports.html', reports=reports)

    except Exception as e:
        flash(f"Error loading reports: {str(e)}", "danger")
        return redirect(url_for('login'))

    finally:
        cur.close()
        conn.close()


########################################## Add Inventory ######################################
@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session or 'user_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = None
        cursor = None
        try:
            material_descriptions = request.form.getlist('material_description[]')
            quantities            = request.form.getlist('quantity[]')
            status                = request.form['status']
            inv_date              = request.form['date']
            org_id                = session['org_id']
            site_engineer_id      = session['user_id']
            engineer_name         = session.get('name', 'Engineer')

            # ── Validate arrays match ──
            if len(material_descriptions) != len(quantities):
                flash('Error: Mismatched material descriptions and quantities', 'danger')
                return redirect(url_for('add_inventory'))

            # ── Validate at least one item ──
            if not material_descriptions or not material_descriptions[0].strip():
                flash('Error: At least one material description is required', 'danger')
                return redirect(url_for('add_inventory'))

            conn   = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            insert_query = """
                INSERT INTO inventory (material_description, quantity, date, status, org_id, site_engineer_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            items_added    = 0
            inventory_items = []

            for i in range(len(material_descriptions)):
                desc    = material_descriptions[i].strip()
                qty_str = quantities[i].strip()

                if not desc or not qty_str:
                    continue

                try:
                    qty = int(qty_str)
                    if qty < 0:
                        flash(f'Error: Quantity cannot be negative for item {i + 1}', 'danger')
                        conn.rollback()
                        return redirect(url_for('add_inventory'))
                except ValueError:
                    flash(f'Error: Invalid quantity for item {i + 1}', 'danger')
                    conn.rollback()
                    return redirect(url_for('add_inventory'))

                cursor.execute(insert_query, (desc, qty, inv_date, status, org_id, site_engineer_id))
                items_added += 1
                inventory_items.append(f"{desc} (Qty: {qty})")

            if items_added == 0:
                flash('Error: No valid items to add', 'danger')
                conn.rollback()
                return redirect(url_for('add_inventory'))

            # ── Commit inventory inserts first ──
            conn.commit()

            # ── Notifications after successful commit ──
            # Use a fresh cursor after commit
            cursor.close()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            try:
                cursor.execute("""
                    SELECT id FROM register 
                    WHERE role = 'admin' AND org_id = %s
                """, (org_id,))
                admins = cursor.fetchall()

                if items_added == 1:
                    notification_message = f'{engineer_name} added inventory: {inventory_items[0]}'
                elif items_added <= 3:
                    items_preview        = ', '.join(inventory_items)
                    notification_message = f'{engineer_name} added {items_added} inventory items: {items_preview}'
                else:
                    items_preview        = ', '.join(inventory_items[:2]) + f' and {items_added - 2} more items'
                    notification_message = f'{engineer_name} added {items_added} inventory items: {items_preview}'

                for admin in admins:
                    create_notification(
                        user_id=admin['id'],
                        org_id=org_id,
                        notification_type='inventory_added',
                        reference_id=None,
                        message=notification_message,
                        cur=cursor
                    )
                conn.commit()
            except Exception as notif_err:
                # Notification failure should NOT rollback the inventory that was already saved
                print(f"Warning: Notification failed after inventory commit: {notif_err}")

            if items_added == 1:
                flash('1 inventory item added successfully!', 'success')
            else:
                flash(f'{items_added} inventory items added successfully!', 'success')

            return redirect(url_for('add_inventory'))

        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error adding inventory: {str(e)}', 'danger')
            return redirect(url_for('add_inventory'))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('add_inventory.html')


######################################## View Inventory ######################################

@app.route('/view_inventory')
def view_inventory():
    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    user_id = session.get('user_id')
    role = session.get('role')
    
    # Mark inventory notifications as read for admins
    if role == 'admin':
        mark_notifications_as_read(user_id, org_id, 'inventory_added')
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT 
                inventory.*,
                register.name AS site_engineer_name
            FROM inventory
            JOIN register ON inventory.site_engineer_id = register.id
            WHERE inventory.org_id = %s
            ORDER BY inventory.date DESC
        """, (org_id,))
        
        inventory = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading inventory: {str(e)}", "danger")
        inventory = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    response = make_response(render_template('view_inventory.html', inventory=inventory))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response
########################---assign sites---#######################################
@app.route('/assign_site', methods=['GET', 'POST'])
def assign_site():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            "SELECT id, name FROM register WHERE role = 'site_engineer' AND org_id = %s",
            (session['org_id'],)
        )
        engineers = cursor.fetchall()

        if request.method == 'POST':
            site_name = request.form['site_name'].strip()
            location = request.form['location'].strip()
            engineer_id = request.form['site_engineer_id']

            # Check duplicate
            cursor.execute(
                "SELECT site_id FROM sites WHERE LOWER(site_name) = LOWER(%s) AND site_engineer_id = %s AND org_id = %s",
                (site_name, engineer_id, session['org_id'])
            )
            existing = cursor.fetchone()

            if existing:
                flash('This site name is already assigned to this Project Manager.', 'error')
                return render_template('assign_site.html', engineers=engineers)

            # Insert site
            cursor.execute(
                "INSERT INTO sites (site_name, location, site_engineer_id, org_id) VALUES (%s, %s, %s, %s)",
                (site_name, location, engineer_id, session['org_id'])
            )
            site_id = cursor.lastrowid
            

            # Notification (after commit)
            create_notification(
                user_id=engineer_id,
                org_id=session['org_id'],
                notification_type='project_assigned',
                reference_id=site_id,
                message=f'New site assigned: {site_name} at {location}',
                cur=cursor    # <-- add this
            )
            conn.commit()

            flash('Site assigned successfully.', 'success')
            return redirect(url_for('assign_site'))

        return render_template('assign_site.html', engineers=engineers)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('assign_site'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ✅ AJAX endpoint — checks duplicate based on site_name + site_engineer_id
@app.route('/check_duplicate_site', methods=['POST'])
def check_duplicate_site():
    data = request.get_json()
    site_name   = data.get('site_name', '').strip()
    engineer_id = data.get('site_engineer_id', '')

    if not site_name or not engineer_id:
        return jsonify({ "duplicate": False })

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:

        cursor.execute(
            "SELECT site_id FROM sites WHERE LOWER(site_name) = LOWER(%s) AND site_engineer_id = %s AND org_id = %s",
            (site_name, engineer_id, session['org_id'])
        )
        exists = cursor.fetchone()
    finally:
        cursor.close()
        db.close()

    return jsonify({ "duplicate": exists is not None })

################################--- View Assigned Sites ---###################

@app.route('/view_assigned_sites')
def view_assigned_sites():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    engineer_id = session['user_id']  # Make sure user_id is set on login
    mark_notifications_as_read(
        user_id=session['user_id'],
        org_id=session['org_id'],
        notification_type='project_assigned'
    )

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:

        cursor.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (engineer_id,))
        sites = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template('view_assigned_sites.html', sites=sites)


######################## 🌟 Upload Progress Report (SITE ENGINEER)###################
@app.route('/upload_progress', methods=['GET', 'POST'])
def upload_progress():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']

    if request.method == 'POST':
        site_id = request.form['site_id']
        progress = request.form['progress']
        remark = request.form['remark']
        today = date.today()

        img_filename = None
        img = request.files.get('image')
        if img and img.filename:
            ext = img.filename.rsplit('.', 1)[1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                img_filename = f"{int(time.time())}_{secure_filename(img.filename)}"
                img.save(os.path.join(UPLOAD_FOLDER_PROGRESS, img_filename))

        pdf_filename = None
        pdf = request.files.get('pdf')
        if pdf and pdf.filename:
            ext = pdf.filename.rsplit('.', 1)[1].lower()
            if ext == 'pdf':
                pdf_filename = f"{int(time.time())}_{secure_filename(pdf.filename)}"
                pdf.save(os.path.join(UPLOAD_FOLDER_PROGRESS, pdf_filename))

        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("""
                INSERT INTO progress_reports 
                (site_id, progress_percent, image_path, pdf_path, report_date, remark, org_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (site_id, progress, img_filename, pdf_filename, today, remark, session['org_id']))
            
            conn.commit()

            cursor.execute("SELECT site_name FROM sites WHERE site_id = %s", (site_id,))
            site_data = cursor.fetchone()
            site_name = site_data['site_name'] if site_data else 'Unknown Site'

            cursor.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (session['org_id'],))
            admins = cursor.fetchall()

            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=session['org_id'],
                    notification_type='progress_report',
                    reference_id=site_id,
                    message=f'Progress report uploaded for {site_name}: {progress}% complete by {session.get("name")}',
                    cur=cursor    # <-- add this
                )
            conn.commit()

            flash('Progress report uploaded successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error uploading progress report: {str(e)}', 'danger')

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('upload_progress'))

    # GET request
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            "SELECT * FROM sites WHERE site_engineer_id = %s AND org_id = %s",
            (site_engineer_id, session['org_id'])
        )
        sites = cursor.fetchall()
        return render_template('upload_progress.html', sites=sites)

    except Exception as e:
        flash(f'Error loading sites: {str(e)}', 'danger')
        return redirect(url_for('site_engineer_dashboard'))

    finally:
        cursor.close()
        conn.close()


################################### View Progress Reports (ADMIN)###############################################
@app.route('/view_progress')
def view_progress():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    

    admin_id = session['user_id']
    org_id = session['org_id']

    mark_notifications_as_read(admin_id, org_id, 'progress_report')

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)


    # Use the correct SQL order: WHERE before ORDER BY
    # Assuming org_id is in the sites table
    try:
        query = """
            SELECT pr.*, s.site_name, pr.report_date AS upload_date
            FROM progress_reports pr
            JOIN sites s ON pr.site_id = s.site_id
            WHERE s.org_id = %s
            ORDER BY pr.report_date DESC
        """

        cursor.execute(query, (session['org_id'],))
        reports = cursor.fetchall()

        return render_template('view_progress.html', reports=reports)
    finally:
        cursor.close()
        db.close()


# ✅ Vendor Inventory with PDF quotes by site engineer & admin approval

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER_VENDOR = 'static/vendor_quotes'
os.makedirs(UPLOAD_FOLDER_VENDOR, exist_ok=True)
ALLOWED_EXT = {'pdf'}

def allowed(filename: str) -> bool:
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

####################################add_vendor_inventory######################################## 
@app.route('/add_vendor_inventory', methods=['GET', 'POST'])
def add_vendor_inventory():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        materials  = request.form.getlist('material_description[]')
        quantities = request.form.getlist('quantity[]')
        statuses   = request.form.getlist('status[]')
        vendors    = request.form.getlist('vendor_name[]')
        v_types    = request.form.getlist('vendor_type[]')
        files      = request.files.getlist('quotation[]')

        if not materials:
            flash('No items submitted.', 'danger')
            return redirect(url_for('add_vendor_inventory'))

        # ✅ Get submitter info
        site_engineer_id = session['user_id']
        org_id = session['org_id']

        db = get_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        try:
            added = 0
            
            for i in range(len(materials)):
                if not materials[i].strip():
                    continue

                file = files[i]
                filename = None
                
                if file and allowed(file.filename):
                    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
                    file.save(os.path.join(UPLOAD_FOLDER_VENDOR, filename))
                else:
                    db.rollback()
                    cursor.close()
                    db.close()
                    flash('Please upload a valid PDF for every item.', 'danger')
                    return redirect(url_for('add_vendor_inventory'))

                # ✅ Insert with site_engineer_id
                cursor.execute("""
                    INSERT INTO vendor_inventory
                    (material_description, quantity, date, status,
                     vendor_name, vendor_type, vendor_quotation_pdf, org_id, site_engineer_id)
                    VALUES (%s, %s, CURDATE(), %s, %s, %s, %s, %s, %s)
                """, (
                    materials[i],
                    int(quantities[i]),
                    statuses[i],
                    vendors[i],
                    v_types[i],
                    filename,
                    org_id,
                    site_engineer_id
                ))
                
                added += 1

            db.commit()

            # Notify admins about pending items
            if added > 0:
                cursor.execute("""
                    SELECT id FROM register 
                    WHERE role = 'admin' AND org_id = %s
                """, (org_id,))
                admins = cursor.fetchall()
                
                summary = f'{added} vendor inventory item(s) submitted for approval by {session.get("name")}'
                
                for admin in admins:
                    create_notification(
                        user_id=admin['id'],
                        org_id=org_id,
                        notification_type='vendor_pending',
                        reference_id=None,
                        message=summary,
                        cur=cursor
                    )
                db.commit()

            flash(f'{added} item(s) added successfully!', 'success')

        except Exception as e:
            db.rollback()
            print(f"Error in add_vendor_inventory: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding vendor inventory: {str(e)}', 'danger')
            
        finally:
            cursor.close()
            db.close()

        return redirect(url_for('add_vendor_inventory'))

    return render_template('add_vendor_inventory.html')

###################### --- Admin View Vendor Inventory --- ####################################################

@app.route('/admin/vendor_inventory', methods=['GET', 'POST'])
def admin_vendor_inventory():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    org_id = session.get('org_id')
    mark_notifications_as_read(admin_id, org_id, 'vendor_pending')

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        rec_id = request.form['id']
        remark = request.form['remark']
        approval = request.form['approval']

        try:
            # ✅ This will now work because site_engineer_id exists
            cursor.execute("""
                SELECT 
                    material_description, 
                    vendor_name, 
                    quantity,
                    site_engineer_id
                FROM vendor_inventory
                WHERE id = %s AND org_id = %s
            """, (rec_id, org_id))
            vendor_data = cursor.fetchone()

            # Update record
            cursor.execute("""
                UPDATE vendor_inventory 
                SET admin_remark=%s, admin_approval=%s 
                WHERE id=%s AND org_id=%s
            """, (remark, approval, rec_id, org_id))
            
            
            # ========== NOTIFICATION - ONLY SUBMITTER ==========
            if vendor_data and vendor_data.get('site_engineer_id'):
                material_desc = vendor_data['material_description']
                vendor_name = vendor_data['vendor_name']
                quantity = vendor_data['quantity']
                submitter_id = vendor_data['site_engineer_id']
                
                if approval.lower() == 'approved':
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} has been approved'
                    notification_type = 'vendor_approved'
                elif approval.lower() == 'rejected':
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} has been rejected'
                    notification_type = 'vendor_rejected'
                else:
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} status updated to {approval}'
                    notification_type = 'vendor_status_updated'
                
                if remark and remark.strip():
                    notification_message += f'. Remark: {remark}'
                
                # ✅ NOTIFY ONLY THE SUBMITTER
                create_notification(
                    user_id=submitter_id,
                    org_id=org_id,
                    notification_type=notification_type,
                    reference_id=rec_id,
                    message=notification_message,
                    cur=cursor
                )

            db.commit()
            # ===================================================
            
            flash(f'Vendor inventory {approval.lower()} successfully.', 'success')
            
        except Exception as e:
            db.rollback()
            flash(f'Error updating vendor inventory: {str(e)}', 'danger')
        finally:
            cursor.close()
            db.close()
        
        active_tab = request.args.get('tab', 'all')
        return redirect(url_for('admin_vendor_inventory', tab=active_tab))

    # GET request
    active_tab = request.args.get('tab', 'all')

    cursor.execute("""
        SELECT * FROM vendor_inventory 
        WHERE org_id = %s
        ORDER BY 
            CASE admin_approval
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'rejected' THEN 3
            END,
            id DESC
    """, (org_id,))
    
    all_inventory = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN admin_approval = 'pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN admin_approval = 'approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN admin_approval = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            COUNT(*) as total_count
        FROM vendor_inventory 
        WHERE org_id = %s
    """, (org_id,))
    
    counts = cursor.fetchone()
    cursor.close()
    db.close()
    
    return render_template('admin_vendor_inventory.html', 
                         inventory=all_inventory,
                         active_tab=active_tab,
                         counts=counts)



########################################### Site Engineer View Inventory ######################################
@app.route('/site_engineer/view_inventory')
def site_engineer_view_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT * FROM inventory
            WHERE org_id = %s
            ORDER BY date DESC
        """, (org_id,))
        data = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading inventory: {str(e)}", "danger")
        data = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('view_inventory.html', inventory=data)



############################################ Site Engineer Approved Vendor Inventory ######################################
@app.route('/site_engineer/approved_vendor_inventory')
def site_engineer_approved_vendor_quotations():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    site_engineer_id = session['user_id']
    mark_notifications_as_read(site_engineer_id, org_id, 'vendor_approved')
    mark_notifications_as_read(site_engineer_id, org_id, 'vendor_rejected')
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT * FROM vendor_inventory
            WHERE admin_approval = 'approved' AND org_id = %s
            ORDER BY date DESC
        """, (org_id,))
        approved_inventory = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading approved vendor inventory: {str(e)}", "danger")
        approved_inventory = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('site_engineer_approved_vendor_quotations.html', inventory=approved_inventory)



############################################### Add Enquiry ######################################
@app.route('/add_enquiry', methods=['GET', 'POST'])
def add_enquiry():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact_no = request.form['contact_no']
        requirement = request.form['requirement']
        engineer_id = session['user_id']
        org_id = session.get('org_id')

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute("""
                INSERT INTO enquiries (site_engineer_id, name, address, contact_no, requirement, org_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (engineer_id, name, address, contact_no, requirement, org_id))
            enquiry_id = cur.lastrowid
            conn.commit()

            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()

            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='enquiry_new',
                    reference_id=enquiry_id,
                    message=f'New visitor enquiry from {name} submitted by {session.get("name")}',
                    cur=cur    # <-- add this
                )
            conn.commit()

            flash('Enquiry submitted successfully.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error submitting enquiry: {str(e)}', 'danger')

        finally:
            cur.close()
            conn.close()

        return redirect(url_for('add_enquiry'))

    return render_template('add_enquiry.html')

    
################################################ View Enquiries ######################################
@app.route('/admin/enquiries')
def view_enquiries():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            org_id = session.get('org_id')
            user_id = session.get('user_id')

            # Mark notifications as read when admin views enquiries
            if session['role'] == 'admin':
                mark_notifications_as_read(
                    user_id=user_id,
                    org_id=org_id,
                    notification_type='enquiry_new'
                )

            if session['role'] == 'admin':
                cur.execute("""
                    SELECT e.*, r.name AS engineer_name 
                    FROM enquiries e
                    JOIN register r ON e.site_engineer_id = r.id
                    WHERE e.org_id = %s
                    ORDER BY e.enquiry_date DESC
                """, (org_id,))
            else:  # site_engineer
                site_engineer_id = session['user_id']
                cur.execute("""
                    SELECT e.*, r.name AS engineer_name 
                    FROM enquiries e
                    JOIN register r ON e.site_engineer_id = r.id
                    WHERE e.site_engineer_id = %s AND e.org_id = %s
                    ORDER BY e.enquiry_date DESC
                """, (site_engineer_id, org_id))

            enquiries = cur.fetchall()
        except Exception as e:
            flash(f"Error loading enquiries: {str(e)}", "danger")
            enquiries = []
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
        
        return render_template('view_enquiry.html', enquiries=enquiries)
    else:
        return redirect(url_for('login'))

    

 ################################################# Add Architect ######################################   
@app.route('/add_architect', methods=['GET', 'POST'])
def add_architect():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Always fetch engineers and sites for the form
        cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer' AND org_id = %s", (session['org_id'],))
        engineers = cursor.fetchall()
        cursor.execute("SELECT site_id, site_name FROM sites WHERE org_id = %s", (session['org_id'],))
        sites = cursor.fetchall()

        if request.method == 'POST':
            name = request.form['name']
            license_number = request.form.get('license_number', '')
            contact_no = request.form.get('contact_no', '')
            email = request.form['email']
            site_id = request.form['project_name']      # actually site_id
            site_engineer_id = request.form['site_engineer_id']

            # Get site name
            selected_site_name = next((s['site_name'] for s in sites if str(s['site_id']) == site_id), '')
            
            cursor.execute("""
                INSERT INTO architects (name, license_number, contact_no, email, project_name, site_engineer_id, org_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, license_number, contact_no, email, selected_site_name, site_engineer_id, session['org_id']))
            conn.commit()
            flash('Architect added successfully.')
            return redirect(url_for('view_architects'))

        return render_template('add_architect.html', engineers=engineers, sites=sites)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('add_architect'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


################################################# View Architects ######################################
@app.route('/view_architects')
def view_architects():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:

            if session['role'] == 'site_engineer':
                site_engineer_id = session['user_id']
                cur.execute("SELECT * FROM architects WHERE site_engineer_id = %s", (site_engineer_id,))
            else:
                cur.execute("SELECT * FROM architects")

            architects = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return render_template('view_architects.html', architects=architects)
    return redirect(url_for('login'))



########################################### View Architect Details ######################################
@app.route('/view_architect_details/<int:architect_id>')
def view_architect_details(architect_id):
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM architects WHERE id = %s", (architect_id,))
            architect = cur.fetchone()
            
            if not architect:
                flash('Architect not found.', 'error')
                return redirect(url_for('view_architects'))
                
            return render_template('architect_detail.html', architect=architect)
            
        except Exception as e:
            flash(f'Error fetching architect details: {str(e)}', 'error')
            return redirect(url_for('view_architects'))
        finally:
            if conn:
                conn.close()
    return redirect(url_for('login'))

########################################### Upload Utilities Services ######################################

@app.route('/upload_utilities_services', methods=['POST'])
def upload_utilities_services():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form.get('project_id')
        water_supply = request.form.get('water_supply_source')
        drainage_system = request.form.get('drainage_system_type')
        power_supply = request.form.get('power_supply_source')

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO utilities_services (
                    project_id, water_supply_source, drainage_system_type, power_supply_source, org_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    water_supply_source = VALUES(water_supply_source),
                    drainage_system_type = VALUES(drainage_system_type),
                    power_supply_source = VALUES(power_supply_source)
            """, (project_id, water_supply, drainage_system, power_supply, session['org_id']))
            conn.commit()
            flash("Utilities Services uploaded successfully.")
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Database error: {str(e)}", "error")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))



############################################ Upload Cost Estimation ######################################
# @app.route('/upload_cost_estimation', methods=['POST'])
# def upload_cost_estimation():
#     if 'role' in session and session['role'] == 'architect':
#         project_id = request.form.get('project_id')
#         arch_cost = request.form.get('architectural_design_cost')
#         struct_cost = request.form.get('structural_design_cost')
#         summary = request.form.get('estimation_summary')
#         boq = request.form.get('boq_reference')
#         cost_per_sqft = request.form.get('cost_per_sqft')
#         org_id = session['org_id']

#         # Ensure the upload directory exists
#         os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

#         # Generate unique PDF filename
#         filename = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
#         save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         #relative_path = os.path.join('uploads', os.path.basename(app.config['UPLOAD_FOLDER']), filename).replace("\\", "/")
#         relative_path = os.path.join('uploads', filename).replace("\\", "/")


#         # Create PDF from submitted data
#         pdf_data = {
#             "Project ID": project_id,
#             "Architectural Design Cost": arch_cost,
#             "Structural Design Cost": struct_cost,
#             "Estimation Summary": summary,
#             "BOQ Reference": boq,
#             "Cost per Sqft": cost_per_sqft
#         }
#         generate_estimation_pdf(pdf_data, save_path)

#         # Save to DB
#         conn = get_connection()
#         cur = conn.cursor()

#         # Update if project already has entry
#         cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s and org_id = %s", (project_id,org_id))
#         if cur.fetchone():
#             cur.execute("""
#                 UPDATE cost_estimation
#                 SET architectural_design_cost = %s,
#                     structural_design_cost = %s,
#                     estimation_summary = %s,
#                     boq_reference = %s,
#                     cost_per_sqft = %s,
#                     report_pdf_path = %s,
#                     generated_on = NOW()
#                 WHERE project_id = %s and org_id = %s
#             """, (arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path, project_id,org_id))
#         else:
#             cur.execute("""
#                 INSERT INTO cost_estimation
#                     (project_id, architectural_design_cost, structural_design_cost,
#                      estimation_summary, boq_reference, cost_per_sqft, report_pdf_path,org_id)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
#             """, (project_id, arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path,org_id))

#         conn.commit()
#         conn.close()

#         flash("Cost estimation saved and PDF generated.")
#         return redirect(url_for('architect_dashboard'))

#     flash("Unauthorized access.")
#     return redirect(url_for('login'))




########################################## Generate PDF for Cost Estimation ######################################
def generate_estimation_pdf(data, save_path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(save_path, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Cost Estimation Report")
    y -= 30

    c.setFont("Helvetica", 12)
    for label, value in data.items():
        c.drawString(50, y, f"{label}: {value}")
        y -= 20

    c.save()
########################################### Generate Cost Estimation PDF ######################################
@app.route('/generate_cost_estimation_pdf', methods=['POST'])
def generate_cost_estimation_pdf():
    if 'role' not in session or session['role'] != 'architect':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        project_id = request.form['project_id']
        architectural_cost = request.form['architectural_design_cost']
        structural_cost = request.form['structural_design_cost']
        estimation_summary = request.form['estimation_summary']
        boq_reference = request.form['boq_reference']
        cost_per_sqft = request.form['cost_per_sqft']
        org_id = session['org_id']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s AND org_id = %s", (project_id, org_id))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE cost_estimation 
                SET architectural_design_cost = %s,
                    structural_design_cost = %s,
                    estimation_summary = %s,
                    boq_reference = %s,
                    cost_per_sqft = %s,
                    generated_on = NOW()
                WHERE project_id = %s AND org_id = %s
            """, (architectural_cost, structural_cost, estimation_summary, boq_reference, cost_per_sqft, project_id, org_id))
        else:
            cur.execute("""
                INSERT INTO cost_estimation 
                (project_id, architectural_design_cost, structural_design_cost, 
                 estimation_summary, boq_reference, cost_per_sqft, generated_on, org_id)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (project_id, architectural_cost, structural_cost, estimation_summary,
                  boq_reference, cost_per_sqft, org_id))
        conn.commit()
        cur.close()
        conn.close()

        # Start background PDF generation
        thread = threading.Thread(
            target=generate_cost_estimation_pdf_async,
            args=(project_id, org_id)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'project_id': project_id})

    except Exception as e:
        print("Error in generate_cost_estimation_pdf:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/cost_estimation_status/<int:project_id>')
def api_cost_estimation_status(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT report_pdf_path FROM cost_estimation WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
        result = cur.fetchone()
        if result and result['report_pdf_path']:
            return jsonify({'status': 'ready', 'pdf_path': result['report_pdf_path']})
        else:
            return jsonify({'status': 'processing'})
    finally:
        cur.close()
        conn.close()

@app.route('/download_cost_estimation_pdf/<int:project_id>')
def download_cost_estimation_pdf(project_id):
    if 'user_id' not in session:
        abort(401)
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT report_pdf_path FROM cost_estimation WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
        result = cur.fetchone()
        if result and result['report_pdf_path']:
            # Ensure the file exists
            file_path = os.path.join(app.root_path, 'static', result['report_pdf_path'])
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True, download_name=f"cost_estimation_{project_id}.pdf")
            else:
                flash('PDF file not found. It may still be generating.', 'warning')
        else:
            flash('PDF not ready yet. Please try again later.', 'warning')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('architect_dashboard'))



############################################ Assign Architect to Project ######################################@app.route('/select_project_by_org')@app.route('/select_project_by_org', methods=['GET'])
@app.route('/select_project_by_org', methods=['GET'])
def select_project_by_org():
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    org_id = session['org_id']
    print("Org ID from session:", org_id)

    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = "SELECT site_id, site_name FROM sites WHERE org_id = %s"
        print("Running query...")
        cursor.execute(query, (org_id,))
        projects = cursor.fetchall()
        print("Fetched projects:", projects)

        return jsonify({'status': 'success', 'projects': projects})

    except Exception as e:
        import traceback
        print("DB error in /select_project_by_org:", e)
        traceback.print_exc()
    return jsonify({'status': 'error', 'message': 'Error loading projects'}), 500



@app.route('/assign_architect', methods=['GET', 'POST'])
def assign_architect():
    if 'role' in session and session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Get sites assigned to site engineers (depends on role)
        if session['role'] == 'admin':
            cursor.execute("""
                SELECT s.site_id, s.site_name
                FROM sites s
                WHERE s.site_engineer_id IS NOT NULL AND s.org_id = %s
            """, (session['org_id'],))
        else:
            site_engineer_id = session['user_id']
            cursor.execute("""
                SELECT s.site_id, s.site_name
                FROM sites s
                WHERE s.site_engineer_id = %s AND s.org_id = %s
            """, (site_engineer_id, session['org_id']))
        projects = cursor.fetchall()

        cursor.execute("SELECT id, name FROM register WHERE role = 'architect' AND org_id = %s", (session['org_id'],))
        architects = cursor.fetchall()

        if request.method == 'POST':
            site_id = request.form['project_id']
            architect_id = request.form['architect_id']

            # Begin transaction
            conn.begin()
            cursor.execute("SELECT site_name FROM sites WHERE site_id = %s AND org_id = %s", (site_id, session['org_id']))
            site = cursor.fetchone()

            if site:
                project_name = site['site_name']

                # Check if project already exists for this site
                cursor.execute("SELECT id FROM projects WHERE site_id = %s AND org_id = %s LIMIT 1", (site_id, session['org_id']))
                existing_project = cursor.fetchone()

                if existing_project:
                    project_id = existing_project['id']
                    cursor.execute("UPDATE projects SET architect_id = %s WHERE id = %s", (architect_id, project_id))
                else:
                    cursor.execute("""
                        INSERT INTO projects (project_name, architect_id, site_id, org_id)
                        VALUES (%s, %s, %s, %s)
                    """, (project_name, architect_id, site_id, session['org_id']))
                    project_id = cursor.lastrowid

                create_notification(
                    user_id=architect_id,
                    org_id=session['org_id'],
                    notification_type='project_assigned',
                    reference_id=project_id,
                    message=f'New project assigned: {project_name}',
                    cur=cursor
                )

                conn.commit()
                flash('Project and Architect assigned successfully.')
            else:
                conn.rollback()
                flash('Site not found.', 'error')

            return redirect(url_for('assign_architect'))

        return render_template('assign_architect.html',
                               projects=projects,
                               architects=architects,
                               session=session)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Database error: {str(e)}', 'error')
        return render_template('assign_architect.html',
                               projects=[],
                               architects=[],
                               session=session)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/get_assigned_sites_by_architect')
def get_assigned_sites_by_architect():
    if 'role' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    architect_id = request.args.get('architect_id')
    org_id = session['org_id']
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT site_id FROM projects 
            WHERE architect_id = %s AND org_id = %s
        """, (architect_id, org_id))
        
        assigned = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    
    assigned_site_ids = [row['site_id'] for row in assigned]
    return jsonify({'status': 'success', 'assigned_site_ids': assigned_site_ids})        
    
########################################### Admin Assigned Sites ######################################    
@app.route('/admin/assigned_sites')
def admin_assigned_sites():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM sites WHERE site_engineer_id IS NOT NULL AND org_id = %s", (session['org_id'],))
        sites = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading assigned sites: {str(e)}", "danger")
        sites = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('admin_assigned_sites.html', sites=sites)

########################################### View Assigned Architects ######################################

@app.route('/view_assigned_architects')
def view_assigned_architects():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        if session['role'] == 'admin':
            cur.execute("""
                SELECT s.site_id, s.site_name, p.id AS project_id, r.name AS architect_name, r.email AS architect_email
                FROM sites s
                LEFT JOIN projects p ON s.site_id = p.site_id
                LEFT JOIN register r ON p.architect_id = r.id
                WHERE s.org_id = %s
            """, (session['org_id'],))
        else:
            site_engineer_id = session['user_id']
            cur.execute("""
                SELECT s.site_id, s.site_name, p.id AS project_id, r.name AS architect_name, r.email AS architect_email
                FROM sites s
                LEFT JOIN projects p ON s.site_id = p.site_id
                LEFT JOIN register r ON p.architect_id = r.id
                WHERE s.site_engineer_id = %s
            """, (site_engineer_id,))
        
        sites = cur.fetchall()
    except Exception as e:
        flash(f"Error loading assigned architects: {str(e)}", "danger")
        sites = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    sites = sorted(sites, key=lambda x: x.get('project_assigned_date') or '', reverse=True)
    
    # Create current_user object to pass to template
    current_user = {
        'role': session['role'],
        'user_id': session['user_id'],
        'name': session.get('name', ''),
        'email': session.get('email', '')
    }
    
    return render_template('view_assigned_architects.html', sites=sites, current_user=current_user)


################################################# View Project Details ######################################
@app.route('/view_project_details', methods=['GET', 'POST'])
def view_project_details():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']
    org_id = session.get('org_id')

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Get all project options for dropdown
        if role == 'admin':
            cursor.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
            project_list = cursor.fetchall()
        elif role == 'site_engineer':
            cursor.execute("""
                SELECT p.id, p.project_name
                FROM projects p
                JOIN sites s ON p.site_id = s.site_id
                WHERE s.site_engineer_id = %s AND s.org_id = %s
            """, (user_id, org_id))
            project_list = cursor.fetchall()
        else:
            project_list = []

        selected_project = None
        project_id = request.form.get('project_id')

        if request.method == 'POST' and project_id:
            # Validate if selected project belongs to org
            cursor.execute("SELECT * FROM projects WHERE id = %s AND org_id = %s", (project_id, org_id))
            selected_project = cursor.fetchone()

            if selected_project:
                cursor.execute("SELECT * FROM design_details WHERE project_id = %s", (project_id,))
                design = cursor.fetchone()

                cursor.execute("SELECT * FROM structural_details WHERE project_id = %s", (project_id,))
                structure = cursor.fetchone()

                cursor.execute("SELECT * FROM material_specifications WHERE project_id = %s", (project_id,))
                material = cursor.fetchone()

                cursor.execute("SELECT * FROM site_conditions WHERE project_id = %s", (project_id,))
                site_conditions = cursor.fetchone()

                cursor.execute("SELECT * FROM utilities_services WHERE project_id = %s", (project_id,))
                utilities = cursor.fetchone()

                cursor.execute("SELECT * FROM cost_estimation WHERE project_id = %s", (project_id,))
                cost = cursor.fetchone()

                cursor.execute("SELECT * FROM drawing_documents WHERE project_id = %s", (project_id,))
                drawings = cursor.fetchall()

                return render_template("view_project_details.html",
                                    project_list=project_list,
                                    selected_project=selected_project,
                                    design=design,
                                    structure=structure,
                                    material=material,
                                    site_conditions=site_conditions,
                                    utilities=utilities,
                                    cost=cost,
                                    drawings=drawings,
                                    selected_project_id=int(project_id))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("view_project_details.html", project_list=project_list)


########################################### Submit Legal Compliances ######################################
@app.route('/submit_legal_compliances', methods=['GET', 'POST'])
def submit_legal_compliances():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        if request.method == 'POST':
            project_id = request.form['project_id']
            municipal_status = request.form['municipal_approval_status']
            environmental_clearance = request.form['environmental_clearance']

            # Helper to save file
            def save_file(file):
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_folder = app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    return os.path.join('uploads', filename).replace("\\", "/")
                return None

            municipal_pdf = save_file(request.files.get('municipal_approval_pdf'))
            building_permit_pdf = save_file(request.files.get('building_permit_pdf'))
            sanction_plan_pdf = save_file(request.files.get('sanction_plan_pdf'))
            fire_noc_pdf = save_file(request.files.get('fire_department_noc_pdf'))
            mngl_pdf = save_file(request.files.get('mngl_pdf'))

            cur.execute("SELECT id FROM legal_and_compliances WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
            existing = cur.fetchone()

            if existing:
                # Get old values to keep if new files not provided
                cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
                old = cur.fetchone()
                municipal_pdf = municipal_pdf or old['municipal_approval_pdf']
                building_permit_pdf = building_permit_pdf or old['building_permit_pdf']
                sanction_plan_pdf = sanction_plan_pdf or old['sanction_plan_pdf']
                fire_noc_pdf = fire_noc_pdf or old['fire_department_noc_pdf']
                mngl_pdf = mngl_pdf or old['mngl_pdf']

                cur.execute("""
                    UPDATE legal_and_compliances
                    SET municipal_approval_status=%s,
                        municipal_approval_pdf=%s,
                        building_permit_pdf=%s,
                        sanction_plan_pdf=%s,
                        fire_department_noc_pdf=%s,
                        environmental_clearance=%s,
                        mngl_pdf=%s
                    WHERE project_id=%s AND org_id = %s
                """, (
                    municipal_status, municipal_pdf, building_permit_pdf,
                    sanction_plan_pdf, fire_noc_pdf, environmental_clearance,
                    mngl_pdf, project_id, session['org_id']
                ))
            else:
                cur.execute("""
                    INSERT INTO legal_and_compliances (
                        project_id, municipal_approval_status, municipal_approval_pdf,
                        building_permit_pdf, sanction_plan_pdf, fire_department_noc_pdf,
                        environmental_clearance, mngl_pdf, org_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    project_id, municipal_status, municipal_pdf,
                    building_permit_pdf, sanction_plan_pdf, fire_noc_pdf,
                    environmental_clearance, mngl_pdf, session['org_id']
                ))

            conn.commit()

            # ---------- Notifications (after commit) ----------
            org_id = session['org_id']
            cur.execute("SELECT project_name, architect_id, site_id FROM projects WHERE id = %s", (project_id,))
            project_data = cur.fetchone()
            if project_data:
                project_name = project_data['project_name']
                notification_message = f'Legal compliance documents updated for {project_name}'

                # Notify architect
                if project_data['architect_id']:
                    create_notification(
                        user_id=project_data['architect_id'],
                        org_id=org_id,
                        notification_type='legal_updated',
                        reference_id=project_id,
                        message=notification_message,
                        cur=cur
                    )

                # Notify accountants
                cur.execute("SELECT DISTINCT accountant_id FROM accountant_projects WHERE project_id = %s AND org_id = %s", (project_id, org_id))
                accountants = cur.fetchall()
                for acc in accountants:
                    create_notification(
                        user_id=acc['accountant_id'],
                        org_id=org_id,
                        notification_type='legal_updated',
                        reference_id=project_id,
                        message=notification_message,
                        cur=cur
                    )

                # Notify site engineers
                if project_data['site_id']:
                    cur.execute("SELECT site_engineer_id FROM sites WHERE site_id = %s", (project_data['site_id'],))
                    site_engineers = cur.fetchall()
                    for se in site_engineers:
                        if se['site_engineer_id'] != session.get('user_id'):
                            create_notification(
                                user_id=se['site_engineer_id'],
                                org_id=org_id,
                                notification_type='legal_updated',
                                reference_id=project_id,
                                message=notification_message,
                                cur=cur
                            )
                    conn.commit()
            # ------------------------------------------------

            flash('Legal compliances submitted successfully.', 'success')
            return redirect(url_for('submit_legal_compliances'))

        # GET method - fetch project list
        user_id = session.get('user_id')
        role = session.get('role')
        if role == 'admin':
            cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (session['org_id'],))
        else:  # site_engineer
            cur.execute("""
                SELECT p.id, p.project_name
                FROM projects p
                JOIN sites s ON p.site_id = s.site_id
                WHERE s.site_engineer_id = %s AND p.org_id = %s
            """, (user_id, session['org_id']))
        projects = cur.fetchall()
        return render_template('submit_legal_compliances.html', projects=projects)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('login'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

############################################ View Legal Compliances ######################################
@app.route('/view_legal_compliances')
def view_legal_compliances():
    if 'role' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']
    org_id = session['org_id']

    # Mark legal compliance notifications as read
    if role in ['architect', 'accountant', 'site_engineer']:
        mark_notifications_as_read(user_id, org_id, 'legal_updated')

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        if role == 'admin':
            cur.execute("""
                SELECT lc.*, p.project_name
                FROM legal_and_compliances lc
                JOIN projects p ON lc.project_id = p.id
                WHERE lc.org_id = %s
            """, (org_id,))
        elif role == 'site_engineer':
            cur.execute("""
                SELECT lc.*, p.project_name
                FROM legal_and_compliances lc
                JOIN projects p ON lc.project_id = p.id
                JOIN sites s ON p.site_id = s.site_id
                WHERE s.site_engineer_id = %s AND p.org_id = %s
            """, (user_id, org_id))
        else:
            # Unauthorized role
            return redirect(url_for('login'))

        compliances = cur.fetchall()
    except Exception as e:
        flash(f"Error loading legal compliances: {str(e)}", "danger")
        compliances = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('view_legal_compliances.html', compliances=compliances)


def save_file(file):
    if file and file.filename:
        filename = secure_filename(file.filename)
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        # Return the relative path for use in the database
        return os.path.join('uploads', filename).replace("\\", "/")
    return None

################################################ Legal Compliances Dashboard#########################################

@app.route('/api/get_projects_by_org', methods=['GET'])
def get_projects_by_org():
    if 'org_id' not in session or 'role' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = session['org_id']
    user_id = session.get('user_id')
    role = session.get('role')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        if role == 'admin':
            cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
            projects = cur.fetchall()

        elif role == 'site_engineer':
            cur.execute("""
                SELECT DISTINCT p.id, p.project_name
                FROM projects p
                JOIN sites s ON p.site_id = s.site_id
                WHERE s.site_engineer_id = %s AND p.org_id = %s
            """, (user_id, org_id))
            projects = cur.fetchall()

        elif role == 'architect':
            cur.execute("SELECT id FROM architects WHERE register_id = %s", (user_id,))
            architect = cur.fetchone()
            if not architect:
                return jsonify({'projects': []})
            cur.execute("""
                SELECT id, project_name
                FROM projects
                WHERE architect_id = %s AND org_id = %s
            """, (architect['id'], org_id))
            projects = cur.fetchall()

        elif role == 'accountant':
            cur.execute("""
                SELECT p.id, p.project_name
                FROM projects p
                JOIN accountant_projects ap ON p.id = ap.project_id
                WHERE ap.accountant_id = %s AND p.org_id = %s
            """, (user_id, org_id))
            projects = cur.fetchall()

        else:
            return jsonify({'error': 'Unauthorized role'}), 403

        return jsonify({'projects': projects}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/legal_compliances_dashboard', methods=['GET', 'POST'])
def legal_compliances_dashboard():

    # conn = get_connection()
    # cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        user_id = session.get('user_id')
        role = session.get('role')
        org_id = session.get('org_id')

        if role in ['architect', 'accountant', 'site_engineer']:
            mark_notifications_as_read(user_id, org_id, 'legal_updated')

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)    

        projects = []
        compliance_data = None
        selected_project = None
        not_approved = False

        if role == 'admin':
            cur.execute("""
                SELECT DISTINCT p.id, p.project_name 
                FROM projects p 
                JOIN legal_and_compliances l ON p.id = l.project_id
            """)
            projects = cur.fetchall()

        elif role == 'site_engineer':
            cur.execute("SELECT site_id FROM sites WHERE site_engineer_id = %s", (user_id))
            user_site_ids = [row['site_id'] for row in cur.fetchall()]
            if user_site_ids:
                format_strings = ','.join(['%s'] * len(user_site_ids))
                cur.execute(f"""
                    SELECT DISTINCT p.id, p.project_name, p.site_id
                    FROM projects p 
                    JOIN legal_and_compliances l ON p.id = l.project_id
                    WHERE p.site_id IN ({format_strings})
                """, user_site_ids)
                projects = cur.fetchall()

        elif role == 'architect':
            cur.execute("SELECT * FROM architects WHERE register_id = %s", (user_id,))
            architect = cur.fetchone()

            if not architect:
                cur.close()
                conn.close()
                flash("Architect profile not found.")
                return redirect(url_for('login'))

            cur.execute("""
                SELECT DISTINCT p.id, p.project_name
                FROM projects p
                JOIN legal_and_compliances l ON p.id = l.project_id
                WHERE p.architect_id = %s
            """, (architect['register_id'],))
            projects = cur.fetchall()

        elif role == 'accountant':
            cur.execute("""
                SELECT DISTINCT p.id, p.project_name
                FROM projects p
                JOIN accountant_projects ap ON p.id = ap.project_id
                WHERE ap.accountant_id = %s
            """, (user_id,))
            projects = cur.fetchall()

        else:
            flash("Unauthorized access.")
            return redirect(url_for('login'))

        # 🔽 POST: View selected project details
        if request.method == 'POST':
            selected_project_id = request.form['project_id']

            if role == 'site_engineer':
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM projects p 
                    JOIN sites s ON p.site_id = s.site_id
                    WHERE p.id = %s AND s.site_engineer_id = %s
                """, (selected_project_id, user_id))
                if cur.fetchone()['count'] == 0:
                    flash("Access denied to this project.")
                    return redirect(url_for('legal_compliances_dashboard'))

            if role == 'architect':
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM projects
                    WHERE id = %s AND architect_id = %s
                """, (selected_project_id, user_id))  # user_id is register_id
                if cur.fetchone()['count'] == 0:
                    flash("Access denied to this project.")
                    return redirect(url_for('legal_compliances_dashboard'))

            if role == 'accountant':
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM accountant_projects
                    WHERE project_id = %s AND accountant_id = %s
                """, (selected_project_id, user_id))
                if cur.fetchone()['count'] == 0:
                    flash("Access denied to this project.")
                    return redirect(url_for('legal_compliances_dashboard'))

            cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s", (selected_project_id,))
            compliance_data = cur.fetchone()

            if compliance_data and compliance_data['municipal_approval_status'] != 'Approved':
                not_approved = True
                compliance_data = None

            cur.execute("SELECT * FROM projects WHERE id = %s", (selected_project_id,))
            selected_project = cur.fetchone()

        return render_template(
            'legal_compliances_dashboard.html',
            projects=projects,
            compliance=compliance_data,
            selected_project=selected_project,
            not_approved=not_approved
        )
    except Exception as e:
        return{
            'status':'fail',
            'message':str(e)
        }
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


## ###############################--- Generate Invoice --- #######################################
@app.route('/engineer/generate_invoice', methods=['GET', 'POST'])
def generate_invoice():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch organization details (same as before)
    org_id = session.get('org_id')
    cur.execute("""
        SELECT company_name, company_address, company_phone, company_email,
               gst_number, bank_name, bank_account, ifsc_code, terms_conditions
        FROM organization_master 
        WHERE org_id = %s
    """, (org_id,))
    org_details = cur.fetchone()
    
    if not org_details:
        flash('Organization details not found', 'danger')
        return redirect(url_for('site_engineer_dashboard'))

    # Fetch projects assigned to this engineer
    site_engineer_id = session['user_id']
    cur.execute("""
        SELECT p.id, p.project_name
        FROM projects p
        JOIN sites s ON p.site_id = s.site_id
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (site_engineer_id, org_id))
    projects = cur.fetchall()

    if request.method == 'POST':
        try:
            project_id = request.form.get('project_id')
            if not project_id:
                flash("Please select a project before generating an invoice.", "danger")
                return redirect(request.url)

            vendor_name = request.form.get('vendor_name')
            client_name = request.form.get('bill_to_name')
            client_address = request.form.get('bill_to_address') or ""
            client_phone = request.form.get('bill_to_phone') or ""
            subtotal = float(request.form.get('subtotal', 0))
            total_amount = float(request.form.get('total_amount', 0))
            invoice_date = datetime.now().strftime("%Y-%m-%d")

            gst_percentage = float(request.form.get('gst_percentage', 0))
            gst_amount = subtotal * gst_percentage / 100
            grand_total = total_amount

            invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
            # No pdf_filename yet – will be set by background task
            pdf_filename = None

            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            totals = request.form.getlist('total[]')

            # Handle image upload (optional)
            invoice_image_filename = None
            if 'invoice_image' in request.files:
                file = request.files['invoice_image']
                if file and file.filename and file.filename != '':
                    allowed_extensions = {'.png', '.jpg', '.jpeg'}
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext in allowed_extensions:
                        try:
                            safe_name = secure_filename(file.filename)
                            unique_name = f"{invoice_number}_{safe_name}"
                            invoice_images_dir = os.path.join(app.static_folder, 'invoice_images')
                            os.makedirs(invoice_images_dir, exist_ok=True)
                            file_path = os.path.join(invoice_images_dir, unique_name)
                            file.save(file_path)
                            invoice_image_filename = unique_name
                        except Exception as e:
                            flash(f"Error saving image: {str(e)}", "error")
                            return redirect(request.url)
                    else:
                        flash("Please upload a valid image file (PNG, JPEG, JPG)", "error")
                        return redirect(request.url)

            # Insert invoice (without PDF)
            cur.execute("""
                INSERT INTO invoices (
                    project_id, site_engineer_id, vendor_name, total_amount,
                    gst_amount, invoice_number, pdf_filename, generated_on,
                    bill_to_name, bill_to_address, bill_to_phone, subtotal,
                    invoice_image_filename, org_id, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
            """, (
                project_id, site_engineer_id, vendor_name, grand_total,
                gst_amount, invoice_number, pdf_filename, invoice_date,
                client_name, client_address, client_phone, subtotal,
                invoice_image_filename, org_id
            ))
            invoice_id = cur.lastrowid

            # Insert invoice items
            for desc, qty, rate, line_total in zip(descriptions, quantities, rates, totals):
                if desc and qty and rate:
                    cur.execute("""
                        INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal, org_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (invoice_id, desc.strip(), float(qty), float(rate), float(line_total), org_id))

            conn.commit()

            # Notify admins about pending invoice (same as before)
            cur.execute("SELECT id FROM register WHERE role = 'admin' AND org_id = %s", (org_id,))
            admin_list = cur.fetchall()
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            proj = cur.fetchone()
            proj_name = proj['project_name'] if proj else 'Unknown Project'
            for admin in admin_list:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='invoice_pending',
                    reference_id=invoice_id,
                    message=f'New invoice {invoice_number} submitted for {proj_name} by {session.get("name")} — ₹{grand_total:,.2f}',
                    cur=cur    # <-- add this
                )
            conn.commit()  

            # 🔥 START BACKGROUND PDF GENERATION
            thread = threading.Thread(
                target=generate_invoice_pdf_async,
                args=(invoice_id, org_id, invoice_number, proj_name, grand_total, session.get('name'))
            )
            thread.daemon = True
            thread.start()

            flash(f'Invoice #{invoice_number} created. PDF is being generated in the background. You will be notified when ready.', 'success')
            return redirect(url_for('site_engineer_invoices'))

        except Exception as e:
            conn.rollback()
            flash(f"Error generating invoice: {str(e)}", "danger")
            return redirect(request.url)
        finally:
            cur.close()
            conn.close()

    # GET request – show form
    cur.close()
    conn.close()
    return render_template('generate_invoice.html', 
                         projects=projects, 
                         current_date=datetime.now().strftime("%Y-%m-%d"), 
                         user_role='site_engineer')

@app.route('/api/invoice_pdf_status/<int:invoice_id>')
def api_invoice_pdf_status(invoice_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM invoices WHERE id = %s AND org_id = %s", (invoice_id, session['org_id']))
        inv = cur.fetchone()
        if inv and inv['pdf_filename']:
            return jsonify({'status': 'ready'})
        else:
            # Optionally check if the invoice exists and is not failed
            return jsonify({'status': 'processing'})
    finally:
        cur.close()
        conn.close()

@app.route('/download_invoice_pdf/<int:invoice_id>')
def download_invoice_pdf(invoice_id):
    if 'user_id' not in session:
        abort(401)
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM invoices WHERE id = %s AND org_id = %s", (invoice_id, session['org_id']))
        inv = cur.fetchone()
        if inv and inv['pdf_filename']:
            pdf_path = os.path.join(app.static_folder, 'invoice_pdfs', inv['pdf_filename'])
            if os.path.exists(pdf_path):
                return send_file(pdf_path, as_attachment=True, download_name=inv['pdf_filename'])
            else:
                flash('PDF file not found. It may still be generating.', 'warning')
        else:
            flash('PDF not ready yet. Please try again later.', 'warning')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('site_engineer_invoices'))


###################################################### Invoice Submission Route ##########################
@app.route('/submit_invoice_alt', methods=['GET', 'POST'])
def submit_invoice_alt():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
    vendor_name = request.form.get('vendor_name')
    item_names = request.form.getlist('item_name')
    quantities = request.form.getlist('quantity')
    rates = request.form.getlist('rate')

    subtotal = 0
    items = []
    for name, qty, rate in zip(item_names, quantities, rates):
        qty = int(qty)
        rate = float(rate)
        amount = qty * rate
        subtotal += amount
        items.append((name, qty, rate, amount))

    gst_amount = round(subtotal * 0.18, 2)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO invoices (site_engineer_id, vendor_name, total_amount, gst_amount)
            VALUES (%s, %s, %s, %s)
        """, (site_engineer_id, vendor_name, subtotal, gst_amount))
        invoice_id = cursor.lastrowid
        for name, qty, rate, amount in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (invoice_id, name, qty, rate, amount))
        conn.commit()
        flash("Invoice submitted successfully.", "success")
        return redirect(url_for('site_engineer_dashboard'))
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
        return redirect(request.url)
    finally:
        cursor.close()
        conn.close()
    

###################################################### Admin View Invoices Route ##########################@app.route('/admin/invoices', methods=['GET', 'POST'])
@app.route('/admin/invoices', methods=['GET', 'POST'])
def admin_view_invoices():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    status_filter = request.args.get('status', 'All')
    admin_id = session.get('user_id')
    org_id = session.get('org_id')

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if request.method == 'POST':
            invoice_id = request.form.get('invoice_id')
            action = request.form.get('action')
            rejection_reason = request.form.get('rejection_reason', '')

            if action == 'approve':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Approved', approved_by=%s, approved_on=NOW(), rejection_reason=NULL 
                    WHERE id=%s AND org_id = %s
                """, (admin_id, invoice_id, org_id))
                conn.commit()
                flash("Invoice approved.", "success")

                cursor.execute("""
                    SELECT i.invoice_number, i.total_amount, i.site_engineer_id, i.project_id
                    FROM invoices i WHERE i.id = %s AND i.org_id = %s
                """, (invoice_id, org_id))
                inv = cursor.fetchone()
                if inv:
                    create_notification(
                        user_id=inv['site_engineer_id'],
                        org_id=org_id,
                        notification_type='invoice_approved',
                        reference_id=invoice_id,
                        message=f'Your invoice {inv["invoice_number"]} (₹{inv["total_amount"]:,.2f}) has been approved',
                        cur=cursor
                    )

                    cursor.execute("""
                        SELECT DISTINCT accountant_id FROM accountant_projects 
                        WHERE project_id = %s AND org_id = %s
                    """, (inv['project_id'], org_id))
                    accountants = cursor.fetchall()
                    for acc in accountants:
                        create_notification(
                            user_id=acc['accountant_id'],
                            org_id=org_id,
                            notification_type='invoice_approved',
                            reference_id=invoice_id,
                            message=f'Invoice {inv["invoice_number"]} approved for project — ₹{inv["total_amount"]:,.2f}',
                            cur=cursor
                        )
                    conn.commit()

            elif action == 'reject':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Rejected', rejection_reason=%s, approved_by=%s, approved_on=NOW() 
                    WHERE id=%s AND org_id = %s
                """, (rejection_reason, admin_id, invoice_id, org_id))
                conn.commit()
                flash("Invoice rejected.", "danger")
                
                cursor.execute("""
                    SELECT invoice_number, total_amount, site_engineer_id
                    FROM invoices WHERE id = %s AND org_id = %s
                """, (invoice_id, org_id))
                inv = cursor.fetchone()
                if inv:
                    reason_text = f' Reason: {rejection_reason}' if rejection_reason else ''
                    create_notification(
                        user_id=inv['site_engineer_id'],
                        org_id=org_id,
                        notification_type='invoice_rejected',
                        reference_id=invoice_id,
                        message=f'Your invoice {inv["invoice_number"]} (₹{inv["total_amount"]:,.2f}) has been rejected.{reason_text}',
                        cur=cursor
                    )
                conn.commit()

            elif action == 'edit':
                return redirect(url_for('admin_edit_invoice', invoice_id=invoice_id))

        # GET request - fetch invoices
        if status_filter in ['Pending', 'Approved', 'Rejected']:
            cursor.execute("""
                SELECT i.*, r.name as engineer_name 
                FROM invoices i 
                LEFT JOIN register r ON i.site_engineer_id = r.id 
                WHERE i.status = %s AND i.org_id = %s
                ORDER BY i.generated_on DESC
            """, (status_filter, org_id))
        else:
            cursor.execute("""
                SELECT i.*, r.name as engineer_name 
                FROM invoices i 
                LEFT JOIN register r ON i.site_engineer_id = r.id 
                WHERE i.org_id = %s
                ORDER BY i.generated_on DESC
            """, (org_id,))
        invoices = cursor.fetchall()

        cursor.execute("""
            SELECT * FROM invoice_items 
            WHERE org_id = %s 
            ORDER BY invoice_id
        """, (org_id,))
        all_items = cursor.fetchall()

    except Exception as e:
        flash(f"Error loading invoices: {str(e)}", "danger")
        invoices = []
        all_items = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Group items by invoice ID
    items_by_invoice = {}
    for item in all_items:
        items_by_invoice.setdefault(item['invoice_id'], []).append(item)

    return render_template(
        'invoice_detail.html',
        invoices=invoices,
        items_by_invoice=items_by_invoice,
        selected_status=status_filter
    )

#################################### Admin Invoice Detail View ######################################
@app.route('/admin/invoice/<int:invoice_id>')
def admin_invoice_detail(invoice_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM invoices WHERE id=%s and org_id = %s", (invoice_id, session['org_id']))
        invoice = cursor.fetchone()
        if not invoice:
            flash("Invoice not found.", "danger")
            return redirect(url_for('admin_view_invoices'))
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=%s and org_id = %s", (invoice_id, session['org_id']))
        items = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading invoice details: {str(e)}", "danger")
        invoice = None
        items = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('invoice_detail.html', invoice=invoice, items=items)
################################## Site Engineer Generate Invoice ######################################
# @app.route('/site_engineer/invoice/new', methods=['GET', 'POST'])
# def site_engineer_generate_invoice():
#     if session.get('role') != 'site_engineer':
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         try:
#             site_engineer_id = session.get('user_id')
#             vendor_name = request.form['vendor_name']
#             # Always use current date for invoice_date
#             invoice_date = datetime.now().strftime("%Y-%m-%d")
#             bill_to_name = request.form['bill_to_name']
#             bill_to_address = request.form['bill_to_address']
#             bill_to_phone = request.form['bill_to_phone']
#             subtotal = float(request.form['subtotal'])
#             total_amount = float(request.form['total_amount'])  # This is grand total from form

#             apply_gst = request.form.get('apply_gst')
#             gst_percentage = 18
#             gst_amount = 0
#             if apply_gst:
#                 gst_amount = subtotal * gst_percentage / 100
#             else:
#                 gst_amount = 0

#             descriptions = request.form.getlist('description[]')
#             quantities = request.form.getlist('quantity[]')
#             item_prices = request.form.getlist('rate[]')
#             totals = request.form.getlist('total[]')

#             invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
#             pdf_filename = f"invoice_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

#             with db.cursor() as cursor:
#                 cursor.execute("""
#                     INSERT INTO invoices (
#                         site_engineer_id, vendor_name, total_amount, gst_amount, pdf_filename, generated_on,
#                         bill_to_name, bill_to_address, bill_to_phone, subtotal, invoice_number
#                     )
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#                 """, (
#                     site_engineer_id, vendor_name, total_amount, gst_amount, pdf_filename, invoice_date,
#                     bill_to_name, bill_to_address, bill_to_phone, subtotal, invoice_number
#                 ))

#                 invoice_id = cursor.lastrowid

#                 items_inserted = 0
#                 for i, (desc, qty, price, total) in enumerate(zip(descriptions, quantities, item_prices, totals)):
#                     if not desc.strip():
#                         continue
#                     try:
#                         qty_val = float(qty) if qty else 0
#                         price_val = float(price) if price else 0
#                         total_val = float(total) if total else (qty_val * price_val)
#                         cursor.execute("""
#                             INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
#                             VALUES (%s, %s, %s, %s, %s)
#                         """, (invoice_id, desc.strip(), qty_val, price_val, total_val))
#                         items_inserted += 1
#                     except (ValueError, TypeError):
#                         continue

#                 if items_inserted == 0:
#                     raise Exception("No valid items were inserted")

#                 db.commit()

#             flash(f"Invoice generated successfully! ({items_inserted} items added)", "success")
#             return redirect(url_for('site_engineer_invoices'))

#         except Exception as e:
#             db.rollback()
#             flash(f"Error: {str(e)}", "danger")

#     # Pass current date to template for display
#     return render_template('generate_invoice.html', current_date=datetime.now().strftime("%Y-%m-%d"), user_role='site_engineer')


####################################################### Submit Invoice Route for Site Engineer ##########################################

@app.route('/submit_invoice', methods=['GET', 'POST'])
def submit_invoice():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
    vendor_name = request.form.get('vendor_name')
    item_names = request.form.getlist('item_name[]')
    quantities = request.form.getlist('quantity[]')
    rates = request.form.getlist('rate[]')

    subtotal = 0
    items = []
    for name, qty, rate in zip(item_names, quantities, rates):
        qty = int(qty)
        rate = float(rate)
        amount = qty * rate
        subtotal += amount
        items.append((name, qty, rate, amount))

    gst_amount = round(subtotal * 0.18, 2)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO invoices (site_engineer_id, vendor_name, total_amount, gst_amount)
            VALUES (%s, %s, %s, %s)
        """, (site_engineer_id, vendor_name, subtotal, gst_amount))
        invoice_id = cursor.lastrowid
        for name, qty, rate, amount in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (invoice_id, name, qty, rate, amount))
        conn.commit()
        flash("Invoice submitted successfully.", "success")
        return redirect(url_for('site_engineer_dashboard'))
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
        return redirect(request.url)
    finally:
        cursor.close()
        conn.close()
    
######################################### Serve Invoice PDF ########################################    
@app.route('/uploads/invoices/<path:filename>')

def serve_invoice_pdf(filename):

    # Allow admin, accountant, site_engineer, architect

    if session.get('role') not in ['admin', 'accountant', 'site_engineer', 'architect']:

        flash("Unauthorized access", "danger")

        return redirect(url_for('login'))

    return send_from_directory('static/invoices', filename)
@app.route('/dashboard')
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'site_engineer':
        return redirect(url_for('site_engineer_dashboard'))
    elif role == 'architect':
        return redirect(url_for('architect_dashboard'))
    elif role == 'accountant':
        return redirect(url_for('accountant_dashboard'))
    else:
        return redirect(url_for('login'))
    from datetime import datetime, date

@app.route('/admin/generate_invoice', methods=['GET', 'POST'])
def admin_generate_invoice():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Fetch site engineers
        cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer' AND org_id = %s", (session['org_id'],))
        engineers = cursor.fetchall()

        # Fetch distinct projects
        cursor.execute("""
            SELECT MIN(id) as id, project_name 
            FROM projects 
            WHERE org_id = %s 
            GROUP BY project_name 
            ORDER BY project_name
        """, (session['org_id'],))
        projects = cursor.fetchall()

        # Fetch organization details (for form display only)
        cursor.execute("""
            SELECT company_name, company_address, company_phone, company_email,
                   gst_number, bank_name, bank_account, ifsc_code, terms_conditions
            FROM organization_master 
            WHERE org_id = %s
        """, (session['org_id'],))
        org_details = cursor.fetchone()

        if not org_details:
            flash('Organization details not found.', 'danger')
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            try:
                project_id = request.form.get('project_id')
                site_engineer_id = request.form.get('site_engineer_id')
                vendor_name = request.form.get('vendor_name')
                client_name = request.form.get('bill_to_name')
                client_address = request.form.get('bill_to_address') or ""
                client_phone = request.form.get('bill_to_phone') or ""
                total_amount = float(request.form.get('total_amount') or 0)
                invoice_date = request.form.get('invoice_date')
                admin_id = session.get('user_id')
                org_id = session['org_id']

                grand_total = total_amount
                subtotal_raw = request.form.get('subtotal', 0)
                subtotal = float(subtotal_raw) if subtotal_raw else 0.0
                gst_percentage = float(request.form.get('gst_percentage', 0))
                gst_amount = subtotal * gst_percentage / 100

                invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
                pdf_filename = None  # Will be set by background task

                descriptions = request.form.getlist('description[]')
                quantities = request.form.getlist('quantity[]')
                rates = request.form.getlist('rate[]')
                totals = request.form.getlist('total[]')

                # Handle invoice image upload (optional)
                image_filename = None
                if 'invoice_image' in request.files:
                    image_file = request.files['invoice_image']
                    if image_file and image_file.filename != '':
                        image_directory = os.path.join('static', 'invoice_images')
                        if not os.path.exists(image_directory):
                            os.makedirs(image_directory)
                        file_extension = os.path.splitext(image_file.filename)[1].lower()
                        image_filename = f"invoice_img_{invoice_number}{file_extension}"
                        image_path = os.path.join(image_directory, image_filename)
                        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.jfif', '.heic'}
                        if file_extension not in allowed_extensions:
                            raise Exception("Invalid file type. Only PNG, JPG, and JPEG files are allowed.")
                        image_file.seek(0, 2)
                        file_size = image_file.tell()
                        image_file.seek(0)
                        if file_size > 5 * 1024 * 1024:
                            raise Exception("File size too large. Maximum size is 5MB.")
                        image_file.save(image_path)

                # 🔥 FIX: Insert subtotal as well
                cursor.execute("""
                    INSERT INTO invoices (
                        project_id, site_engineer_id, vendor_name, total_amount, gst_amount, subtotal,
                        invoice_number, pdf_filename, generated_on,
                        bill_to_name, bill_to_address, bill_to_phone, status, approved_by, approved_on,
                        invoice_image_filename, org_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Approved', %s, NOW(), %s, %s)
                """, (
                    project_id, site_engineer_id, vendor_name, grand_total, gst_amount, subtotal,
                    invoice_number, pdf_filename, invoice_date,
                    client_name, client_address, client_phone, admin_id, image_filename, org_id
                ))
                invoice_id = cursor.lastrowid

                # Insert invoice items
                items_inserted = 0
                for desc, qty, rate, subtotal_item in zip(descriptions, quantities, rates, totals):
                    if desc and qty and rate:
                        cursor.execute("""
                            INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal, org_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (invoice_id, desc.strip(), float(qty), float(rate), float(subtotal_item), org_id))
                        items_inserted += 1

                if items_inserted == 0:
                    raise Exception("No valid invoice items found")

                conn.commit()

                # Notifications (unchanged)
                cursor.execute("""
                    SELECT p.project_name, r.name as engineer_name
                    FROM projects p
                    LEFT JOIN register r ON %s = r.id
                    WHERE p.id = %s
                """, (site_engineer_id, project_id))
                project_data = cursor.fetchone()
                project_name = project_data['project_name'] if project_data else 'Unknown Project'

                if site_engineer_id:
                    create_notification(
                        user_id=site_engineer_id,
                        org_id=org_id,
                        notification_type='invoice_approved',
                        reference_id=invoice_id,
                        message=f'Invoice {invoice_number} generated for {project_name} — ₹{grand_total:,.2f}',
                        cur=cursor 
                    )

                cursor.execute("""
                    SELECT DISTINCT accountant_id 
                    FROM accountant_projects 
                    WHERE project_id = %s AND org_id = %s
                """, (project_id, org_id))
                accountants = cursor.fetchall()
                for acc in accountants:
                    create_notification(
                        user_id=acc['accountant_id'],
                        org_id=org_id,
                        notification_type='invoice_approved',
                        reference_id=invoice_id,
                        message=f'Invoice {invoice_number} approved for {project_name} — ₹{grand_total:,.2f}',
                        cur=cursor
                    )
                conn.commit()

                # Start background PDF generation (reuse existing function)
                thread = threading.Thread(
                    target=generate_invoice_pdf_async,
                    args=(invoice_id, org_id, invoice_number, project_name, grand_total, session.get('name'))
                )
                thread.daemon = True
                thread.start()

                flash(f'Admin invoice #{invoice_number} generated. PDF is being generated in the background.', 'success')
                return redirect(url_for('admin_view_invoices'))

            except Exception as e:
                conn.rollback()
                flash(f"Error generating invoice: {str(e)}", "danger")
                return redirect(request.url)

        # GET request
        return render_template('generate_invoice.html', 
                               engineers=engineers, 
                               projects=projects, 
                               user_role='admin', 
                               current_date=date.today().isoformat())

    except Exception as e:
        flash(f"Error loading form: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/get_engineer_projects/<int:engineer_id>')
def get_engineer_projects(engineer_id):
    """Get projects assigned to a specific site engineer"""
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get projects where this site engineer is assigned via sites table
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND s.org_id = %s
            ORDER BY p.project_name
        """, (engineer_id, org_id))
        
        projects = cur.fetchall()
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cur.close()
        conn.close()

@app.route('/site_engineer/invoices')
def site_engineer_invoices():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
    org_id = session['org_id']

    # Mark notification types as read
    mark_notifications_as_read(site_engineer_id, org_id, 'invoice_rejected')
    mark_notifications_as_read(site_engineer_id, org_id, 'invoice_approved')

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Single query: invoices + their items via LEFT JOIN
        cursor.execute("""
            SELECT
                i.id, i.invoice_number, i.generated_on, i.total_amount,
                i.status, i.rejection_reason, i.pdf_filename,
                it.id AS item_id, it.description, it.quantity, it.rate, it.subtotal
            FROM invoices i
            LEFT JOIN invoice_items it ON i.id = it.invoice_id AND it.org_id = i.org_id
            WHERE i.site_engineer_id = %s AND i.org_id = %s
            ORDER BY i.generated_on DESC, it.id
        """, (site_engineer_id, org_id))

        rows = cursor.fetchall()

        # Group items by invoice_id
        invoices_dict = {}
        for row in rows:
            inv_id = row['id']
            if inv_id not in invoices_dict:
                # FIX: Keep generated_on as a datetime object (not converted to string).
                # The template calls {{ invoice.generated_on.strftime('%Y-%m-%d') }}
                # which requires a datetime object, NOT a string.
                invoices_dict[inv_id] = {
                    'id': inv_id,
                    'invoice_number': row['invoice_number'],
                    'generated_on': row['generated_on'],   # <-- datetime object kept as-is
                    'total_amount': float(row['total_amount']),
                    'status': row['status'],
                    'rejection_reason': row['rejection_reason'],
                    'pdf_filename': row['pdf_filename'],
                    'items': []
                }
            # Add item if present (LEFT JOIN may give NULL item_id)
            if row['item_id']:
                invoices_dict[inv_id]['items'].append({
                    'description': row['description'],
                    'quantity': float(row['quantity']),
                    'rate': float(row['rate']),
                    'subtotal': float(row['subtotal'])
                })

        invoices = list(invoices_dict.values())

    except Exception as e:
        flash(f"Error loading invoices: {str(e)}", "danger")
        invoices = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('site_engineer_invoices.html', invoices=invoices)

# @app.route('/admin/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
# def admin_edit_invoice(invoice_id):
#     if session.get('role') != 'admin':
#         return redirect(url_for('login'))

#     with db.cursor(pymysql.cursors.DictCursor) as cursor:
#         cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
#         invoice = cursor.fetchone()

#         if not invoice:
#             flash("Invoice not found.", "danger")
#             return redirect(url_for('admin_view_invoices'))

#         cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
#         items = cursor.fetchall()

#         if request.method == 'POST':
#             vendor_name = request.form.get('vendor_name')
#             total_amount = request.form.get('total_amount')
#             gst_amount = request.form.get('gst_amount')
#             pdf_filename = request.form.get('pdf_filename')

#             cursor.execute("""
#                 UPDATE invoices 
#                 SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
#                     status='Pending', rejection_reason=NULL
#                 WHERE id=%s
#             """, (vendor_name, total_amount, gst_amount, pdf_filename, invoice_id))
#             db.commit()

#             flash("Invoice updated and reset to Pending for review.", "success")
#             return redirect(url_for('admin_view_invoices'))

#     return render_template('admin_edit_invoice.html', invoice=invoice, items=items)

@app.route('/admin/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def admin_edit_invoice(invoice_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Get invoice
        cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            flash("Invoice not found.", "danger")
            return redirect(url_for('admin_view_invoices'))
         
        # Get invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
        items = cursor.fetchall()
         
        if request.method == 'POST':
            vendor_name = request.form.get('vendor_name')
            total_amount = float(request.form.get('total_amount'))
            gst_amount = float(request.form.get('gst_amount'))
             
            # Generate PDF using ReportLab
            new_pdf_filename = f"invoice_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("static", "invoices", new_pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
             
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            y = height - 50
            c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
            y -= 30
            c.drawString(50, y, f"Vendor Name: {vendor_name}")
            y -= 30
            c.drawString(50, y, f"Total Amount: ₹{total_amount:.2f}")
            y -= 30
            c.drawString(50, y, f"GST Amount: ₹{gst_amount:.2f}")
            y -= 50
            c.drawString(50, y, "Items:")
            y -= 30
            for item in items:
                line = f"{item['description']} - Qty: {item['quantity']} x ₹{item['rate']} = ₹{item['subtotal']}"
                c.drawString(70, y, line)
                y -= 25
            c.save()
             
            # Store only filename (not full path) in DB
            cursor.execute("""
                UPDATE invoices 
                SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
                    status='Pending', rejection_reason=NULL
                WHERE id=%s
            """, (vendor_name, total_amount, gst_amount, new_pdf_filename, invoice_id))
            conn.commit()
             
            flash("Invoice updated. New PDF generated. Status reset to Pending.", "success")
            return redirect(url_for('admin_view_invoices'))
         
        return render_template('admin_edit_invoice.html', invoice=invoice, items=items)
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin_view_invoices'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    
    engineer_id = session.get('user_id')
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Verify the invoice belongs to this engineer
        cursor.execute("""
            SELECT * FROM invoices 
            WHERE id = %s AND site_engineer_id = %s AND status = 'Rejected' AND org_id = %s
        """, (invoice_id, engineer_id, session['org_id']))
        invoice = cursor.fetchone()
        
        if not invoice:
            flash("Invoice not found or not eligible for update.", "danger")
            return redirect(url_for('site_engineer_invoices'))
        
        # Get invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s and org_id = %s", (invoice_id, session['org_id']))
        items = cursor.fetchall()
        
        if request.method == 'POST':
            vendor_name = request.form.get('vendor_name')
            total_amount = float(request.form.get('total_amount'))
            gst_amount = float(request.form.get('gst_amount'))
            
            # Generate new PDF
            new_pdf_filename = f"invoice_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("static", "invoice_pdfs", new_pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            y = height - 50
            c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
            y -= 30
            c.drawString(50, y, f"Vendor Name: {vendor_name}")
            y -= 30
            c.drawString(50, y, f"Total Amount: ₹{total_amount:.2f}")
            y -= 30
            c.drawString(50, y, f"GST Amount: ₹{gst_amount:.2f}")
            y -= 50
            c.drawString(50, y, "Items:")
            y -= 30
            for item in items:
                line = f"{item['description']} - Qty: {item['quantity']} x ₹{item['rate']} = ₹{item['subtotal']}"
                c.drawString(70, y, line)
                y -= 25
            c.save()
            
            # Update invoice with new details and reset status
            cursor.execute("""
                UPDATE invoices 
                SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
                    status='Pending', rejection_reason=NULL
                WHERE id=%s
            """, (vendor_name, total_amount, gst_amount, new_pdf_filename, invoice_id))
            conn.commit()
            
            flash("Invoice updated and resubmitted for approval.", "success")
            return redirect(url_for('site_engineer_invoices'))
        
        return render_template('edit_invoice.html', invoice=invoice, items=items)
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('site_engineer_invoices'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
@app.route('/admin/assign_accountant', methods=['GET', 'POST'])
def assign_accountant():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    org_id = session.get('org_id')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        accountant_id = request.form['accountant_id']
        project_ids = request.form.getlist('project_ids')

        try:
            # ✅ INSERT IGNORE prevents duplicate rows without deleting existing assignments
            for project_id in project_ids:
                cur.execute(
                    """INSERT IGNORE INTO accountant_projects (accountant_id, project_id, org_id) 
                       VALUES (%s, %s, %s)""",
                    (accountant_id, project_id, org_id)
                )

            project_count = len(project_ids)
            create_notification(
                user_id=accountant_id,
                org_id=org_id,
                notification_type='project_assigned',
                reference_id=int(accountant_id),
                message=f'{project_count} project(s) assigned to you',
                cur=cur
            )

            conn.commit()
            flash('Projects assigned successfully.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error assigning projects: {str(e)}', 'danger')

    # Fetch all accountants belonging to this org
    cur.execute("SELECT id, name FROM register WHERE role = 'accountant' AND org_id = %s", (org_id,))
    accountants = cur.fetchall()

    # Fetch all projects belonging to this org
    cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
    projects = cur.fetchall()

    # Get current assignments to check the boxes in the template
    assignments = {}
    if accountants:
        cur.execute("SELECT accountant_id, project_id FROM accountant_projects WHERE org_id = %s", (org_id,))
        all_assignments = cur.fetchall()
        for a in all_assignments:
            if a['accountant_id'] not in assignments:
                assignments[a['accountant_id']] = []
            assignments[a['accountant_id']].append(a['project_id'])

    cur.close()
    conn.close()

    selected_accountant_id = request.args.get('accountant_id', '')
    return render_template(
        'assign_accountant.html',
        accountants=accountants,
        projects=projects,
        assignments=assignments,
        selected_accountant_id=selected_accountant_id
    )
@app.route('/')
def landing(): 
  return render_template('landing_page.html')

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import json
from datetime import datetime, date

def default_json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

@app.route('/communication')
def communication():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # user_id = session['user_id']
    # org_id = session['org_id']
    # mark_notifications_as_read(user_id, org_id, 'communication_message')
    
    return render_template('communication.html')

@app.route('/get_current_user_role')
def get_current_user_role():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT role FROM register WHERE id = %s and org_id = %s", (session['user_id'], session['org_id']))
        result = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    
    if result:
        return jsonify({'role': result['role']})
    return jsonify({'error': 'User not found'})

@app.route('/get_users')
def get_users():
    if 'user_id' not in session:
        return jsonify([])

    current_user_id = session['user_id']
    org_id = session.get('org_id')

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get current user's role
    try:
        cursor.execute("SELECT role FROM register WHERE id = %s AND org_id = %s", (current_user_id, org_id))
        result = cursor.fetchone()
    
        if not result:
            return jsonify([])
        current_user_role = result['role']

        # Get users
        if current_user_role == 'admin':
            cursor.execute("""
                SELECT r.id, r.name, r.role,
                    (SELECT COUNT(*) FROM messages 
                        WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
                FROM register r
                WHERE r.id != %s AND r.role != 'super_admin' AND r.org_id = %s
                ORDER BY r.name
            """, (current_user_id, current_user_id, org_id))
        elif current_user_role == 'accountant':
            cursor.execute("""
                SELECT r.id, r.name, r.role,
                    (SELECT COUNT(*) FROM messages 
                        WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
                FROM register r
                WHERE r.role = 'admin' AND r.id != %s AND r.org_id = %s
                ORDER BY r.name
            """, (current_user_id, current_user_id, org_id))
        else:
            cursor.execute("""
                SELECT r.id, r.name, r.role,
                    (SELECT COUNT(*) FROM messages 
                        WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
                FROM register r
                WHERE (
                    r.role = %s OR r.role = 'admin' OR 
                    (r.role = 'site_engineer' AND %s = 'architect') OR
                    (r.role = 'architect' AND %s = 'site_engineer')
                )
                AND r.id != %s AND r.role != 'super_admin' AND r.org_id = %s
                ORDER BY r.name
            """, (
                current_user_id,
                current_user_role,
                current_user_role,
                current_user_role,
                current_user_id,
                org_id
            ))

        users = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Rename site_engineer to project_manager
    for user in users:
        if user['role'] == 'site_engineer':
            user['role'] = 'project_manager'

    return jsonify(users)

@app.route('/get_messages/<int:receiver_id>')
def get_messages(receiver_id):
    if 'user_id' not in session:
        return jsonify([])
    
    sender_id = session['user_id']
    org_id = session['org_id']
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get all messages
        cursor.execute("""
            SELECT * FROM messages
            WHERE ((sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)) AND org_id = %s
            ORDER BY timestamp ASC
        """, (sender_id, receiver_id, receiver_id, sender_id, org_id))
        messages = cursor.fetchall()
        
        # Check if there are unread messages BEFORE marking as read
        cursor.execute("""
            SELECT COUNT(*) as unread_count
            FROM messages 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (receiver_id, sender_id))
        unread_result = cursor.fetchone()
        had_unread = unread_result['unread_count'] > 0 if unread_result else False
        
        # Mark messages as read
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (receiver_id, sender_id))
        
        # Also mark communication notifications as read
        if had_unread:
            cursor.execute("""
                UPDATE notifications 
                SET is_read = TRUE 
                WHERE user_id = %s 
                AND org_id = %s 
                AND notification_type = 'communication_message'
                AND is_read = FALSE
            """, (sender_id, org_id))
        
        conn.commit()
        
        # Convert datetime to ISO format
        for message in messages:
            if 'timestamp' in message and message['timestamp']:
                if isinstance(message['timestamp'], (datetime, date)):
                    message['timestamp'] = message['timestamp'].isoformat()
        
        return jsonify({
            'messages': messages,
            'marked_as_read': had_unread
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON'})
        
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    sender_id = session['user_id']
    org_id = session['org_id']

    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing data'})

    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Don't specify timestamp - let DEFAULT CURRENT_TIMESTAMP handle it
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, message, org_id)
            VALUES (%s, %s, %s, %s)
        """, (sender_id, receiver_id, message, org_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/mark_as_read', methods=['POST'])
def mark_as_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON'})
    
    sender_id = data.get('sender_id')
    receiver_id = session['user_id']
    
    if not sender_id:
        return jsonify({'success': False, 'error': 'Missing sender_id'})
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (sender_id, receiver_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/mark_messages_read/<int:sender_id>', methods=['POST'])
def mark_messages_read(sender_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    receiver_id = session['user_id']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (sender_id, receiver_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



######################enhanced advance salary routes#############################
@app.route('/advance_management')
def advance_management():
    """Display advance management page for accountant"""
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get all advances with employee details
        cur.execute("""
            SELECT 
                a.id,
                a.advance_amount,
                a.remaining_amount,
                a.created_on,
                r.name as employee_name,
                r.role as employee_role,
                creator.name as created_by_name
            FROM advances a
            JOIN register r ON a.user_id = r.id
            JOIN register creator ON a.created_by = creator.id
            WHERE a.org_id = %s AND r.role != 'admin'
            ORDER BY a.created_on DESC
        """, (org_id,))
        
        advances = cur.fetchall()
        
        # Format data
        for advance in advances:
            if advance['created_on']:
                advance['created_on'] = advance['created_on'].strftime('%Y-%m-%d %H:%M:%S')
            advance['advance_amount'] = float(advance['advance_amount'])
            advance['remaining_amount'] = float(advance['remaining_amount'])
            advance['deducted_amount'] = advance['advance_amount'] - advance['remaining_amount']
        
        # Get employees for the form dropdown
        cur.execute("""
            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN sites s ON p.site_id = s.site_id
            JOIN register r ON r.id = s.site_engineer_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN register r ON r.id = p.architect_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM register r
            WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s

            ORDER BY name ASC
        """, (accountant_id, org_id, accountant_id, org_id, accountant_id, org_id))
        employees = cur.fetchall()
        
    except Exception as e:
        flash(f"Error loading advance management: {str(e)}", "danger")
        advances = []
        employees = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return render_template('advance_management.html', advances=advances, employees=employees)


@app.route('/add_advance', methods=['POST'])
def add_advance():
    """Add a new advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        advance_amount = float(data.get('advance_amount', 0))
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        if advance_amount <= 0:
            return jsonify({'success': False, 'error': 'Advance amount must be greater than 0'}), 400
        
        accountant_id = session['user_id']
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Verify user belongs to organization
        cur.execute("""
            SELECT id FROM register WHERE id = %s AND org_id = %s AND role != 'admin'
        """, (user_id, org_id))
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Employee not found in organization'}), 404
        
        # Insert advance record
        cur.execute("""
            INSERT INTO advances (user_id, advance_amount, remaining_amount, created_by, org_id, created_on)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, advance_amount, advance_amount, accountant_id, org_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance added successfully'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_user_total_advance', methods=['POST'])
def get_user_total_advance():
    """Get total remaining advance for a user"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get user details
        cur.execute("""
            SELECT name, role FROM register WHERE id = %s AND org_id = %s 
        """, (user_id, org_id))
        user_details = cur.fetchone()
        
        # Get total remaining advance
        cur.execute("""
            SELECT 
                COALESCE(SUM(advance_amount), 0) as total_given,
                COALESCE(SUM(remaining_amount), 0) as total_remaining
            FROM advances
            WHERE user_id = %s AND org_id = %s
        """, (user_id, org_id))
        
        advance_data = cur.fetchone()
        
        # Get advance history
        cur.execute("""
            SELECT 
                id,
                advance_amount,
                remaining_amount,
                created_on
            FROM advances
            WHERE user_id = %s AND org_id = %s 
            ORDER BY created_on DESC
        """, (user_id, org_id))
        
        history = cur.fetchall()
        
        # Format history
        for item in history:
            item['advance_amount'] = float(item['advance_amount'])
            item['remaining_amount'] = float(item['remaining_amount'])
            item['deducted_amount'] = item['advance_amount'] - item['remaining_amount']
            if item['created_on']:
                item['created_on'] = item['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'user_details': user_details,
            'total_given': float(advance_data['total_given']),
            'total_remaining': float(advance_data['total_remaining']),
            'total_deducted': float(advance_data['total_given']) - float(advance_data['total_remaining']),
            'history': history
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/deduct_advance_from_salary', methods=['POST'])
def deduct_advance_from_salary():
    """Deduct advance amount when processing salary (internal function)"""
    # This is called automatically from add_salary route
    try:
        user_id = request.json.get('user_id')
        deduction_amount = float(request.json.get('deduction_amount', 0))
        org_id = session['org_id']
        
        if deduction_amount <= 0:
            return jsonify({'success': True, 'message': 'No deduction needed'})
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get advances with remaining balance (oldest first - FIFO)
        cur.execute("""
            SELECT id, advance_amount, remaining_amount
            FROM advances
            WHERE user_id = %s AND org_id = %s AND remaining_amount > 0
            ORDER BY created_on ASC
        """, (user_id, org_id))
        
        advances = cur.fetchall()
        
        if not advances:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No advance available for this employee'}), 400
        
        # Calculate total available
        total_available = sum(float(adv['remaining_amount']) for adv in advances)
        
        if deduction_amount > total_available:
            cur.close()
            conn.close()
            return jsonify({
                'success': False, 
                'error': f'Deduction amount (₹{deduction_amount:.2f}) exceeds available advance (₹{total_available:.2f})'
            }), 400
        
        # Deduct from advances (FIFO)
        remaining_to_deduct = deduction_amount
        
        for advance in advances:
            if remaining_to_deduct <= 0:
                break
            
            advance_id = advance['id']
            advance_remaining = float(advance['remaining_amount'])
            
            if remaining_to_deduct >= advance_remaining:
                # Fully deduct this advance
                new_remaining = 0
                remaining_to_deduct -= advance_remaining
            else:
                # Partially deduct
                new_remaining = advance_remaining - remaining_to_deduct
                remaining_to_deduct = 0
            
            # Update advance
            cur.execute("""
                UPDATE advances
                SET remaining_amount = %s
                WHERE id = %s
            """, (new_remaining, advance_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance deducted successfully',
            'deducted_amount': deduction_amount
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
# Add this route to handle advance updates

@app.route('/update_advance_amount/<int:advance_id>', methods=['POST'])
def update_advance_amount(advance_id):
    """Update advance amount - add more to existing advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        additional_amount = float(data.get('additional_amount', 0))
        
        if additional_amount <= 0:
            return jsonify({'success': False, 'error': 'Additional amount must be greater than 0'}), 400
        
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get current advance details
        cur.execute("""
            SELECT advance_amount, remaining_amount, user_id
            FROM advances
            WHERE id = %s AND org_id = %s 
        """, (advance_id, org_id))
        
        advance = cur.fetchone()
        
        if not advance:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Advance not found'}), 404
        
        # Calculate new amounts
        new_advance_amount = float(advance['advance_amount']) + additional_amount
        new_remaining_amount = float(advance['remaining_amount']) + additional_amount
        
        # Update advance record
        cur.execute("""
            UPDATE advances
            SET advance_amount = %s, remaining_amount = %s
            WHERE id = %s
        """, (new_advance_amount, new_remaining_amount, advance_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance updated successfully',
            'new_advance_amount': new_advance_amount,
            'new_remaining_amount': new_remaining_amount
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/get_employee_advance', methods=['POST'])
def get_employee_advance():
    """Get employee's remaining advance from advances table - NEW ROUTE FOR ADD SALARY PAGE"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
            
        org_id = session['org_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get total remaining advance from advances table
        cur.execute("""
            SELECT COALESCE(SUM(remaining_amount), 0) as total_remaining
            FROM advances
            WHERE user_id = %s AND org_id = %s 
        """, (user_id, org_id))
        
        result = cur.fetchone()
        remaining_advance = float(result['total_remaining']) if result else 0.00

        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'remaining_advance': remaining_advance
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_advance_details/<int:advance_id>', methods=['GET'])
def get_advance_details(advance_id):
    """Get details of a specific advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        cur.execute("""
            SELECT 
                a.id,
                a.advance_amount,
                a.remaining_amount,
                a.created_on,
                r.name as employee_name,
                r.role as employee_role,
                creator.name as created_by_name
            FROM advances a
            JOIN register r ON a.user_id = r.id
            JOIN register creator ON a.created_by = creator.id
            WHERE a.id = %s AND a.org_id = %s 
        """, (advance_id, org_id))
        
        advance = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not advance:
            return jsonify({'success': False, 'error': 'Advance not found'}), 404
        
        # Format data
        advance['advance_amount'] = float(advance['advance_amount'])
        advance['remaining_amount'] = float(advance['remaining_amount'])
        advance['deducted_amount'] = advance['advance_amount'] - advance['remaining_amount']
        if advance['created_on']:
            advance['created_on'] = advance['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'advance': advance
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


# Simplified add_salary route with advance integration

@app.route('/add_salary', methods=['GET', 'POST'])
def add_salary():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))

    accountant_id = session['user_id']
    org_id = session['org_id']

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch assigned projects
    cur.execute("""
        SELECT DISTINCT p.id, p.project_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        GROUP BY p.id, p.project_name
    """, (accountant_id, org_id))
    projects = cur.fetchall()

    # Fetch relevant users
    cur.execute("""
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN sites s ON p.site_id = s.site_id
        JOIN register r ON r.id = s.site_engineer_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        
        UNION
        
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN register r ON r.id = p.architect_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        
        UNION
        
        SELECT DISTINCT r.id, r.name, r.role
        FROM register r
        WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s
    """, (accountant_id, org_id, accountant_id, org_id, accountant_id, org_id))
    users = cur.fetchall()

    if request.method == 'POST':
        try:
            project_id = request.form['project_id']
            user_id = request.form['user_id']
            role = request.form['role']
            month_year = request.form['month_year']
            base_salary = float(request.form['base_salary'])
            allowance = float(request.form.get('allowance', 0) or 0)
            pf = float(request.form.get('pf', 0) or 0)
            other_deductions = float(request.form.get('other_deductions', 0) or 0)
            advance_deduction = float(request.form.get('advance', 0) or 0)
            description = request.form.get('description', '').strip()
            payment_mode = request.form['payment_mode']
            cheque_number = request.form.get('cheque_number', '').strip() if payment_mode == 'cheque' else None

            # Calculate net salary
            net_salary = base_salary + allowance - pf - advance_deduction - other_deductions

            # Check if salary already exists
            cur.execute("""
                SELECT id FROM salaries 
                WHERE user_id = %s AND project_id = %s AND month_year = %s 
                AND org_id = %s AND base_salary > 0
            """, (user_id, project_id, month_year, org_id))
            
            existing_salary = cur.fetchone()
            if existing_salary:
                flash('Salary already exists for this user, project, and month.', 'warning')
                return render_template('add_salary.html', projects=projects, users=users)

            # Insert salary record (without pdf_filename initially)
            cur.execute("""
                INSERT INTO salaries (
                    project_id, user_id, role, month_year, base_salary, allowance, pf,
                    advance, other_deductions, description, net_salary, payment_mode, 
                    cheque_number, created_by, created_on, org_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (
                project_id, user_id, role, month_year, base_salary, allowance, pf,
                advance_deduction, other_deductions, description, net_salary, payment_mode, 
                cheque_number, accountant_id, org_id
            ))
            salary_id = cur.lastrowid   # Get the ID of the newly inserted salary

            # If advance deduction was made, update advances table
            if advance_deduction > 0:
                # Get advances with remaining balance (oldest first - FIFO)
                cur.execute("""
                    SELECT id, advance_amount, remaining_amount
                    FROM advances
                    WHERE user_id = %s AND org_id = %s AND remaining_amount > 0
                    ORDER BY created_on ASC
                """, (user_id, org_id))
                
                advances = cur.fetchall()
                
                if not advances:
                    conn.rollback()
                    flash('No advance available for this employee.', 'danger')
                    return render_template('add_salary.html', projects=projects, users=users)
                
                # Calculate total available
                total_available = sum(float(adv['remaining_amount']) for adv in advances)
                
                if advance_deduction > total_available:
                    conn.rollback()
                    flash(f'Advance deduction (₹{advance_deduction:.2f}) exceeds available advance (₹{total_available:.2f})', 'danger')
                    return render_template('add_salary.html', projects=projects, users=users)
                
                # Deduct from advances (FIFO)
                remaining_to_deduct = advance_deduction
                
                for advance in advances:
                    if remaining_to_deduct <= 0:
                        break
                    
                    advance_id = advance['id']
                    advance_remaining = float(advance['remaining_amount'])
                    
                    if remaining_to_deduct >= advance_remaining:
                        # Fully deduct this advance
                        new_remaining = 0
                        remaining_to_deduct -= advance_remaining
                    else:
                        # Partially deduct
                        new_remaining = advance_remaining - remaining_to_deduct
                        remaining_to_deduct = 0
                    
                    # Update advance
                    cur.execute("""
                        UPDATE advances
                        SET remaining_amount = %s
                        WHERE id = %s
                    """, (new_remaining, advance_id))

            conn.commit()

            # 🔥 START BACKGROUND PDF GENERATION FOR SALARY SLIP
            thread = threading.Thread(
                target=generate_salary_slip_async,
                args=(salary_id, org_id)
            )
            thread.daemon = True
            thread.start()

            # 1. Notify the employee about their salary entry
            create_notification(
                user_id=user_id,
                org_id=org_id,
                notification_type='salary_new',
                reference_id=salary_id,
                message=f'Salary entry for {month_year} has been processed. Net: ₹{net_salary:,.2f}',
                cur=cur
            )
            # 2. Notify all admins about the new salary entry
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()
            
            # Get employee name for admin notification
            cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
            emp_data = cur.fetchone()
            emp_name = emp_data['name'] if emp_data else 'Employee'
            
            # Get project name
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            proj_data = cur.fetchone()
            project_name = proj_data['project_name'] if proj_data else 'Unknown Project'
            
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='salary_added',
                    reference_id=salary_id,
                    message=f'Salary added: {emp_name} - {project_name} ({month_year}) - Net: ₹{net_salary:,.2f}',
                    cur=cur
                )
            conn.commit()

            flash('Salary entry added successfully. Salary slip PDF will be generated in the background.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('add_salary'))

    cur.close()
    conn.close()
    return render_template('add_salary.html', projects=projects, users=users)


@app.route('/api/get_users_by_project/<int:project_id>')
def get_users_by_project(project_id):
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'error': 'Unauthorized'}), 401
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        cur.execute("""
            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN sites s ON p.site_id = s.site_id
            JOIN register r ON r.id = s.site_engineer_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s AND p.id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN register r ON r.id = p.architect_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s AND p.id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM register r
            WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s
        """, (accountant_id, org_id, project_id,
              accountant_id, org_id, project_id,
              accountant_id, org_id))
        
        users = cur.fetchall()
        return jsonify({'users': users})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Accountant: View Own Entered Salaries
@app.route('/view_salaries')
def view_salaries():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']

    # Mark salary notifications as read when accountant views this page
    mark_notifications_as_read(accountant_id, org_id, 'salary_new')

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        cur.execute("""
            SELECT 
                s.*, 
                p.project_name, 
                r.name AS user_name, 
                cr.name AS created_by_name
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            JOIN register cr ON s.created_by = cr.id
            WHERE s.created_by = %s AND s.org_id = %s
            ORDER BY s.created_on DESC, s.month_year DESC, p.project_name
        """, (accountant_id, org_id))
        
        salaries = cur.fetchall()
        
        # Process each salary record to add computed fields
        for salary in salaries:
            if salary['base_salary'] == 0 and salary['advance'] > 0:
                salary['entry_type'] = 'Advance Payment'
            elif salary['base_salary'] > 0 and salary['advance'] > 0:
                salary['entry_type'] = 'Salary with Advance Deduction'
            elif salary['base_salary'] > 0 and (salary['advance'] == 0 or salary['advance'] is None):
                salary['entry_type'] = 'Salary Payment'
            else:
                salary['entry_type'] = 'Other'
            
            if salary['base_salary'] == 0:
                salary['net_amount'] = float(salary['advance'] or 0)
            else:
                base = float(salary['base_salary'] or 0)
                allowance = float(salary['allowance'] or 0)
                pf = float(salary['pf'] or 0)
                advance = float(salary['advance'] or 0)
                other_deductions = float(salary.get('other_deductions', 0) or 0)
                salary['net_amount'] = base + allowance - pf - advance - other_deductions
    except Exception as e:
        flash(f"Error loading salaries: {str(e)}", "danger")
        salaries = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return render_template('view_salaries.html', salaries=salaries)

@app.route('/admin/view_salaries')
def admin_view_salaries():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    admin_id = session['user_id']
    org_id = session.get('org_id')
    
    # Mark salary notifications as read when admin views this page
    mark_notifications_as_read(admin_id, org_id, 'salary_added')
    
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        cur.execute("""
            SELECT s.*, p.project_name, r.name AS user_name, cr.name AS created_by_name
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            JOIN register cr ON s.created_by = cr.id
            WHERE s.org_id = %s
            ORDER BY s.month_year DESC, p.project_name
        """, (org_id,))
        salaries = cur.fetchall()
    except Exception as e:
        flash(f"Error loading salaries: {str(e)}", "danger")
        salaries = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return render_template('admin_view_salaries.html', salaries=salaries)



##########base salary ##############################

@app.route('/base_salary_management')
def base_salary_management():
    """Display base salary management page for accountant"""
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        cur.execute("""
            SELECT DISTINCT
                r.id,
                r.name,
                r.role,
                COALESCE(bs.salary, 0.00) as base_salary,
                bs.created_on,
                bs.updated_on,
                creator.name as created_by_name,
                updater.name as updated_by_name
            FROM register r
            LEFT JOIN base_salaries bs ON r.id = bs.user_id AND bs.org_id = %s
            LEFT JOIN register creator ON bs.created_by = creator.id
            LEFT JOIN register updater ON bs.updated_by = updater.id
            WHERE r.org_id = %s
            AND r.role != 'admin'
            AND r.id IN (
                SELECT DISTINCT s.site_engineer_id
                FROM accountant_projects ap
                JOIN projects p ON ap.project_id = p.id
                JOIN sites s ON p.site_id = s.site_id
                WHERE ap.accountant_id = %s AND ap.org_id = %s
                AND s.site_engineer_id IS NOT NULL

                UNION

                SELECT DISTINCT p.architect_id
                FROM accountant_projects ap
                JOIN projects p ON ap.project_id = p.id
                WHERE ap.accountant_id = %s AND ap.org_id = %s
                AND p.architect_id IS NOT NULL

                UNION

                SELECT %s
            )
            ORDER BY r.name ASC
        """, (org_id, org_id, accountant_id, org_id, accountant_id, org_id, accountant_id))
        
        employees = cur.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for emp in employees:
            if emp['created_on']:
                emp['created_on'] = emp['created_on'].strftime('%Y-%m-%d %H:%M:%S')
            if emp['updated_on']:
                emp['updated_on'] = emp['updated_on'].strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        flash(f"Error loading base salary management: {str(e)}", "danger")
        employees = []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return render_template('base_salary_management.html', employees=employees)


@app.route('/get_employee_base_salary', methods=['POST'])
def get_employee_base_salary():
    """Get base salary for a specific employee"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        org_id = session['org_id']
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get employee details with base salary
        cur.execute("""
            SELECT 
                r.id,
                r.name,
                r.role,
                COALESCE(bs.salary, 0.00) as base_salary,
                bs.created_on,
                bs.updated_on,
                creator.name as created_by_name,
                updater.name as updated_by_name
            FROM register r
            LEFT JOIN base_salaries bs ON r.id = bs.user_id AND bs.org_id = %s
            LEFT JOIN register creator ON bs.created_by = creator.id
            LEFT JOIN register updater ON bs.updated_by = updater.id
            WHERE r.id = %s AND r.org_id = %s AND r.role != 'admin'
        """, (org_id, user_id, org_id))
        
        employee = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not employee:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Convert datetime objects to strings
        if employee['created_on']:
            employee['created_on'] = employee['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        if employee['updated_on']:
            employee['updated_on'] = employee['updated_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'employee': employee
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_base_salary', methods=['POST'])
def update_base_salary():
    """Update or create base salary for an employee"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_salary = data.get('salary')
        
        if not user_id or new_salary is None:
            return jsonify({'success': False, 'error': 'User ID and salary are required'}), 400
        
        # Validate salary amount
        try:
            new_salary = float(new_salary)
            if new_salary < 0:
                return jsonify({'success': False, 'error': 'Salary cannot be negative'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid salary amount'}), 400
        
        accountant_id = session['user_id']
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if employee exists in the organization
        cur.execute("""
            SELECT id FROM register WHERE id = %s AND org_id = %s AND role != 'admin'
        """, (user_id, org_id))
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Employee not found in organization'}), 404
        
        # Check if base salary record exists
        cur.execute("""
            SELECT id FROM base_salaries WHERE user_id = %s AND org_id = %s
        """, (user_id, org_id))
        
        existing_record = cur.fetchone()
        
        if existing_record:
            # Update existing record
            cur.execute("""
                UPDATE base_salaries 
                SET salary = %s, updated_by = %s, updated_on = NOW()
                WHERE user_id = %s AND org_id = %s
            """, (new_salary, accountant_id, user_id, org_id))
            message = 'Base salary updated successfully'
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO base_salaries (user_id, salary, created_by, org_id, created_on)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, new_salary, accountant_id, org_id))
            message = 'Base salary added successfully'
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
####################salary slip download ###########################

@app.route('/download_salary_slip/<int:salary_id>')
def download_salary_slip(salary_id):
    if 'role' not in session or session['role'] not in ['accountant', 'admin']:
        return redirect(url_for('login'))
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM salaries WHERE id = %s AND org_id = %s", (salary_id, session['org_id']))
        salary = cur.fetchone()
        if salary and salary['pdf_filename']:
            pdf_path = os.path.join(app.static_folder, 'salary_slips', salary['pdf_filename'])
            if os.path.exists(pdf_path):
                return send_file(pdf_path, as_attachment=True, download_name=f"SalarySlip_{salary_id}.pdf")
            else:
                flash('PDF file not found. It may still be generating.', 'warning')
        else:
            flash('Salary slip PDF is being generated. Please try again in a few moments.', 'info')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(request.referrer or url_for('view_salaries'))


@app.route('/api/salary_slip_status/<int:salary_id>')
def api_salary_slip_status(salary_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM salaries WHERE id = %s AND org_id = %s", (salary_id, session['org_id']))
        result = cur.fetchone()
        if result and result['pdf_filename']:
            return jsonify({'status': 'ready'})
        else:
            return jsonify({'status': 'processing'})
    finally:
        cur.close()
        conn.close()
    

@app.route('/download_salary_report', methods=['POST'])
def download_salary_report():
    """Start background generation of salary disbursement report and return task ID."""
    if 'role' not in session or session['role'] not in ['accountant', 'admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    month_year = data.get('month_year')
    if not month_year:
        return jsonify({'success': False, 'error': 'Month-year is required'}), 400

    org_id = session['org_id']
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Insert task record
        cur.execute("""
            INSERT INTO salary_report_tasks (month_year, status, org_id, created_by)
            VALUES (%s, 'pending', %s, %s)
        """, (month_year, org_id, user_id))
        task_id = cur.lastrowid
        conn.commit()
    finally:
        cur.close()
        conn.close()

    # Start background thread
    thread = threading.Thread(
        target=generate_salary_report_async,
        args=(task_id, month_year, org_id, user_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/salary_report_status/<int:task_id>')
def api_salary_report_status(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT status, pdf_filename, error_message FROM salary_report_tasks WHERE id = %s AND org_id = %s",
                    (task_id, session['org_id']))
        task = cur.fetchone()
        if not task:
            return jsonify({'status': 'not_found'}), 404
        return jsonify({
            'status': task['status'],
            'pdf_filename': task.get('pdf_filename'),
            'error': task.get('error_message')
        })
    finally:
        cur.close()
        conn.close()

@app.route('/download_salary_report_file/<int:task_id>')
def download_salary_report_file(task_id):
    if 'user_id' not in session:
        abort(401)
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT status, pdf_filename FROM salary_report_tasks WHERE id = %s AND org_id = %s",
                    (task_id, session['org_id']))
        task = cur.fetchone()
        if task and task['status'] == 'completed' and task['pdf_filename']:
            pdf_path = os.path.join(app.static_folder, 'salary_reports', task['pdf_filename'])
            if os.path.exists(pdf_path):
                return send_file(pdf_path, as_attachment=True, download_name=task['pdf_filename'])
            else:
                flash('Report file not found.', 'danger')
        else:
            flash('Report not ready or invalid.', 'warning')
    finally:
        cur.close()
        conn.close()
    return redirect(request.referrer or url_for('view_salaries'))


@app.route('/api/get_compliance_data')
def get_compliance_data():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return jsonify({'error': 'Unauthorized'}), 401

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'Project ID required'}), 400

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute("""
            SELECT * FROM legal_and_compliances 
            WHERE project_id = %s AND org_id = %s
        """, (project_id, session['org_id']))
        
        compliance = cur.fetchone()
        
        if compliance:
            return jsonify({
                'exists': True,
                'municipal_approval_status': compliance['municipal_approval_status'],
                'municipal_approval_pdf': compliance['municipal_approval_pdf'],
                'building_permit_pdf': compliance['building_permit_pdf'],
                'sanction_plan_pdf': compliance['sanction_plan_pdf'],
                'fire_department_noc_pdf': compliance['fire_department_noc_pdf'],
                'mngl_pdf': compliance['mngl_pdf'],
                'environmental_clearance': compliance['environmental_clearance']
            })
        else:
            return jsonify({'exists': False})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cur.close()
        conn.close()

@app.route('/site_engineer/expenses', methods=['GET', 'POST'])
def site_engineer_expenses():
    if 'user_id' not in session or session.get('role') != 'site_engineer':
        return redirect('/login')

    site_engineer_id = session['user_id']
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Get org_id for the current site engineer
        cursor.execute("SELECT org_id FROM register WHERE id = %s", (site_engineer_id,))
        org = cursor.fetchone()
        org_id = org['org_id'] if org else None

        view_type = request.args.get('view', 'submit')
        if view_type == 'status':
            # Mark expense status notifications as read when viewing updates
            mark_notifications_as_read(site_engineer_id, org_id, 'expense_status')

        # Handle expense form submission
        if request.method == 'POST':
            date = request.form['date']
            description = request.form['description']
            amount = request.form['amount']
            project_id = request.form['project_id']

            # Validate: ensure project belongs to this engineer and org
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM projects p
                JOIN sites s ON p.site_id = s.site_id
                WHERE p.id = %s AND s.site_engineer_id = %s AND s.org_id = %s
            """, (project_id, site_engineer_id, org_id))
            valid = cursor.fetchone()

            if valid and valid['count'] > 0:
                cursor.execute("""
                    INSERT INTO daily_expenses 
                    (site_engineer_id, org_id, project_id, date, description, amount) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (site_engineer_id, org_id, project_id, date, description, amount))
                expense_id = cursor.lastrowid
                conn.commit()
                
                # Notify admins
                cursor.execute("""
                    SELECT id FROM register 
                    WHERE role = 'admin' AND org_id = %s
                """, (org_id,))
                admins = cursor.fetchall()
                
                cursor.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
                project = cursor.fetchone()
                project_name = project['project_name'] if project else 'Unknown Project'
                
                for admin in admins:
                    create_notification(
                        user_id=admin['id'],
                        org_id=org_id,
                        notification_type='expense_submitted',
                        reference_id=expense_id,
                        message=f'New expense ₹{amount} submitted for {project_name} by {session.get("name")}',
                        cur=cursor
                    )
                conn.commit()
                
                flash('Expense added successfully.', 'success')
            else:
                flash('Invalid project selection. You can only add expenses for your assigned projects.', 'error')

        # Fetch expenses submitted by this engineer
        cursor.execute("""
            SELECT de.*, p.project_name 
            FROM daily_expenses de
            JOIN projects p ON de.project_id = p.id
            WHERE de.site_engineer_id = %s AND de.org_id = %s
            ORDER BY de.date DESC
        """, (site_engineer_id, org_id))
        expenses = cursor.fetchall()

        # Fetch projects assigned to this site engineer
        cursor.execute("""
            SELECT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND s.org_id = %s
        """, (site_engineer_id, org_id))
        projects = cursor.fetchall()

        return render_template("expenses.html", expenses=expenses, projects=projects)
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('site_engineer_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/site_engineer_expenses_view')
def site_engineer_expenses_view():
    # ✅ FIX 1: Use lowercase 'site_engineer' to match your existing route
    if 'user_id' not in session or session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # ✅ FIX 2: Get org_id from database like your existing route does
        cursor.execute("SELECT org_id FROM register WHERE id = %s", (user_id,))
        org = cursor.fetchone()
        org_id = org['org_id'] if org else None
        
        # ✅ FIX 3: Get projects using the same query structure as your existing route
        cursor.execute("""
            SELECT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND s.org_id = %s
        """, (user_id, org_id))
        projects = cursor.fetchall()
        
        # ✅ FIX 4: Query daily_expenses table (not expenses) and use site_engineer_id
        cursor.execute("""
            SELECT de.*, p.project_name
            FROM daily_expenses de
            JOIN projects p ON de.project_id = p.id
            WHERE de.site_engineer_id = %s AND de.org_id = %s
            ORDER BY de.date DESC, de.created_at DESC
        """, (user_id, org_id))
        expenses = cursor.fetchall()
        
    except Exception as e:
        flash(f"Error loading expenses: {str(e)}", "danger")
        projects = []
        expenses = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Categorize expenses
    pending_expenses = [exp for exp in expenses if exp['status'] == 'Pending']
    approved_expenses = [exp for exp in expenses if exp['status'] == 'Approved']
    rejected_expenses = [exp for exp in expenses if exp['status'] == 'Rejected']
    
    return render_template('site_engineer_expenses_view.html',
                         expenses=expenses,
                         pending_expenses=pending_expenses,
                         approved_expenses=approved_expenses,
                         rejected_expenses=rejected_expenses,
                         projects=projects)
##################################### Admin View Expenses #####################################
@app.route('/admin/expenses', methods=['GET', 'POST'])
def admin_view_expenses():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    admin_id = session['user_id']
    org_id = session.get('org_id')

    # Mark expense_submitted notifications as read
    mark_notifications_as_read(admin_id, org_id, 'expense_submitted')
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Handle approval/rejection
        if request.method == 'POST':
            expense_id = request.form['expense_id']
            action = request.form['action']
            comment = request.form.get('admin_comment', '')

            if action in ['Approved', 'Rejected']:
                # Fetch expense details before updating
                cursor.execute("""
                    SELECT de.*, r.name AS engineer_name, de.site_engineer_id, de.amount, p.project_name
                    FROM daily_expenses de
                    JOIN register r ON de.site_engineer_id = r.id
                    JOIN projects p ON de.project_id = p.id
                    WHERE de.id = %s
                """, (expense_id,))
                expense_data = cursor.fetchone()

                # Update status
                cursor.execute("""
                    UPDATE daily_expenses 
                    SET status = %s, admin_comment = %s 
                    WHERE id = %s AND org_id = %s
                """, (action, comment, expense_id, org_id))
                conn.commit()

                # Send notifications
                if expense_data and expense_data['site_engineer_id']:
                    notification_message = f'Expense ₹{expense_data["amount"]} for {expense_data["project_name"]} {action.lower()}'
                    if comment:
                        notification_message += f'. Comment: {comment}'

                    # Notify the site engineer
                    create_notification(
                        user_id=expense_data['site_engineer_id'],
                        org_id=org_id,
                        notification_type='expense_status',
                        reference_id=expense_id,
                        message=notification_message,
                        cur=cursor
                    )

                    # If approved, also notify accountants assigned to this project
                    if action == 'Approved':
                        cursor.execute("""
                            SELECT DISTINCT ap.accountant_id
                            FROM daily_expenses de
                            JOIN accountant_projects ap ON de.project_id = ap.project_id
                            WHERE de.id = %s AND de.org_id = %s
                        """, (expense_id, org_id))
                        accountants = cursor.fetchall()

                        for acc in accountants:
                            create_notification(
                                user_id=acc['accountant_id'],
                                org_id=org_id,
                                notification_type='expense_approved',
                                reference_id=expense_id,
                                message=f'Expense ₹{expense_data["amount"]} approved for {expense_data["project_name"]}',
                                cur=cursor
                            )
                    conn.commit()

            flash(f'Expense {action.lower()} successfully.', 'success')
            return redirect(url_for('admin_view_expenses'))

        # GET - Fetch all expenses for this org
        cursor.execute("""
            SELECT de.*, r.name AS engineer_name, p.project_name
            FROM daily_expenses de
            JOIN register r ON de.site_engineer_id = r.id
            JOIN projects p ON de.project_id = p.id
            WHERE de.org_id = %s
            ORDER BY de.created_at DESC
        """, (org_id,))
        expenses = cursor.fetchall()

    except Exception as e:
        flash(f"Error loading expenses: {str(e)}", "danger")
        expenses = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("admin_view_expenses.html", expenses=expenses)


##################################### Accountant View Expenses #####################################
@app.route('/accountant/expenses')
def accountant_view_expenses():
    if 'user_id' not in session or session.get('role') != 'accountant':
        return redirect('/login')

    accountant_id = session['user_id']
    org_id = session.get('org_id')

    # Mark expense_approved notifications as read
    mark_notifications_as_read(accountant_id, org_id, 'expense_approved')

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Get assigned project IDs for this accountant
        cursor.execute("""
            SELECT project_id FROM accountant_projects 
            WHERE accountant_id = %s AND org_id = %s
        """, (accountant_id, org_id))
        project_ids = [row['project_id'] for row in cursor.fetchall()]

        if not project_ids:
            expenses = []
        else:
            format_strings = ','.join(['%s'] * len(project_ids))
            query = f"""
                SELECT de.*, r.name AS engineer_name, p.project_name
                FROM daily_expenses de
                JOIN register r ON de.site_engineer_id = r.id
                JOIN projects p ON de.project_id = p.id
                WHERE de.org_id = %s AND de.status = 'Approved' 
                AND de.project_id IN ({format_strings})
                ORDER BY de.created_at DESC
            """
            cursor.execute(query, [org_id] + project_ids)
            expenses = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading expenses: {str(e)}", "danger")
        expenses = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("accountant_expenses.html", expenses=expenses)


@app.route('/admin/change_password', methods=['GET', 'POST'])
def admin_change_password():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        admin_id = session['user_id']
        
        conn = None  # Initialize conn
        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Verify current password
            cursor.execute("SELECT password_hash FROM register WHERE id = %s", (admin_id,))
            user = cursor.fetchone()
            
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if not check_password_hash(user['password_hash'], current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'warning')
                return redirect(url_for('admin_change_password'))
            
            # Update password
            hashed_pw = generate_password_hash(new_password)
            cursor.execute("UPDATE register SET password_hash = %s WHERE id = %s", (hashed_pw, admin_id))
            conn.commit()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin_change_password'))
            
        finally:
            if conn:
                conn.close()
    
    return render_template('admin_change_password.html')

################################### NOTIFICATION API ROUTES ###################################
@app.route('/api/notifications/count')
def get_notification_counts():
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    role = session.get('role', '')
    
    counts = {}
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # ── Single query for all notification type counts ──
        cur.execute("""
            SELECT notification_type, COUNT(*) as cnt
            FROM notifications
            WHERE user_id = %s AND org_id = %s AND is_read = 0
            GROUP BY notification_type
        """, (user_id, org_id))
        rows = cur.fetchall()
        type_counts = {row['notification_type']: int(row['cnt']) for row in rows}
        
        # ── Single query for total unread notifications ──
        total = sum(type_counts.values())
        
        # ── Single query for unread messages ──
        cur.execute("""
            SELECT COUNT(*) as unread_count 
            FROM messages 
            WHERE receiver_id = %s AND org_id = %s AND is_read = FALSE
        """, (user_id, org_id))
        msg_result = cur.fetchone()
        unread_messages = int(msg_result['unread_count']) if msg_result else 0

        if role == 'site_engineer':
            counts['projects']         = type_counts.get('project_assigned', 0)
            counts['invoices']         = (
                type_counts.get('invoice_rejected', 0) +
                type_counts.get('invoice_approved', 0)
            )
            counts['expenses']         = type_counts.get('expense_status', 0)
            counts['vendor_inventory'] = type_counts.get('vendor_approved', 0)
            counts['legal']            = type_counts.get('legal_updated', 0)
            counts['communication']    = unread_messages

        elif role == 'admin':
            counts['invoices']         = type_counts.get('invoice_pending', 0)
            counts['expenses']         = type_counts.get('expense_submitted', 0)
            counts['worker_reports']   = type_counts.get('worker_report_new', 0)
            counts['vendor_inventory'] = type_counts.get('vendor_pending', 0)
            counts['enquiries']        = type_counts.get('enquiry_new', 0)
            counts['salaries']         = type_counts.get('salary_added', 0)
            counts['progress']         = type_counts.get('progress_report', 0)
            counts['inventory']        = type_counts.get('inventory_added', 0)
            counts['communication']    = unread_messages
            counts['bills']            = type_counts.get('bill_added', 0)

        elif role == 'architect':
            counts['projects']      = type_counts.get('project_assigned', 0)
            counts['legal']         = type_counts.get('legal_updated', 0)
            counts['communication'] = unread_messages

        elif role == 'accountant':
            counts['invoices']      = type_counts.get('invoice_approved', 0)
            counts['expenses']      = type_counts.get('expense_approved', 0)
            counts['salary']        = type_counts.get('salary_new', 0)
            counts['projects']      = type_counts.get('project_assigned', 0)
            counts['legal']         = type_counts.get('legal_updated', 0)
            counts['communication'] = unread_messages
            counts['bills']         = type_counts.get('bill_added', 0)

        else:
            counts['info'] = 'No role-specific counts available'

        counts['total'] = total + unread_messages

        return jsonify(counts), 200

    except Exception as e:
        print(f"Error in get_notification_counts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/notifications/recent')
def get_recent_notifications_api():
    """
    API endpoint to get recent notifications for current user
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    limit = request.args.get('limit', 10, type=int)
    
    try:
        notifications = get_recent_notifications(user_id, org_id, limit)
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        }), 200
        
    except Exception as e:
        print(f"Error in get_recent_notifications_api: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read_api():
    """
    API endpoint to mark notifications as read by type
    Expects JSON: { "notification_type": "project_assigned" }
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data or 'notification_type' not in data:
        return jsonify({'error': 'notification_type is required'}), 400
    
    user_id = session['user_id']
    org_id = session['org_id']
    notification_type = data['notification_type']
    
    try:
        affected = mark_notifications_as_read(user_id, org_id, notification_type)
        return jsonify({
            'success': True,
            'message': f'{affected} notifications of type {notification_type} marked as read'
        }), 200
        
    except Exception as e:
        print(f"Error in mark_notifications_read_api: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """
    API endpoint to mark ALL notifications as read for current user
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications 
            SET is_read = 1 
            WHERE user_id = %s AND org_id = %s AND is_read = 0
        """, (user_id, org_id))
        
        affected_rows = cur.rowcount
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{affected_rows} notifications marked as read'
        }), 200
        
    except Exception as e:
        print(f"Error in mark_all_notifications_read: {e}")
        conn.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/notifications/delete/<int:notification_id>', methods=['DELETE'])
def delete_notification_api(notification_id):
    """
    API endpoint to delete a specific notification
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM notifications 
            WHERE id = %s AND user_id = %s AND org_id = %s
        """, (notification_id, user_id, org_id))
        
        if cur.rowcount > 0:
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Notification deleted'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Notification not found or unauthorized'
            }), 404
            
    except Exception as e:
        print(f"Error in delete_notification_api: {e}")
        conn.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/notifications/debug-all')
def debug_all_notifications():
    """DEBUG ONLY - See all notifications in database"""
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get ALL notifications (not filtered by user)
        cur.execute("""
            SELECT 
                n.id,
                n.user_id,
                n.org_id,
                n.notification_type,
                n.reference_id,
                n.message,
                n.is_read,
                n.created_at,
                r.name as user_name,
                r.role as user_role
            FROM notifications n
            LEFT JOIN register r ON n.user_id = r.id
            ORDER BY n.created_at DESC
            LIMIT 50
        """)
        
        all_notifs = cur.fetchall()
        
        # Convert datetime
        for n in all_notifs:
            if n['created_at']:
                n['created_at'] = n['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return jsonify({
        'total_count': len(all_notifs),
        'notifications': all_notifs,
        'session_user_id': session.get('user_id'),
        'session_org_id': session.get('org_id'),
        'session_role': session.get('role')
    })

    ################################### NOTIFICATION TYPE CONSTANTS ###################################

# Notification Types Reference
NOTIFICATION_TYPES = {
    # Site Engineer notifications
    'project_assigned': 'New project assigned to you',
    'invoice_rejected': 'Your invoice was rejected',
    'invoice_approved': 'Your invoice was approved',
    'expense_status': 'Your expense status updated',
    'vendor_approved': 'Vendor inventory approved',
    
    # Admin notifications
    'invoice_pending': 'New invoice pending approval',
    'expense_submitted': 'New expense submitted',
    'worker_report_new': 'New worker report submitted',
    'vendor_pending': 'Vendor inventory pending approval',
    'enquiry_new': 'New visitor enquiry submitted',
    'salary_added': 'New salary entry added',
    
    # Architect notifications
    'legal_updated': 'Legal compliance updated',
    
    # Accountant notifications
    'salary_new': 'New salary entry',
    
    # Common notifications
    'message_new': 'New message received',
    'progress_report': 'New progress report uploaded'
}

############bills and payments routes#####################
import os
import time
from io import BytesIO
from datetime import datetime
from werkzeug.utils import secure_filename

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

# ── Upload folder for bill files ──────────────────────────────
UPLOAD_FOLDER_BILLS = 'static/bill_uploads'
os.makedirs(UPLOAD_FOLDER_BILLS, exist_ok=True)

def allowed_bill_file(filename):
    ALLOWED = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


# ── Route: Bills & Payments (Add + History) ───────────────────
@app.route('/bills_and_payments', methods=['GET', 'POST'])
def bills_and_payments():
    if 'role' not in session or session['role'] not in ['admin', 'accountant']:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role    = session['role']
    org_id  = session['org_id']

    # ── POST: Add new bill ────────────────────────────────────────────────────
    if request.method == 'POST':
        conn   = None
        cur    = None
        bill_id = None
        try:
            bill_no                = request.form['bill_no'].strip()
            bill_date              = request.form['bill_date']
            bill_type              = request.form['bill_type']
            advance_amount         = float(request.form.get('advance_amount', 0) or 0)
            running_account_amount = float(request.form.get('running_account_amount', 0) or 0)
            final_amount           = float(request.form.get('final_amount', 0) or 0)
            work_name              = request.form['work_name'].strip()
            project_id             = request.form.get('project_id') or None
            accountant_id          = request.form.get('accountant_id') or None
            work_order_number      = request.form['work_order_number'].strip()
            work_order_date        = request.form['work_order_date']
            tender_name            = request.form.get('tender_name', '').strip()
            tender_number          = request.form.get('tender_number', '').strip()
            gross_amount           = float(request.form['gross_amount'])
            gst_percentage         = float(request.form['gst_percentage'])
            security_deposit       = float(request.form.get('security_deposit', 0) or 0)
            payment_status         = request.form['payment_status']

            # ── Calculations ──
            gst_amount     = round((gross_amount * gst_percentage) / 100, 2)
            labour_charges = round((gross_amount * 1.1) / 100, 2)
            net_amount     = round(gross_amount + gst_amount - security_deposit - labour_charges, 2)

            # ── File upload ──
            bill_file_path = None
            bill_file_type = None

            if 'bill_file' in request.files:
                file = request.files['bill_file']
                if file and file.filename and allowed_bill_file(file.filename):
                    filename    = secure_filename(file.filename)
                    file_ext    = filename.rsplit('.', 1)[1].lower()
                    unique_name = f"bill_{bill_no.replace('/', '_')}_{int(time.time())}.{file_ext}"
                    save_path   = os.path.join(UPLOAD_FOLDER_BILLS, unique_name)
                    file.save(save_path)
                    bill_file_path = f"bill_uploads/{unique_name}"
                    bill_file_type = 'pdf' if file_ext == 'pdf' else 'image'

            conn = get_connection()
            cur  = conn.cursor(pymysql.cursors.DictCursor)

            # ── Insert bill (without pdf_filename initially) ──
            cur.execute("""
                INSERT INTO bills_and_payments (
                    bill_no, bill_date, bill_type, bill_file_path, bill_file_type,
                    advance_amount, running_account_amount, final_amount,
                    work_name, work_order_number, work_order_date,
                    tender_name, tender_number,
                    gross_amount, gst_percentage, gst_amount,
                    security_deposit, labour_charges, net_amount,
                    payment_status, created_by, created_by_role, org_id,
                    project_id, accountant_id
                ) VALUES (
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s
                )
            """, (
                bill_no, bill_date, bill_type, bill_file_path, bill_file_type,
                advance_amount, running_account_amount, final_amount,
                work_name, work_order_number, work_order_date,
                tender_name, tender_number,
                gross_amount, gst_percentage, gst_amount,
                security_deposit, labour_charges, net_amount,
                payment_status, user_id, role, org_id,
                project_id, accountant_id
            ))
            bill_id = cur.lastrowid

            # ── Commit bill insert ──
            conn.commit()

            # 🔥 START BACKGROUND PDF GENERATION FOR BILL
            import threading
            thread = threading.Thread(
                target=generate_bill_pdf_async,
                args=(bill_id, org_id)
            )
            thread.daemon = True
            thread.start()

            # ── Notifications after successful commit ──
            # Use fresh cursor after commit
            cur.close()
            cur = conn.cursor(pymysql.cursors.DictCursor)

            try:
                cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
                creator_data  = cur.fetchone()
                creator_name  = creator_data['name'] if creator_data else 'User'

                notification_message = (
                    f'New {bill_type} added: {bill_no} - {work_name} '
                    f'(₹{net_amount:,.2f}) by {creator_name}'
                )

                if role == 'admin':
                    # Admin added bill → notify assigned accountant only
                    if accountant_id:
                        create_notification(
                            user_id=int(accountant_id),
                            org_id=org_id,
                            notification_type='bill_added',
                            reference_id=bill_id,
                            message=notification_message,
                            cur=cur
                        )
                elif role == 'accountant':
                    # Accountant added bill → notify all admins
                    cur.execute("""
                        SELECT id FROM register 
                        WHERE role = 'admin' AND org_id = %s
                    """, (org_id,))
                    admins = cur.fetchall()
                    for admin in admins:
                        create_notification(
                            user_id=admin['id'],
                            org_id=org_id,
                            notification_type='bill_added',
                            reference_id=bill_id,
                            message=notification_message,
                            cur=cur
                        )
                conn.commit()
            except Exception as notif_err:
                # Notification failure should NOT rollback the bill that was already saved
                print(f"Warning: Notification failed after bill commit: {notif_err}")

            flash('Bill added successfully! Bill PDF will be generated in the background.', 'success')
            return redirect(url_for('bills_and_payments', tab='history'))

        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error adding bill: {str(e)}', 'danger')
            return redirect(url_for('bills_and_payments'))

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    # ── GET: Fetch dropdown data + bill history ───────────────────────────────
    conn = None
    cur  = None
    try:
        conn = get_connection()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        # ── Mark bill notifications as read on GET ──
        mark_notifications_as_read(user_id, org_id, 'bill_added')

        # ── Fetch accountants and projects for admin dropdown ──
        accountants = []
        projects    = []
        if role == 'admin':
            cur.execute("""
                SELECT id, name FROM register 
                WHERE role = 'accountant' AND org_id = %s
                ORDER BY name
            """, (org_id,))
            accountants = cur.fetchall()

            cur.execute("""
                SELECT id, project_name FROM projects 
                WHERE org_id = %s
                ORDER BY project_name
            """, (org_id,))
            projects = cur.fetchall()

        # ── Fetch bills based on role ──
        if role == 'admin':
            cur.execute("""
                SELECT bp.*, r.name AS created_by_name
                FROM bills_and_payments bp
                JOIN register r ON bp.created_by = r.id
                WHERE bp.org_id = %s
                ORDER BY bp.created_at DESC
            """, (org_id,))
        elif role == 'accountant':
            cur.execute("""
                SELECT bp.*, r.name AS created_by_name
                FROM bills_and_payments bp
                JOIN register r ON bp.created_by = r.id
                WHERE bp.org_id = %s 
                AND (bp.accountant_id = %s OR bp.created_by = %s)
                ORDER BY bp.created_at DESC
            """, (org_id, user_id, user_id))

        bills      = cur.fetchall()
        active_tab = request.args.get('tab', 'add')

        return render_template(
            'bills_and_payments.html',
            bills=bills,
            active_tab=active_tab,
            accountants=accountants,
            projects=projects
        )

    except Exception as e:
        flash(f'Error loading bills: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard') if role == 'admin' else url_for('accountant_dashboard'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ── Route: Download Bill as PDF ──────────────────────────────
@app.route('/download_bill_pdf/<int:bill_id>')
def download_bill_pdf(bill_id):
    """Serve pre-generated bill PDF, or show message if not ready."""
    if 'role' not in session or session['role'] not in ['admin', 'accountant']:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM bills_and_payments WHERE id = %s AND org_id = %s", (bill_id, session['org_id']))
        bill = cur.fetchone()
        if bill and bill['pdf_filename']:
            pdf_path = os.path.join(app.static_folder, 'bill_pdfs', bill['pdf_filename'])
            if os.path.exists(pdf_path):
                return send_file(pdf_path, as_attachment=True, download_name=bill['pdf_filename'])
            else:
                flash('PDF file not found. It may still be generating.', 'warning')
        else:
            flash('Bill PDF is being generated. Please try again in a few moments.', 'info')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(request.referrer or url_for('bills_and_payments', tab='history'))

@app.route('/api/bill_pdf_status/<int:bill_id>')
def api_bill_pdf_status(bill_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT pdf_filename FROM bills_and_payments WHERE id = %s AND org_id = %s", (bill_id, session['org_id']))
        result = cur.fetchone()
        if result and result['pdf_filename']:
            return jsonify({'status': 'ready'})
        else:
            return jsonify({'status': 'processing'})
    finally:
        cur.close()
        conn.close()
    
@app.route('/api/get_accountant_projects/<int:accountant_id>')
def get_accountant_projects(accountant_id):
    """Get projects assigned to a specific accountant"""
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get projects assigned to this accountant
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN accountant_projects ap ON p.id = ap.project_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s
            ORDER BY p.project_name
        """, (accountant_id, org_id))
        
        projects = cur.fetchall()
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
