"""External SMTP adapter for human invitation delivery.

The invitation token remains graph/identity state. SMTP is deliberately kept
outside the graph because it is external I/O and credentials must not become
graph data.
"""
import os
import re
import smtplib
from email.message import EmailMessage


EMAIL_RE = re.compile(r'^[^@\s]{1,128}@[^@\s]{1,255}$')


class InvitationEmailError(RuntimeError):
    pass


def configured():
    return bool(os.environ.get('SEEDFORTH_SMTP_USER') and
                os.environ.get('SEEDFORTH_SMTP_APP_PASSWORD'))


def send_invitation(recipient, link, principal, scope):
    if not isinstance(recipient, str) or not EMAIL_RE.fullmatch(recipient):
        raise InvitationEmailError('invalid_recipient')
    user = os.environ.get('SEEDFORTH_SMTP_USER', '')
    password = os.environ.get('SEEDFORTH_SMTP_APP_PASSWORD', '')
    if not user or not password:
        raise InvitationEmailError('invitation_email_not_configured')
    host = os.environ.get('SEEDFORTH_SMTP_HOST', 'smtp.gmail.com')
    port = int(os.environ.get('SEEDFORTH_SMTP_PORT', '587'))
    sender = os.environ.get('SEEDFORTH_INVITE_FROM', user)
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = 'Your SeedForth access link'
    msg.set_content(
        'You have been invited to SeedForth.\n\n'
        f'Project scope: {scope or "SeedForth"}\n'
        f'Identity: {principal}\n\n'
        'Open this one-time link to enter:\n' + link + '\n\n'
        'The link expires in 24 hours and can be used once. '
        'If you did not expect this, ignore this email.'
    )
    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise InvitationEmailError('invitation_email_delivery_failed') from exc
