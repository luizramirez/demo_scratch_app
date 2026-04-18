const User = require('../models/User');
const {
  signAccessToken,
  signRefreshToken,
  verifyRefreshToken,
  generateSecureToken,
  hashToken,
} = require('../utils/jwt');
const { sendVerificationEmail, sendPasswordResetEmail } = require('../services/email');

// ─── Helpers ───────────────────────────────────────────────────────────────

const issueTokens = (res, user) => {
  const accessToken = signAccessToken(user._id);
  const refreshToken = signRefreshToken(user._id);

  // HttpOnly cookie for refresh token
  res.cookie('refreshToken', refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7d
  });

  return { accessToken, refreshToken };
};

// ─── Register ──────────────────────────────────────────────────────────────

exports.register = async (req, res) => {
  try {
    const { name, email, password } = req.body;

    const existing = await User.findOne({ email });
    if (existing) {
      return res.status(409).json({ message: 'Email already registered' });
    }

    const verificationToken = generateSecureToken();
    const user = await User.create({
      name,
      email,
      password,
      emailVerificationToken: hashToken(verificationToken),
      emailVerificationExpires: Date.now() + 24 * 60 * 60 * 1000, // 24h
    });

    await sendVerificationEmail(user.email, verificationToken);

    res.status(201).json({
      message: 'Registration successful. Please check your email to verify your account.',
      user: user.toJSON(),
    });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Login ─────────────────────────────────────────────────────────────────

exports.login = async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await User.findOne({ email }).select(
      '+password +loginAttempts +lockUntil +refreshTokens'
    );

    if (!user) {
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    if (user.isLocked()) {
      const minutesLeft = Math.ceil((user.lockUntil - Date.now()) / 60000);
      return res.status(423).json({
        message: `Account locked. Try again in ${minutesLeft} minutes.`,
      });
    }

    const isMatch = await user.comparePassword(password);
    if (!isMatch) {
      await user.incLoginAttempts();
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    if (!user.isEmailVerified) {
      return res.status(403).json({
        message: 'Please verify your email before logging in.',
        code: 'EMAIL_NOT_VERIFIED',
      });
    }

    await user.resetLoginAttempts();

    const { accessToken, refreshToken } = issueTokens(res, user);

    // Store refresh token hash
    user.refreshTokens.push({ token: hashToken(refreshToken) });
    // Keep only last 5 refresh tokens
    if (user.refreshTokens.length > 5) {
      user.refreshTokens = user.refreshTokens.slice(-5);
    }
    await user.save({ validateBeforeSave: false });

    res.json({ accessToken, user: user.toJSON() });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Logout ────────────────────────────────────────────────────────────────

exports.logout = async (req, res) => {
  try {
    const refreshToken = req.cookies?.refreshToken;
    if (refreshToken) {
      const hashed = hashToken(refreshToken);
      await User.findByIdAndUpdate(req.user._id, {
        $pull: { refreshTokens: { token: hashed } },
      });
    }
    res.clearCookie('refreshToken');
    res.json({ message: 'Logged out successfully' });
  } catch (err) {
    console.error('Logout error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Refresh Token ─────────────────────────────────────────────────────────

exports.refreshToken = async (req, res) => {
  try {
    const token = req.cookies?.refreshToken;
    if (!token) return res.status(401).json({ message: 'No refresh token' });

    const decoded = verifyRefreshToken(token);
    const user = await User.findById(decoded.id).select('+refreshTokens');
    if (!user) return res.status(401).json({ message: 'User not found' });

    const hashed = hashToken(token);
    const stored = user.refreshTokens.find((t) => t.token === hashed);
    if (!stored) return res.status(401).json({ message: 'Invalid refresh token' });

    // Rotate: remove old, issue new
    user.refreshTokens = user.refreshTokens.filter((t) => t.token !== hashed);
    const { accessToken, refreshToken: newRefreshToken } = issueTokens(res, user);
    user.refreshTokens.push({ token: hashToken(newRefreshToken) });
    await user.save({ validateBeforeSave: false });

    res.json({ accessToken });
  } catch {
    res.status(401).json({ message: 'Invalid or expired refresh token' });
  }
};

// ─── Verify Email ──────────────────────────────────────────────────────────

exports.verifyEmail = async (req, res) => {
  try {
    const hashed = hashToken(req.params.token);
    const user = await User.findOne({
      emailVerificationToken: hashed,
      emailVerificationExpires: { $gt: Date.now() },
    });

    if (!user) {
      return res.status(400).json({ message: 'Invalid or expired verification link' });
    }

    user.isEmailVerified = true;
    user.emailVerificationToken = undefined;
    user.emailVerificationExpires = undefined;
    await user.save({ validateBeforeSave: false });

    res.json({ message: 'Email verified successfully. You can now log in.' });
  } catch (err) {
    console.error('Verify email error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Resend Verification ───────────────────────────────────────────────────

exports.resendVerification = async (req, res) => {
  try {
    if (req.user.isEmailVerified) {
      return res.status(400).json({ message: 'Email already verified' });
    }
    const verificationToken = generateSecureToken();
    await User.findByIdAndUpdate(req.user._id, {
      emailVerificationToken: hashToken(verificationToken),
      emailVerificationExpires: Date.now() + 24 * 60 * 60 * 1000,
    });
    await sendVerificationEmail(req.user.email, verificationToken);
    res.json({ message: 'Verification email sent' });
  } catch (err) {
    console.error('Resend verification error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Forgot Password ───────────────────────────────────────────────────────

exports.forgotPassword = async (req, res) => {
  try {
    const { email } = req.body;
    // Always return success to prevent user enumeration
    const user = await User.findOne({ email });
    if (user) {
      const resetToken = generateSecureToken();
      user.passwordResetToken = hashToken(resetToken);
      user.passwordResetExpires = Date.now() + 60 * 60 * 1000; // 1h
      await user.save({ validateBeforeSave: false });
      await sendPasswordResetEmail(user.email, resetToken);
    }
    res.json({ message: 'If that email exists, a reset link has been sent.' });
  } catch (err) {
    console.error('Forgot password error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Reset Password ────────────────────────────────────────────────────────

exports.resetPassword = async (req, res) => {
  try {
    const hashed = hashToken(req.params.token);
    const user = await User.findOne({
      passwordResetToken: hashed,
      passwordResetExpires: { $gt: Date.now() },
    });

    if (!user) {
      return res.status(400).json({ message: 'Invalid or expired reset link' });
    }

    user.password = req.body.password;
    user.passwordResetToken = undefined;
    user.passwordResetExpires = undefined;
    // Invalidate all refresh tokens on password change
    user.refreshTokens = [];
    await user.save();

    res.clearCookie('refreshToken');
    res.json({ message: 'Password reset successful. Please log in.' });
  } catch (err) {
    console.error('Reset password error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

// ─── Get Current User ──────────────────────────────────────────────────────

exports.getMe = async (req, res) => {
  res.json({ user: req.user });
};

// ─── Change Password ───────────────────────────────────────────────────────

exports.changePassword = async (req, res) => {
  try {
    const { currentPassword, password } = req.body;
    const user = await User.findById(req.user._id).select('+password');

    const isMatch = await user.comparePassword(currentPassword);
    if (!isMatch) return res.status(400).json({ message: 'Current password is incorrect' });

    user.password = password;
    user.refreshTokens = []; // invalidate all sessions
    await user.save();

    res.clearCookie('refreshToken');
    res.json({ message: 'Password changed. Please log in again.' });
  } catch (err) {
    console.error('Change password error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
