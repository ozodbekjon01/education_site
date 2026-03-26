from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import hashlib

bp = Blueprint('dashboard', __name__)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
from flask import send_file, abort
import sqlite3, io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
import qrcode

@bp.route("/certificate/<int:cert_id>/download")
def download_certificate(cert_id):
    conn = get_db()
    c = conn.cursor()
    
    cert = c.execute("""
        SELECT certificates.id, users.full_name, courses.name, certificates.date
        FROM certificates
        JOIN users ON users.id = certificates.user_id
        JOIN courses ON courses.id = certificates.course_id
        WHERE certificates.id = ?
    """, (cert_id,)).fetchone()
    
    if not cert:
        conn.close()
        abort(404, "Sertifikat topilmadi")
    
    cert_id, full_name, course_name, date = cert
    conn.close()
    
    # Static PDF shablonni ochish
    template_path = "static/certificate/certificate.pdf"
    reader = PdfReader(template_path)
    writer = PdfWriter()
    
    # Kalitlarni almashtirish uchun canvas yaratish
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    
    # {name}, {course}, {date}, {id} joylashuvi
    can.setFont("Helvetica-Bold", 24)
    can.drawString(100, 540, full_name)  # {name}
    can.setFont("Helvetica", 24)
    can.drawString(100, 460, course_name)  # {course}
    can.setFont("Helvetica", 12)
    can.drawString(110, 424, date)  # {date}
    can.drawString(330, 97, f" {cert_id}")  # {id}
    
    # QR kodi
    qr_url = f"http://library.ustoznext.uz/certificate/{cert_id}/verify"
    qr_img = qrcode.make(qr_url)
    qr_bytes = io.BytesIO()
    qr_img.save(qr_bytes, format="PNG")
    qr_bytes.seek(0)
    qr_reader = ImageReader(qr_bytes)
    can.drawImage(qr_reader, 200, 194, width=170, height=170)  # {qr} joyi
    
    can.save()
    packet.seek(0)
    
    # PDF ni birlashtirish
    overlay_pdf = PdfReader(packet)
    page = reader.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f"certificate_{cert_id}.pdf",
        mimetype="application/pdf"
    )
    
    
@bp.route("/certificate/<int:cert_id>/verify")
def verify_certificate(cert_id):
    conn = get_db()
    c = conn.cursor()
    
    cert = c.execute("""
        SELECT certificates.id, users.full_name, courses.name, certificates.date
        FROM certificates
        JOIN users ON users.id = certificates.user_id
        JOIN courses ON courses.id = certificates.course_id
        WHERE certificates.id = ?
    """, (cert_id,)).fetchone()
    
    conn.close()
    
    if not cert:
        return "Sertifikat topilmadi yoki noto‘g‘ri ID", 404
    
    cert_id, full_name, course_name, date = cert
    return f"""Sertifikat haqiqiy ✅<br>Foydalanuvchi: {full_name}<br>Kurs: {course_name}<br>Sana: {date}<br>ID: {cert_id} <br> yuklab olish <a href="/certificate/{ cert_id }/download">yuklab olish</a> """





















