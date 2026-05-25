const nodemailer = require('nodemailer');

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => {
      data += chunk;
    });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function normalizeText(value) {
  return String(value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function messageHtml(value) {
  return escapeHtml(normalizeText(value)).replace(/\n/g, '<br>');
}

function textBody({ name, email, subject, message, submittedAt }) {
  return [
    'AlliTrack',
    'New contact form message',
    '',
    `Subject: ${subject}`,
    '',
    'From:',
    `Name: ${name}`,
    `Email: ${email}`,
    submittedAt ? `Date/time submitted: ${submittedAt}` : null,
    '',
    'Message:',
    normalizeText(message),
    '',
    'This message was sent from the AlliTrack contact form.'
  ].filter(Boolean).join('\n');
}

function htmlBody({ name, email, subject, message, submittedAt }) {
  const safeName = escapeHtml(name);
  const safeEmail = escapeHtml(email);
  const safeSubject = escapeHtml(subject);
  const safeSubmittedAt = submittedAt ? escapeHtml(submittedAt) : '';
  const safeMessage = messageHtml(message);

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AlliTrack Contact Message</title>
  </head>
  <body style="margin:0; padding:0; background:#f3f6fb; font-family:Arial, Helvetica, sans-serif; color:#172033;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6fb; padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;">
            <tr>
              <td style="padding:0 0 18px;">
                <div style="font-size:28px; line-height:1.2; font-weight:800; color:#1d4ed8;">AlliTrack</div>
                <div style="font-size:14px; line-height:1.5; color:#64748b; margin-top:4px;">New contact form message</div>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:28px; box-shadow:0 14px 36px rgba(15, 23, 42, 0.08);">
                <div style="font-size:13px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">Subject</div>
                <div style="font-size:22px; line-height:1.35; font-weight:800; color:#0f172a; margin-bottom:24px;">${safeSubject}</div>

                <div style="border-top:1px solid #e2e8f0; padding-top:22px; margin-top:4px;">
                  <div style="font-size:15px; font-weight:800; color:#0f172a; margin-bottom:12px;">Sender information</div>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="width:110px; padding:6px 0; font-size:14px; color:#64748b;">Name</td>
                      <td style="padding:6px 0; font-size:14px; color:#172033; font-weight:600;">${safeName}</td>
                    </tr>
                    <tr>
                      <td style="width:110px; padding:6px 0; font-size:14px; color:#64748b;">Email</td>
                      <td style="padding:6px 0; font-size:14px; color:#172033; font-weight:600;">${safeEmail}</td>
                    </tr>
                    ${safeSubmittedAt ? `<tr>
                      <td style="width:110px; padding:6px 0; font-size:14px; color:#64748b;">Submitted</td>
                      <td style="padding:6px 0; font-size:14px; color:#172033; font-weight:600;">${safeSubmittedAt}</td>
                    </tr>` : ''}
                  </table>
                </div>

                <div style="border-top:1px solid #e2e8f0; padding-top:22px; margin-top:22px;">
                  <div style="font-size:15px; font-weight:800; color:#0f172a; margin-bottom:12px;">Message details</div>
                  <div style="font-size:15px; line-height:1.7; color:#334155; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:18px;">${safeMessage}</div>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 4px 0; font-size:12px; line-height:1.6; color:#64748b; text-align:center;">
                This message was sent from the AlliTrack contact form.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`;
}

async function main() {
  const mailUser = process.env.MAIL_USER;
  const mailPass = (process.env.MAIL_PASS || '').replace(/\s+/g, '');
  const receiver = process.env.CONTACT_RECEIVER;

  if (!mailUser || !mailPass || !receiver) {
    throw new Error('Missing MAIL_USER, MAIL_PASS, or CONTACT_RECEIVER');
  }

  const payload = JSON.parse(await readStdin());
  const { name, email, subject, message } = payload;
  const submittedAt = payload.submittedAt || payload.submitted_at || new Date().toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZoneName: 'short'
  });

  if (!name || !email || !subject || !message) {
    throw new Error('Missing contact email payload fields');
  }

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: mailUser,
      pass: mailPass
    }
  });

  await transporter.sendMail({
    from: `AlliTrack Contact Form <${mailUser}>`,
    to: receiver,
    replyTo: email,
    subject: `[AlliTrack Contact] ${subject}`,
    text: textBody({ name, email, subject, message, submittedAt }),
    html: htmlBody({ name, email, subject, message, submittedAt })
  });
}

main().catch(error => {
  console.error(error.message || error);
  process.exit(1);
});
