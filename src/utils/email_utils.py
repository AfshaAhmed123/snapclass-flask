import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PARENT_EMAILS = {
    "Aditya Kumar":   "parent.aditya@gmail.com",
    "Sneha Patel":    "parent.sneha@gmail.com",
    "Rahul Singh":    "parent.rahul@gmail.com",
    "Priya Nair":     "parent.priya@gmail.com",
    "Vikram Joshi":   "parent.vikram@gmail.com",
    "Meera Reddy":    "parent.meera@gmail.com",
    "Aryan Gupta":    "parent.aryan@gmail.com",
    "Divya Menon":    "parent.divya@gmail.com",
    "Karan Malhotra": "parent.karan@gmail.com",
    "Anjali Sharma":  "parent.anjali@gmail.com",
}

def send_absence_email(student_name, subject_name):
    parent_email = PARENT_EMAILS.get(
        student_name,
        f"parent_{student_name.lower().replace(' ', '_')}@gmail.com"
    )

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    from_email = os.environ.get("FROM_EMAIL")
    smtp_port  = int(os.environ.get("SMTP_PORT", 465))

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
      <div style="background:#5865F2;padding:24px 32px;">
        <h2 style="color:white;margin:0;">SnapClass AI — Absence Alert</h2>
      </div>
      <div style="padding:32px;">
        <p>Dear Parent / Guardian,</p>
        <p style="color:#475569;">This is an automated notification from <strong>SnapClass AI</strong>.</p>
        <div style="background:#fef2f2;border-left:4px solid #ef4444;
                    padding:16px 20px;border-radius:8px;margin:20px 0;">
          <strong style="color:#dc2626;">⚠️ Absence Recorded</strong><br>
          Student: <strong>{student_name}</strong><br>
          Subject: <strong>{subject_name}</strong>
        </div>
        <p style="color:#64748b;">Please contact the teacher if this is an error.</p>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
        <p style="color:#94a3b8;font-size:13px;">SnapClass AI · Built by Afsha Ahmed</p>
      </div>
    </div>
    """

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Absence Alert – {student_name} – {subject_name}"
            msg["From"]    = from_email or smtp_user
            msg["To"]      = parent_email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email or smtp_user, parent_email, msg.as_string())
            return {"sent": True, "to": parent_email, "student": student_name}
        except Exception as e:
            return {"sent": False, "error": str(e), "to": parent_email}

    # Demo mode
    return {"sent": False, "demo": True,
            "message": f"[DEMO] Would email {parent_email} about {student_name}'s absence"}
