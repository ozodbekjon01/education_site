from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, abort
import sqlite3
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
import qrcode

bp = Blueprint("dashboard", __name__)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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

    display_name = full_name.strip().title() if full_name else ""
    display_date = date.split(" ")[0] if date and " " in date else (date or "")

    template_path = "static/certificate/certificate.pdf"
    reader = PdfReader(template_path)
    writer = PdfWriter()

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=landscape(A4))

    # {name}, {course}, {date}, {id} joylashuvi
    can.setFont("Helvetica-Bold", 36)
    can.drawString(60, 242, display_name)
    can.setFont("Helvetica", 28)
    can.drawString(60, 362, course_name)
    can.setFont("Helvetica", 13)
    can.drawString(650, 526, display_date)
    can.drawString(175, 74, f"{cert_id}")

    # QR kodi (rasmiy domen bilan va yashil ramka markazida)
    qr_url = f"https://digitalplatform.uz/certificate/{cert_id}/verify"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_bytes = io.BytesIO()
    qr_img.save(qr_bytes, format="PNG")
    qr_bytes.seek(0)
    qr_reader = ImageReader(qr_bytes)

    # Yashil ramka: x=396.3, y=29.23, w=184.25, h=184.25 -> markaz: x=403.4, y=36.35, w=170, h=170
    can.drawImage(qr_reader, 396.5, 36.35, width=170, height=170)

    can.save()
    packet.seek(0)

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


@bp.route("/certificate/verify", methods=["GET", "POST"])
def verify_certificate_search():
    cert_id_raw = request.values.get("cert_id", "").strip()
    if cert_id_raw:
        clean_id = "".join(ch for ch in cert_id_raw if ch.isdigit())
        if clean_id:
            return redirect(url_for("dashboard.verify_certificate", cert_id=int(clean_id)))
        return render_template(
            "verify_certificate.html",
            cert=None,
            searched_id=cert_id_raw,
            error="Sertifikat ID raqami faqat sonlardan iborat bo‘lishi kerak."
        ), 400

    return render_template(
        "verify_certificate.html",
        cert=None,
        searched_id=None,
        error=None
    )


@bp.route("/certificate/<int:cert_id>/verify")
def verify_certificate(cert_id):
    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
        SELECT certificates.id, users.full_name, courses.name, certificates.date
        FROM certificates
        JOIN users ON users.id = certificates.user_id
        JOIN courses ON courses.id = certificates.course_id
        WHERE certificates.id = ?
    """, (cert_id,)).fetchone()

    conn.close()

    if not row:
        return render_template(
            "verify_certificate.html",
            cert=None,
            searched_id=cert_id,
            error=f"#{cert_id} raqamli sertifikat ma’lumotlar bazasidan topilmadi."
        ), 404

    import base64
    c_id, full_name, course_name, date = row
    verify_url = f"https://digitalplatform.uz/certificate/{c_id}/verify"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    cert_data = {
        "id": c_id,
        "full_name": full_name.strip().title() if full_name else "",
        "course_name": course_name,
        "date": date,
        "short_date": date.split(" ")[0] if date and " " in date else (date or ""),
        "verify_url": verify_url,
        "qr_base64": qr_b64
    }

    return render_template(
        "verify_certificate.html",
        cert=cert_data,
        searched_id=c_id,
        error=None
    )