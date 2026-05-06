"""
Professional certificate PDF generator — inspired by Leaston University design.
"""

from reportlab.lib.pagesizes import landscape, A4, portrait
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, white, black
from io import BytesIO
from datetime import datetime
import qrcode
import qrcode.image.pil
import math


# ── Brand colours ────────────────────────────────────────────────────────────
NAVY        = HexColor('#0A1E52')
NAVY_LIGHT  = HexColor('#1A3A7A')
GOLD        = HexColor('#C9A84C')
GOLD_LIGHT  = HexColor('#E8D48B')
TEAL        = HexColor('#2DD4BF')
SILVER      = HexColor('#E2E8F0')
DARK_BG     = HexColor('#0B1631')
DARK_MID    = HexColor('#0F2045')
TEXT_DARK   = HexColor('#1A202C')
TEXT_MID    = HexColor('#4A5568')
TEXT_LIGHT  = HexColor('#94A3B8')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_qr(url: str) -> ImageReader:
    qr = qrcode.QRCode(version=1, box_size=5, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def _partial_circle(c, cx, cy, r, color, start_deg=0, span_deg=360, fill=True):
    """Draw a full or partial circle using bezier approximation."""
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)
    p = c.beginPath()
    p.circle(cx, cy, r)
    c.drawPath(p, fill=1 if fill else 0, stroke=0)
    c.restoreState()


def _draw_dashed_line(c, x1, y1, x2, y2, color, width=0.5, dash=(4, 4)):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setDash(*dash)
    c.line(x1, y1, x2, y2)
    c.restoreState()


def _gold_line(c, x, y, w, thick=1.2):
    c.setStrokeColor(GOLD)
    c.setLineWidth(thick)
    c.line(x, y, x + w, y)


def _draw_stars(c, width, height, color, count=40, seed=42):
    """Scatter small dot 'stars' on a dark background."""
    import random
    random.seed(seed)
    c.setFillColor(color)
    for _ in range(count):
        x = random.uniform(0.3*cm, width - 0.3*cm)
        y = random.uniform(0.3*cm, height - 0.3*cm)
        r = random.uniform(0.5, 2.0)
        c.circle(x, y, r, fill=1, stroke=0)


def _draw_seal(c, cx, cy, radius=1.4*cm, label="CERTIFIÉ"):
    """Draw a decorative circular seal/stamp."""
    # Outer ring
    c.setStrokeColor(GOLD)
    c.setFillColor(HexColor('#FFF8E7'))
    c.setLineWidth(2)
    c.circle(cx, cy, radius, fill=1, stroke=1)
    # Inner ring
    c.setFillColor(HexColor('#FFFDF0'))
    c.circle(cx, cy, radius * 0.78, fill=1, stroke=1)
    # Text
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(cx, cy + 0.18*cm, label)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(cx, cy - 0.05*cm, "CERTICHAIN")
    c.drawCentredString(cx, cy - 0.28*cm, "AFRICA")


def _qr_stamp(c, url, cert_num, x, y, size=1.9*cm):
    if not url or url == 'N/A':
        return
    qr = _make_qr(url)
    c.drawImage(qr, x, y, width=size, height=size, mask='auto')
    c.setFont("Helvetica", 5.2)
    c.setFillColor(TEXT_LIGHT)
    c.drawCentredString(x + size/2, y - 0.25*cm, "Scan to verify")
    c.setFont("Courier", 4.8)
    c.drawCentredString(x + size/2, y - 0.42*cm, cert_num[:20])


# ─────────────────────────────────────────────────────────────────────────────
# DIPLÔME  — style Leaston blanc/épuré
# ─────────────────────────────────────────────────────────────────────────────

