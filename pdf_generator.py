"""
PDF certificate generator — ReportLab + QR code verification stamp.
"""

from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime
import qrcode
import qrcode.image.pil


def _make_qr(url: str) -> ImageReader:
    """Return a ReportLab-compatible ImageReader for a QR code pointing to url."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def _draw_verification_stamp(c, url: str, blockchain_hash: str, cert_num: str,
                              x: float, y: float, qr_size: float = 2.2*cm):
    """Draw QR code + verification text block at (x, y) — bottom-left anchor."""
    # QR code
    if url and url != 'N/A':
        qr_img = _make_qr(url)
        c.drawImage(qr_img, x, y, width=qr_size, height=qr_size, mask='auto')

    # Text beside QR
    tx = x + qr_size + 0.3*cm
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(tx, y + qr_size - 0.35*cm, "VÉRIFICATION")
    c.setFont("Helvetica", 6.5)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(tx, y + qr_size - 0.75*cm, "Scannez pour authentifier")
    c.setFont("Courier", 6)
    c.setFillColorRGB(0.35, 0.45, 0.85)
    hash_display = (blockchain_hash[:36] + '…') if len(blockchain_hash) > 36 else blockchain_hash
    c.drawString(tx, y + qr_size - 1.1*cm, f"Hash: {hash_display}")
    c.drawString(tx, y + qr_size - 1.45*cm, f"N°: {cert_num}")


# ─────────────────────────────────────────────────────────────────────────────
# DIPLÔME
# ─────────────────────────────────────────────────────────────────────────────

def create_diploma_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',    "[PRÉNOM NOM DE L'ETUDIANT]")
    domain           = data.get('domain',            '[DOMAINE/SPÉCIALITÉ]')
    mention          = data.get('mention',           '[MENTION]')
    grad_date        = data.get('graduation_date',   datetime.now().strftime('%d/%m/%Y'))
    institution_name = data.get('institution_name',  "[NOM DE VOTRE INSTITUTION]")
    cert_num         = data.get('cert_number',       '[CERT-2025-XXXXX]')
    duration         = data.get('duration',          '[X crédits/heures]')
    blockchain_hash  = data.get('blockchain_hash',   'N/A')
    verify_url       = data.get('verify_url',        '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Background
    c.setFillColorRGB(0.98, 0.98, 0.98)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Top bar
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.rect(0, height - 1*cm, width, 1*cm, fill=1, stroke=0)

    # Border
    c.setLineWidth(3)
    c.setStrokeColorRGB(0.4, 0.49, 0.92)
    c.rect(0.5*cm, 0.5*cm, width - 1*cm, height - 1*cm)

    # Institution
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(2*cm, height - 2.2*cm, institution_name)
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(2*cm, height - 2.7*cm, "Certification Officielle")

    # Main title
    c.setFont("Helvetica-Bold", 32)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawCentredString(width/2, height - 5*cm, "DIPLÔME")
    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width/2, height - 5.7*cm, "Certificat d'Accomplissement")

    # Recipient
    y_pos = height - 7*cm
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width/2, y_pos, "Décerné à")

    y_pos -= 0.8*cm
    c.setFont("Helvetica-Bold", 28)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, y_pos, recipient)

    c.setLineWidth(2)
    c.setStrokeColorRGB(0.4, 0.49, 0.92)
    c.line(width/2 - 3*cm, y_pos - 0.5*cm, width/2 + 3*cm, y_pos - 0.5*cm)

    y_pos -= 1.5*cm
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width/2, y_pos,
        "Pour avoir complété avec succès le programme de formation en")
    y_pos -= 0.6*cm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, y_pos, domain)

    # Details
    y_pos -= 1.2*cm
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(2.5*cm, y_pos, f"Date: {grad_date}")
    c.drawString(width/2,  y_pos, f"Mention: {mention}")
    y_pos -= 0.6*cm
    c.drawString(2.5*cm, y_pos, f"Certif. N°: {cert_num}")
    c.drawString(width/2,  y_pos, f"Durée: {duration}")

    # Signatures
    y_pos -= 1.5*cm
    sig_x = [2*cm, width - 4*cm]
    c.setFont("Helvetica", 10)
    c.drawString(sig_x[0], y_pos, "Signature Directeur")
    c.drawString(sig_x[1], y_pos, "Sceau Institution")
    y_pos -= 0.8*cm
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(sig_x[0], y_pos, sig_x[0] + 3*cm, y_pos)
    c.line(sig_x[1], y_pos, sig_x[1] + 3*cm, y_pos)

    # QR verification stamp (bottom-right)
    _draw_verification_stamp(c, verify_url, blockchain_hash, cert_num,
                             x=width - 8*cm, y=0.6*cm, qr_size=2.2*cm)

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────────────────────
# CERTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def create_certification_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',   "[PRÉNOM NOM DU CANDIDAT]")
    domain           = data.get('domain',           '[DOMAINE DE COMPÉTENCE]')
    competencies     = data.get('competencies',     '')
    institution_name = data.get('institution_name', "[NOM DE VOTRE INSTITUTION]")
    issued_date      = data.get('graduation_date',  datetime.now().strftime('%d/%m/%Y'))
    cert_number      = data.get('cert_number',      'CERT-2025-XXXXX')
    blockchain_hash  = data.get('blockchain_hash',  'N/A')
    verify_url       = data.get('verify_url',       '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Background and top bar
    c.setFillColorRGB(0.98, 0.98, 0.98)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColorRGB(0.47, 0.29, 0.64)
    c.rect(0, height - 0.8*cm, width, 0.8*cm, fill=1, stroke=0)
    c.setLineWidth(3)
    c.setStrokeColorRGB(0.47, 0.29, 0.64)
    c.rect(0.5*cm, 0.5*cm, width - 1*cm, height - 1*cm)

    # Institution
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(1*cm, height - 1.8*cm, institution_name)

    # Title
    c.setFont("Helvetica-Bold", 28)
    c.setFillColorRGB(0.47, 0.29, 0.64)
    c.drawCentredString(width/2, height - 4*cm, "CERTIFICATION PROFESSIONNELLE")

    # Recipient
    y_pos = height - 5.2*cm
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width/2, y_pos, "Décerné à")
    y_pos -= 0.8*cm
    c.setFont("Helvetica-Bold", 22)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, y_pos, recipient)
    c.setLineWidth(2)
    c.setStrokeColorRGB(0.47, 0.29, 0.64)
    c.line(width/2 - 2.5*cm, y_pos - 0.4*cm, width/2 + 2.5*cm, y_pos - 0.4*cm)

    # Domain
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, y_pos, "Pour avoir démontré une maîtrise en :")
    y_pos -= 0.5*cm
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width/2, y_pos, domain)

    # Competencies grid
    y_pos -= 1*cm
    c.setFont("Helvetica", 9)
    if competencies:
        skills = [s.strip() for s in competencies.split(',') if s.strip()][:6]
    else:
        skills = []
    while len(skills) < 6:
        skills.append('')

    x_positions = [1.5*cm, 6*cm, 10.5*cm]
    for i, skill in enumerate(skills):
        col = i % 3
        row = i // 3
        x = x_positions[col]
        y = y_pos - (row * 0.8*cm)
        c.setFillColorRGB(0.95, 0.95, 0.98)
        c.setStrokeColorRGB(0.47, 0.29, 0.64)
        c.setLineWidth(1)
        c.rect(x, y - 0.4*cm, 4.2*cm, 0.6*cm, fill=1, stroke=1)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(x + 0.2*cm, y - 0.1*cm, skill)

    # Signature line
    y_pos = 4*cm
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(1.5*cm, y_pos, "Responsable Certification")
    c.drawString(width - 5*cm, y_pos, f"Date: {issued_date}")
    c.line(1.5*cm, y_pos - 0.4*cm, 6*cm, y_pos - 0.4*cm)

    # QR verification stamp (bottom-right)
    _draw_verification_stamp(c, verify_url, blockchain_hash, cert_number,
                             x=width - 8*cm, y=0.8*cm, qr_size=2.2*cm)

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────────────────────
# BADGE
# ─────────────────────────────────────────────────────────────────────────────

def create_badge_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',   "[PRÉNOM NOM DU TITULAIRE]")
    competence       = data.get('domain',           '[COMPÉTENCE SPÉCIFIQUE]')
    level            = data.get('level',            'Intermédiaire')
    validity_months  = data.get('validity',         24)
    validity         = f"{validity_months} mois" if isinstance(validity_months, int) else str(validity_months)
    institution_name = data.get('institution_name', "[NOM DE VOTRE INSTITUTION]")
    issued_date      = data.get('graduation_date',  datetime.now().strftime('%d/%m/%Y'))
    blockchain_hash  = data.get('blockchain_hash',  'N/A')
    cert_number      = data.get('cert_number',      'BADGE-2025-XXXXX')
    verify_url       = data.get('verify_url',       '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Background
    c.setFillColorRGB(0.98, 0.98, 0.98)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Badge circle
    badge_x = width / 2
    badge_y = height - 4*cm
    badge_radius = 3*cm
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.circle(badge_x, badge_y, badge_radius, fill=1, stroke=0)
    c.setLineWidth(2)
    c.setStrokeColorRGB(0.4, 0.49, 0.92)
    c.circle(badge_x, badge_y, badge_radius, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(1, 1, 1)
    c.drawCentredString(badge_x, badge_y - 0.3*cm, "BADGE")

    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, height - 7.5*cm, competence)
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width/2, height - 8*cm, f"Délivré par {institution_name}")

    # Details
    y_pos = height - 9*cm
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    for detail in [f"Délivré à: {recipient}", f"Date: {issued_date}",
                   f"Validité: {validity}", f"Niveau: {level}"]:
        c.drawString(1.5*cm, y_pos, detail)
        y_pos -= 0.55*cm

    # Blockchain box
    y_pos -= 0.8*cm
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.4, 0.49, 0.92)
    c.setFillColorRGB(0.95, 0.95, 0.98)
    c.rect(1.5*cm, y_pos - 0.8*cm, width - 3*cm, 0.9*cm, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(1.8*cm, y_pos - 0.2*cm, "Vérifiable sur Blockchain")
    c.setFont("Courier", 7)
    hash_display = (blockchain_hash[:50] + '…') if len(blockchain_hash) > 50 else blockchain_hash
    c.drawString(1.8*cm, y_pos - 0.55*cm, hash_display)

    # QR verification stamp (bottom-right)
    _draw_verification_stamp(c, verify_url, blockchain_hash, cert_number,
                             x=width - 8*cm, y=0.8*cm, qr_size=2.2*cm)

    c.save()
    buffer.seek(0)
    return buffer
