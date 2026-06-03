import { NextRequest, NextResponse } from 'next/server';
import db from '@/lib/db';
import {
  hashPassword,
  createSession,
  verifyPasswordConstantTime,
} from '@/lib/auth';
import { initDatabase } from '@/lib/db';
import {
  isSameOrigin,
  parseSignup,
  RateLimiter,
  ValidationError,
} from '@/lib/validation';

const signupLimiter = new RateLimiter(60_000, 5);

export async function POST(request: NextRequest) {
  try {
    if (!isSameOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const clientKey = request.headers.get('x-forwarded-for') ?? 'local';
    const limit = signupLimiter.check(`signup:${clientKey}`);
    if (!limit.allowed) {
      return NextResponse.json(
        { error: 'too many signups; try again later' },
        { status: 429, headers: { 'retry-after': String(limit.retryAfterSec) } },
      );
    }

    initDatabase();

    let parsed;
    try {
      parsed = parseSignup(await request.json());
    } catch (err) {
      if (err instanceof ValidationError) {
        return NextResponse.json({ error: err.message }, { status: 400 });
      }
      throw err;
    }
    const { email, password, name } = parsed;

    // Check if user already exists
    const existingUser = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
    if (existingUser) {
      // Run a constant-time dummy verify to avoid leaking which emails are
      // registered via response-time differences.
      await verifyPasswordConstantTime(password, null);
      return NextResponse.json(
        { error: 'User already exists' },
        { status: 400 }
      );
    }

    // Create user
    const passwordHash = await hashPassword(password);
    const result = db
      .prepare('INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)')
      .run(email, passwordHash, name);

    const userId = result.lastInsertRowid as number;
    const sessionId = createSession(userId);

    const response = NextResponse.json({ success: true, userId });
    response.cookies.set('session', sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    return response;
  } catch (error) {
    console.error('Signup error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
