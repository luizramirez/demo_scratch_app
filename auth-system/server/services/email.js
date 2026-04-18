const nodemailer = require('nodemailer');

const isDev = process.env.NODE_ENV !== 'production';

// In development, create a one-time Ethereal test account and reuse it
let devTransporter = null;
const getDevTransporter = async () => {
  if (devTransporter) return devTransporter;
  const testAccount = await nodemailer.createTestAccount();
  devTransporter = nodemailer.createTransport({
    host: 'smtp.ethereal.email',
    port: 587,
    auth: { user: testAccount.user, pass: testAccount.pass },
  });
  return devTransporter;
};

const getProdTransporter = () =>
  nodemailer.createTransport({
    host: process.env.EMAIL_HOST,
    port: Number(process.env.EMAIL_PORT),
    secure: process.env.EMAIL_PORT === '465',
    auth: { user: process.env.EMAIL_USER, pass: process.env.EMAIL_PASS },
  });

const sendEmail = async ({ to, subject, html }) => {
  const transporter = isDev ? await getDevTransporter() : getProdTransporter();
  const info = await transporter.sendMail({
    from: process.env.EMAIL_FROM || 'Auth App <no-reply@example.com>',
    to,
    subject,
    html,
  });
  if (isDev) {
    console.log(`\n📧  Email preview: ${nodemailer.getTestMessageUrl(info)}\n`);
  }
};

const sendVerificationEmail = (email, token) =>
  sendEmail({
    to: email,
    subject: 'Verify your email address',
    html: `
      <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2>Verify your email</h2>
        <p>Click the button below to verify your email address. This link expires in 24 hours.</p>
        <a href="${process.env.CLIENT_URL}/verify-email/${token}"
           style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px">
          Verify Email
        </a>
        <p style="margin-top:16px;color:#6b7280;font-size:14px">
          Or copy this link: ${process.env.CLIENT_URL}/verify-email/${token}
        </p>
      </div>
    `,
  });

const sendPasswordResetEmail = (email, token) =>
  sendEmail({
    to: email,
    subject: 'Reset your password',
    html: `
      <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2>Reset your password</h2>
        <p>Click the button below to reset your password. This link expires in 1 hour.</p>
        <a href="${process.env.CLIENT_URL}/reset-password/${token}"
           style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px">
          Reset Password
        </a>
        <p style="margin-top:16px;color:#6b7280;font-size:14px">
          If you didn't request this, you can safely ignore this email.
        </p>
      </div>
    `,
  });

module.exports = { sendVerificationEmail, sendPasswordResetEmail };