def create_diploma_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',    "Jean-Baptiste Kouassi")
    domain           = data.get('domain',            "Communication & Management")
    mention          = data.get('mention',           '')
    grad_date        = data.get('graduation_date',   datetime.now().strftime('%d %B %Y'))
    institution_name = data.get('institution_name',  "VOTRE INSTITUTION")
    cert_num         = data.get('cert_number',       'CERT-2025-00001')
    duration         = data.get('duration',          '')
    blockchain_hash  = data.get('blockchain_hash',  'N/A')
    verify_url       = data.get('verify_url',        '')
    description      = data.get('description',       '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    W, H = landscape(A4)

    # ── Background ────────────────────────────────────────────────────────────
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Decorative circles (corners) ──────────────────────────────────────────
    # Top-left teal circle (partial, clipped by corner)
    c.saveState()
    c.setFillColor(HexColor('#E0F7F4'))
    c.circle(-1.5*cm, H + 1.5*cm, 4.5*cm, fill=1, stroke=0)
    c.restoreState()

    c.saveState()
    c.setFillColor(TEAL)
    c.circle(-1.8*cm, H + 1.8*cm, 3*cm, fill=1, stroke=0)
    c.restoreState()

    # Bottom-right navy circle
    c.saveState()
    c.setFillColor(HexColor('#EBF0FA'))
    c.circle(W + 1.5*cm, -1.5*cm, 4.5*cm, fill=1, stroke=0)
    c.restoreState()

    c.saveState()
    c.setFillColor(NAVY)
    c.circle(W + 1.8*cm, -1.8*cm, 3*cm, fill=1, stroke=0)
    c.restoreState()

    # Top-right small accent
    c.saveState()
    c.setFillColor(HexColor('#FFF3CD'))
    c.circle(W + 0.5*cm, H - 2*cm, 2.2*cm, fill=1, stroke=0)
    c.restoreState()

    # ── Outer border ──────────────────────────────────────────────────────────
    c.setStrokeColor(SILVER)
    c.setLineWidth(1)
    c.rect(0.8*cm, 0.8*cm, W - 1.6*cm, H - 1.6*cm, fill=0, stroke=1)

    # ── Institution name ──────────────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 20)
    inst_upper = institution_name.upper()
    c.drawCentredString(W/2, H - 2.2*cm, inst_upper)

    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    inst_w = min(len(inst_upper) * 11, W * 0.5)
    c.line(W/2 - inst_w/2, H - 2.6*cm, W/2 + inst_w/2, H - 2.6*cm)

    c.setFillColor(TEXT_MID)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W/2, H - 3.1*cm,
        f"L'École Supérieure et le Département Executive Education décernent le présent certificat à :")

    # ── Divider ───────────────────────────────────────────────────────────────
    _gold_line(c, 3*cm, H - 3.55*cm, W - 6*cm, thick=0.7)

    # ── Recipient ─────────────────────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(W/2, H - 5.0*cm, recipient)

    # Underline recipient
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)
    name_w = min(len(recipient) * 16, W * 0.55)
    c.line(W/2 - name_w/2, H - 5.45*cm, W/2 + name_w/2, H - 5.45*cm)

    c.setFillColor(TEXT_MID)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H - 6.05*cm, "pour sa participation au programme")

    # ── Domain / programme ────────────────────────────────────────────────────
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 16)
    domain_text = f'"{domain}"'
    c.drawCentredString(W/2, H - 7.0*cm, domain_text)

    # Duration / mention
    if duration and duration != 'N/A':
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W/2, H - 7.7*cm,
            f"ayant validé avec succès une formation de {duration}.")
    elif mention:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W/2, H - 7.7*cm,
            f"avec la mention  {mention}")

    if description:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 9)
        c.drawCentredString(W/2, H - 8.3*cm, description[:90])

    # ── Date ──────────────────────────────────────────────────────────────────
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W/2, H - 9.0*cm, f"Délivré le {grad_date}")

    # ── Signatures ────────────────────────────────────────────────────────────
    sig_y = 3.6*cm
    sig_left  = 3.5*cm
    sig_right = W - 3.5*cm - 4*cm

    # Left signature block
    c.setStrokeColor(HexColor('#CBD5E0'))
    c.setLineWidth(0.8)
    c.line(sig_left, sig_y + 0.8*cm, sig_left + 4*cm, sig_y + 0.8*cm)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(sig_left, sig_y + 0.35*cm, "Dr. Directeur Général")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(TEXT_MID)
    c.drawString(sig_left, sig_y + 0.05*cm, institution_name[:28])

    # Right signature block
    c.setStrokeColor(HexColor('#CBD5E0'))
    c.line(sig_right, sig_y + 0.8*cm, sig_right + 4*cm, sig_y + 0.8*cm)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(sig_right, sig_y + 0.35*cm, "Directeur Académique")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(TEXT_MID)
    c.drawString(sig_right, sig_y + 0.05*cm, "Executive Education")

    # ── Seal (center) ─────────────────────────────────────────────────────────
    _draw_seal(c, W/2, sig_y + 0.9*cm, radius=1.3*cm)

    # ── QR code (bottom right) ────────────────────────────────────────────────
    _qr_stamp(c, verify_url, cert_num, W - 4.2*cm, 0.9*cm, size=2*cm)

    # ── Cert number (bottom left) ─────────────────────────────────────────────
    c.setFont("Courier", 6.5)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(1.2*cm, 0.9*cm, cert_num)
    c.drawString(1.2*cm, 0.6*cm, f"Hash: {blockchain_hash[:40]}")

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────────────────────
# CERTIFICATION  — style dark blue "Certificate of Achievement"
# ─────────────────────────────────────────────────────────────────────────────

