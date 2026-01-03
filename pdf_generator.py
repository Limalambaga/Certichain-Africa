"""
Module pour générer des certificats PDF avec champs remplis à partir des données fournies.
"""

from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO
from datetime import datetime


def create_diploma_pdf(data=None):
    """Crée un modèle de diplôme PDF avec champs remplis.

    data (dict) keys: recipient_name, domain, mention, graduation_date,
    institution_name, cert_number, duration, blockchain_hash
    """
    if data is None:
        data = {}

    recipient = data.get('recipient_name', "[PRÉNOM NOM DE L'ETUDIANT]")
    domain = data.get('domain', '[DOMAINE/SPÉCIALITÉ]')
    mention = data.get('mention', '[MENTION]')
    grad_date = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
    institution_name = data.get('institution_name', "[NOM DE VOTRE INSTITUTION]")
    cert_num = data.get('cert_number', '[CERT-2025-XXXXX]')
    duration = data.get('duration', '[X crédits/heures]')
    blockchain_hash = data.get('blockchain_hash', '0x...')

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

    # Logo
    c.setFont("Helvetica-Bold", 48)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(2*cm, height - 2.5*cm, "🎓")

    # Institution
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(4*cm, height - 2.2*cm, institution_name)

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(4*cm, height - 2.7*cm, "Certification Officielle")

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
    text = "Pour avoir complété avec succès le programme de formation et démontré les compétences requises en"
    c.drawCentredString(width/2, y_pos, text)

    y_pos -= 0.6*cm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width/2, y_pos, domain)

    # Details
    y_pos -= 1.2*cm
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    col_x = [2.5*cm, width/2]
    c.drawString(col_x[0], y_pos, f"Date: {grad_date}")
    c.drawString(col_x[1], y_pos, f"Mention: {mention}")

    y_pos -= 0.6*cm
    c.drawString(col_x[0], y_pos, f"Certif. N°: {cert_num}")
    c.drawString(col_x[1], y_pos, f"Durée: {duration}")

    # Signatures
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    sig_x = [2*cm, width - 4*cm]
    c.drawString(sig_x[0], y_pos, "Signature Directeur")
    c.drawString(sig_x[1], y_pos, "Sceau Institution")

    y_pos -= 0.8*cm
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(sig_x[0], y_pos, sig_x[0] + 3*cm, y_pos)
    c.line(sig_x[1], y_pos, sig_x[1] + 3*cm, y_pos)

    # Blockchain hash
    c.setFont("Courier", 7)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(width - 7*cm, 0.8*cm, f"Hash: {blockchain_hash}")

    c.save()
    buffer.seek(0)
    return buffer


def create_certification_pdf(data=None):
    """Crée un modèle de certification PDF avec champs remplis."""
    if data is None:
        data = {}
    recipient = data.get('recipient_name', "[PRÉNOM NOM DU CANDIDAT]")
    domain = data.get('domain', '[DOMAINE DE COMPÉTENCE PRINCIPAL]')
    competencies = data.get('competencies', '')
    institution_name = data.get('institution_name', "[NOM DE VOTRE INSTITUTION]")
    issued_date = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
    cert_number = data.get('cert_number', 'Certificat Blockchain #2025-XXXXX')
    blockchain_hash = data.get('blockchain_hash', '0x...')

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

    # Logo and institution
    c.setFont("Helvetica-Bold", 40)
    c.setFillColorRGB(0.47, 0.29, 0.64)
    c.drawString(1*cm, height - 2*cm, "⭐")
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(3*cm, height - 1.8*cm, institution_name)

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
        while len(skills) < 6:
            skills.append('')
    else:
        skills = ["Compétence 1", "Compétence 2", "Compétence 3", "Compétence 4", "Compétence 5", "Compétence 6"]

    x_positions = [1.5*cm, 6*cm, 10.5*cm]
    row = 0
    for i, skill in enumerate(skills):
        col = i % 3
        if col == 0 and i > 0:
            row += 1
        x = x_positions[col]
        y = y_pos - (row * 0.8*cm)
        c.setFillColorRGB(0.95, 0.95, 0.98)
        c.setStrokeColorRGB(0.47, 0.29, 0.64)
        c.setLineWidth(1)
        c.rect(x, y - 0.4*cm, 4.2*cm, 0.6*cm, fill=1, stroke=1)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(x + 0.2*cm, y - 0.1*cm, skill)

    # Signatures
    y_pos = 2*cm
    c.setFont("Helvetica", 10)
    c.drawString(1.5*cm, y_pos, "Responsable Certification")
    c.drawString(width - 5*cm, y_pos, f"Date: {issued_date}")
    c.line(1.5*cm, y_pos - 0.4*cm, 6*cm, y_pos - 0.4*cm)

    # Footer
    c.setFont("Courier", 7)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(1.5*cm, 0.7*cm, cert_number)
    c.drawString(1.5*cm, 0.4*cm, f"Hash: {blockchain_hash}")

    c.save()
    buffer.seek(0)
    return buffer


def create_badge_pdf(data=None):
    """Crée un modèle de badge PDF avec champs remplis."""
    if data is None:
        data = {}
    recipient = data.get('recipient_name', "[PRÉNOM NOM DU TITULAIRE]")
    competence = data.get('domain', '[COMPÉTENCE SPÉCIFIQUE]')  # Utilise domain comme competence
    level = data.get('level', 'Intermédiaire')
    validity_months = data.get('validity', 24)
    validity = f"{validity_months} mois" if isinstance(validity_months, int) else str(validity_months)
    institution_name = data.get('institution_name', "[NOM DE VOTRE INSTITUTION]")
    issued_date = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
    blockchain_hash = data.get('blockchain_hash', '0x...')

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

    c.setFont("Helvetica-Bold", 60)
    c.setFillColorRGB(1, 1, 1)
    c.drawCentredString(badge_x, badge_y - 0.5*cm, "🎖️")

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
    details = [
        f"Délivré à: {recipient}",
        f"Date: {issued_date}",
        f"Validité: {validity}",
        f"Niveau: {level}"
    ]
    for i, detail in enumerate(details):
        c.drawString(1.5*cm, y_pos - (i * 0.5*cm), detail)

    # Blockchain area
    y_pos -= 2.5*cm
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.4, 0.49, 0.92)
    c.setFillColorRGB(0.95, 0.95, 0.98)
    c.rect(1.5*cm, y_pos - 1.2*cm, width - 3*cm, 1.2*cm, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(1.8*cm, y_pos - 0.3*cm, "🔐 Vérifiable sur Blockchain")
    c.setFont("Courier", 8)
    c.setFillColorRGB(0.4, 0.49, 0.92)
    c.drawString(1.8*cm, y_pos - 0.7*cm, blockchain_hash)

    c.save()
    buffer.seek(0)
    return buffer
