import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL       = os.getenv("FROM_EMAIL", "hello@careerpilotai.com")
ADMIN_EMAIL      = os.getenv("ADMIN_EMAIL", "admin@careerpilotai.com")

def send_email(to_email: str, subject: str, html_content: str):
    """Send an email via SendGrid."""
    if not SENDGRID_API_KEY:
        print(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
        return
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        print(f"Email error: {e}")

def send_contact_confirmation(name: str, email: str, service: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#6366f1">Thanks for reaching out, {name}! 🚀</h2>
      <p>We received your enquiry about <strong>{service}</strong>.</p>
      <p>Our team will get back to you within <strong>24 hours</strong>.</p>
      <hr/>
      <p style="color:#888">CareerPilot AI — Get Hired Faster</p>
    </div>
    """
    send_email(email, "We received your message — CareerPilot AI", html)
    send_email(ADMIN_EMAIL, f"New Contact: {name} — {service}",
               f"<p>New enquiry from <b>{name}</b> ({email}) about <b>{service}</b>.</p>")

def send_booking_confirmation(name: str, email: str, service: str, date: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#6366f1">Booking Confirmed! 🎉</h2>
      <p>Hi {name}, your <strong>{service}</strong> session is booked for <strong>{date}</strong>.</p>
      <p>You'll receive a Google Meet/Zoom link before your session.</p>
      <hr/>
      <p style="color:#888">CareerPilot AI</p>
    </div>
    """
    send_email(email, "Your Consultation is Confirmed — CareerPilot AI", html)
    send_email(ADMIN_EMAIL, f"New Booking: {name} — {service} @ {date}",
               f"<p><b>{name}</b> ({email}) booked <b>{service}</b> for <b>{date}</b>.</p>")

def send_payment_success(name: str, email: str, plan: str, amount: float):
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#10b981">Payment Successful! ✅</h2>
      <p>Hi {name}, your payment of <strong>₹{amount}</strong> for the <strong>{plan}</strong> plan is confirmed.</p>
      <p>Our team will contact you within 24 hours to begin your career transformation.</p>
      <hr/>
      <p style="color:#888">CareerPilot AI</p>
    </div>
    """
    send_email(email, f"Payment Confirmed — {plan} Plan", html)