def create_certification_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',   "Jane Doe Smith")
    domain           = data.get('domain',           "Digital Innovation & Strategy")
    competencies     = data.get('competencies',     '')
    institution_name = data.get('institution_name', "VOTRE INSTITUTION")
    issued_date      = data.get('graduation_date',  datetime.now().strftime('%d %B %Y'))
    cert_number      = data.get('cert_number',      'CERT-2025-00001')
    blockchain_hash  = data.get('blockchain_hash',  'N/A')
    verify_url       = data.get('verify_url',       '')
    description      = data.get('description',      '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=portrait(A4))
    W, H = portrait(A4)

    # ── Dark background ───────────────────────────────────────────────────────
    c.setFillColor(DARK_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Mid panel
    c.setFillColor(DARK_MID)
    c.rect(0, H * 0.18, W, H * 0.64, fill=1, stroke=0)

    # ── Stars ─────────────────────────────────────────────────────────────────
    _draw_stars(c, W, H, HexColor('#FFFFFF'), count=55, seed=77)
    _draw_stars(c, W, H, HexColor('#C9A84C'), count=15, seed=13)

    # ── Decorative side circles ───────────────────────────────────────────────
    c.saveState()
    c.setFillColor(HexColor('#0D2860'))
    c.circle(-2*cm, H * 0.5, 4*cm, fill=1, stroke=0)
    c.circle(W + 2*cm, H * 0.5, 4*cm, fill=1, stroke=0)
    c.restoreState()

    # ── Gold top & bottom bars ────────────────────────────────────────────────
    c.setFillColor(GOLD)
    c.rect(0, H - 0.45*cm, W, 0.45*cm, fill=1, stroke=0)
    c.rect(0, 0, W, 0.45*cm, fill=1, stroke=0)

    # ── CERTIFICATE header ────────────────────────────────────────────────────
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(W/2, H - 2.5*cm, "CERTIFICATE")

    c.setFillColor(HexColor('#B0BEC5'))
    c.setFont("Helvetica", 13)
    c._charSpace = 4
    c.drawCentredString(W/2, H - 3.3*cm, "OF ACHIEVEMENT")

    # Gold divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(W/2 - 4*cm, H - 3.8*cm, W/2 + 4*cm, H - 3.8*cm)

    # ── Awarded text ──────────────────────────────────────────────────────────
    c.setFillColor(HexColor('#B0BEC5'))
    c.setFont("Helvetica", 9)
    c._charSpace = 2
    c.drawCentredString(W/2, H - 4.6*cm, "THIS CERTIFICATE IS AWARDED TO")

    # ── Institution name ──────────────────────────────────────────────────────
    c.setFillColor(HexColor('#7F9EC5'))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W/2, H - 5.1*cm, institution_name.upper())

    # ── Recipient name ────────────────────────────────────────────────────────
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(W/2, H - 6.1*cm, recipient)

    # Gold underline
    name_w = min(len(recipient) * 14, W * 0.7)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(W/2 - name_w/2, H - 6.5*cm, W/2 + name_w/2, H - 6.5*cm)

    # ── Description paragraph ─────────────────────────────────────────────────
    base_desc = (description or
        f"Pour avoir démontré une maîtrise exceptionnelle "
        f"et complété avec succès le programme certifiant en :")

    c.setFillColor(HexColor('#B0C4DE'))
    c.setFont("Helvetica", 8.5)
    words = base_desc.split()
    lines_out, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 8.5) < W - 5*cm:
            line = test
        else:
            lines_out.append(line)
            line = w
    if line:
        lines_out.append(line)
    ty = H - 7.2*cm
    for ln in lines_out[:3]:
        c.drawCentredString(W/2, ty, ln)
        ty -= 0.48*cm

    # ── Domain / programme ────────────────────────────────────────────────────
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, ty - 0.5*cm, f'"{domain}"')
    ty -= 1.3*cm

    # ── Competencies pills ────────────────────────────────────────────────────
    if competencies:
        skills = [s.strip() for s in competencies.split(',') if s.strip()][:6]
        pill_y = ty - 0.3*cm
        total_pills = len(skills)
        pill_w = (W - 4*cm) / min(total_pills, 3)
        for i, skill in enumerate(skills[:6]):
            col = i % 3
            row = i // 3
            px = 2*cm + col * pill_w
            py = pill_y - row * 0.75*cm
            c.setFillColor(HexColor('#1A3A7A'))
            c.setStrokeColor(GOLD)
            c.setLineWidth(0.5)
            c.roundRect(px, py - 0.25*cm, pill_w - 0.3*cm, 0.5*cm, 4, fill=1, stroke=1)
            c.setFillColor(white)
            c.setFont("Helvetica", 7)
            c.drawCentredString(px + (pill_w - 0.3*cm)/2, py - 0.07*cm, skill[:22])

    # ── Date & location ───────────────────────────────────────────────────────
    date_y = H * 0.27
    c.setFillColor(HexColor('#B0BEC5'))
    c.setFont("Helvetica", 9)
    c._charSpace = 1
    c.drawCentredString(W/2, date_y, f"DÉLIVRÉ LE  {issued_date.upper()}")

    # ── Institution name ──────────────────────────────────────────────────────
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W/2, date_y - 0.7*cm, f"· {institution_name.upper()} ·")

    # Gold dots separator
    c.setFillColor(GOLD)
    c.circle(W/2 - 1.2*cm, date_y - 0.72*cm + 0.1*cm, 2, fill=1, stroke=0)
    c.circle(W/2 + 1.2*cm, date_y - 0.72*cm + 0.1*cm, 2, fill=1, stroke=0)

    # ── Signature blocks ──────────────────────────────────────────────────────
    sig_y = H * 0.11
    sig_lx = 2.5*cm
    sig_rx = W - 2.5*cm - 3.5*cm

    for sx in [sig_lx, sig_rx]:
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.8)
        c.line(sx, sig_y + 0.6*cm, sx + 3.5*cm, sig_y + 0.6*cm)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(sig_lx, sig_y + 0.25*cm, "Directeur Général")
    c.drawString(sig_rx, sig_y + 0.25*cm, "Doyen Académique")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(HexColor('#7F8EA3'))
    c.drawString(sig_lx, sig_y + 0.02*cm, institution_name[:22])
    c.drawString(sig_rx, sig_y + 0.02*cm, "Executive Education")

    # ── "Class of" badge ──────────────────────────────────────────────────────
    badge_cx = W/2
    badge_cy = sig_y + 0.9*cm
    badge_r  = 1.0*cm
    c.setFillColor(GOLD)
    c.circle(badge_cx, badge_cy, badge_r, fill=1, stroke=0)
    c.setFillColor(DARK_BG)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(badge_cx, badge_cy + 0.25*cm, "Class of")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(badge_cx, badge_cy - 0.15*cm, str(datetime.now().year))

    # ── QR code ───────────────────────────────────────────────────────────────
    if verify_url and verify_url != 'N/A':
        qr = _make_qr(verify_url)
        c.drawImage(qr, W - 2.6*cm, 0.55*cm, width=1.8*cm, height=1.8*cm, mask='auto')

    # ── Cert number ───────────────────────────────────────────────────────────
    c.setFont("Courier", 5.5)
    c.setFillColor(HexColor('#4A5568'))
    c.drawString(0.8*cm, 0.6*cm, cert_number)
    c.drawString(0.8*cm, 0.35*cm, f"Hash: {blockchain_hash[:38]}")

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────────────────────
# BADGE  — style premium blanc/or avec médaillon
# ─────────────────────────────────────────────────────────────────────────────

def create_badge_pdf(data=None):
    if data is None:
        data = {}

    recipient        = data.get('recipient_name',   "Prénom Nom")
    competence       = data.get('domain',           "Excellence Professionnelle")
    level            = data.get('level',            'Expert')
    validity_months  = data.get('validity',         24)
    validity         = f"{validity_months} mois" if str(validity_months).isdigit() else str(validity_months)
    institution_name = data.get('institution_name', "VOTRE INSTITUTION")
    issued_date      = data.get('graduation_date',  datetime.now().strftime('%d %B %Y'))
    blockchain_hash  = data.get('blockchain_hash',  'N/A')
    cert_number      = data.get('cert_number',      'BADGE-2025-00001')
    verify_url       = data.get('verify_url',       '')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=portrait(A4))
    W, H = portrait(A4)

    # ── Background: white with navy top band ──────────────────────────────────
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Navy header band
    c.setFillColor(NAVY)
    c.rect(0, H - 5.5*cm, W, 5.5*cm, fill=1, stroke=0)

    # Subtle dot pattern on navy band
    c.setFillColor(HexColor('#0D2560'))
    for row in range(6):
        for col in range(18):
            c.circle(col * 1.2*cm + 0.3*cm, H - 5.2*cm + row * 0.9*cm, 1.5, fill=1, stroke=0)

    # Gold accent line below band
    c.setFillColor(GOLD)
    c.rect(0, H - 5.5*cm, W, 0.3*cm, fill=1, stroke=0)

    # ── Institution name in header ────────────────────────────────────────────
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W/2, H - 1.8*cm, institution_name.upper())
    c.setFont("Helvetica", 8)
    c.setFillColor(GOLD_LIGHT)
    c._charSpace = 3
    c.drawCentredString(W/2, H - 2.3*cm, "CERTIFICAT NUMÉRIQUE")

    # ── Medallion badge circle ────────────────────────────────────────────────
    med_cx = W/2
    med_cy = H - 5.5*cm   # sits on the gold line

    # Outer glow ring
    c.setFillColor(HexColor('#FFF3CD'))
    c.circle(med_cx, med_cy, 2.6*cm, fill=1, stroke=0)
    # Gold ring
    c.setFillColor(GOLD)
    c.circle(med_cx, med_cy, 2.3*cm, fill=1, stroke=0)
    # White ring
    c.setFillColor(white)
    c.circle(med_cx, med_cy, 1.95*cm, fill=1, stroke=0)
    # Navy inner
    c.setFillColor(NAVY)
    c.circle(med_cx, med_cy, 1.6*cm, fill=1, stroke=0)

    # Star / badge icon inside
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(med_cx, med_cy + 0.4*cm, "★")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(white)
    c.drawCentredString(med_cx, med_cy + 0.05*cm, "BADGE")
    c.setFont("Helvetica", 6)
    c.drawCentredString(med_cx, med_cy - 0.28*cm, level.upper())

    # ── Body content ──────────────────────────────────────────────────────────
    body_top = med_cy - 3.2*cm

    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, body_top, "Ce badge est décerné à")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W/2, body_top - 1.1*cm, recipient)

    # Underline
    name_w = min(len(recipient) * 12, W * 0.7)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(W/2 - name_w/2, body_top - 1.55*cm, W/2 + name_w/2, body_top - 1.55*cm)

    c.setFillColor(TEXT_MID)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, body_top - 2.2*cm, "pour excellence démontrée dans")

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, body_top - 3.0*cm, competence)

    # ── Info grid ─────────────────────────────────────────────────────────────
    grid_y = body_top - 3.5*cm
    c.setStrokeColor(SILVER)
    c.setFillColor(HexColor('#F7F9FC'))
    c.setLineWidth(0.7)
    box_w = (W - 4*cm) / 3
    labels = ["Niveau", "Validité", "Délivré le"]
    values = [level, validity, issued_date]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        bx = 2*cm + i * box_w
        c.roundRect(bx, grid_y - 1*cm, box_w - 0.3*cm, 1.1*cm, 6, fill=1, stroke=1)
        c.setFillColor(TEXT_LIGHT)
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + (box_w - 0.3*cm)/2, grid_y - 0.2*cm, lbl.upper())
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(bx + (box_w - 0.3*cm)/2, grid_y - 0.6*cm, val)

    # ── Blockchain verification box ───────────────────────────────────────────
    box_y = grid_y - 2.2*cm
    c.setFillColor(HexColor('#EFF6FF'))
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(2*cm, box_y - 1*cm, W - 4*cm, 1.15*cm, 6, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2.4*cm, box_y - 0.3*cm, "Vérifiable sur Blockchain Polygon")
    c.setFont("Courier", 6.5)
    c.setFillColor(TEXT_MID)
    hash_display = (blockchain_hash[:52] + '…') if len(blockchain_hash) > 52 else blockchain_hash
    c.drawString(2.4*cm, box_y - 0.6*cm, hash_display)

    # ── Signature & Seal ──────────────────────────────────────────────────────
    sig_y = box_y - 2.3*cm
    c.setStrokeColor(HexColor('#CBD5E0'))
    c.setLineWidth(0.8)
    c.line(2*cm, sig_y + 0.8*cm, 5.5*cm, sig_y + 0.8*cm)
    c.line(W - 5.5*cm, sig_y + 0.8*cm, W - 2*cm, sig_y + 0.8*cm)

    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2*cm, sig_y + 0.3*cm, "Directeur Général")
    c.drawString(W - 5.5*cm, sig_y + 0.3*cm, "Responsable Formation")
    c.setFont("Helvetica", 7)
    c.setFillColor(TEXT_MID)
    c.drawString(2*cm, sig_y + 0.02*cm, institution_name[:22])
    c.drawString(W - 5.5*cm, sig_y + 0.02*cm, "Département Pédagogique")

    _draw_seal(c, W/2, sig_y + 0.75*cm, radius=1.1*cm, label="VALIDÉ")

    # ── QR code ───────────────────────────────────────────────────────────────
    _qr_stamp(c, verify_url, cert_number, W - 3.5*cm, 0.7*cm, size=1.9*cm)

    # ── Cert number ───────────────────────────────────────────────────────────
    c.setFont("Courier", 6)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(1*cm, 0.8*cm, cert_number)
    c.drawString(1*cm, 0.55*cm, f"Hash: {blockchain_hash[:38]}")

    c.save()
    buffer.seek(0)
    return buffer
