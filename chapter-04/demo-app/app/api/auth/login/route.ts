import { NextRequest, NextResponse } from 'next/server';
import db from '@/lib/db';
import {
  createSession,
  verifyPasswordConstantTime,
} from '@/lib/auth';
import { initDatabase } from '@/lib/db';
import {
  isSameOrigin,
  parseLogin,
  RateLimiter,
  ValidationError,
} from '@/lib/validation';

const loginLimiter = new RateLimiter(60_000, 10);

export async function POST(request: NextRequest) {
  try {
    if (!isSameOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const clientKey = request.headers.get('x-forwarded-for') ?? 'local';
    const limit = loginLimiter.check(`login:${clientKey}`);
    if (!limit.allowed) {
      return NextResponse.json(
        { error: 'too many login attempts; try again later' },
        { status: 429, headers: { 'retry-after': String(limit.retryAfterSec) } },
      );
    }

    initDatabase();

    let parsed;
    try {
      parsed = parseLogin(await request.json());
    } catch (err) {
      if (err instanceof ValidationError) {
        return NextResponse.json({ error: err.message }, { status: 400 });
      }
      throw err;
    }
    const { email, password } = parsed;

    const user = db
      .prepare('SELECT id, password_hash FROM users WHERE email = ?')
      .get(email) as { id: number; password_hash: string } | undefined;

    // Constant-time verification: compare against the real hash when the
    // user exists, otherwise against a cached dummy hash. Either way the
    // bcrypt cost is paid, so an attacker cannot enumerate registered
    // emails by measuring response time.
    const isValid = await verifyPasswordConstantTime(
      password,
      user?.password_hash ?? null,
    );

    if (!user || !isValid) {
      return NextResponse.json(
        { error: 'Invalid email or password' },
        { status: 401 }
      );
    }

    // Create session
    const sessionId = createSession(user.id);

    const response = NextResponse.json({ success: true, userId: user.id });
    response.cookies.set('session', sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    return response;
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
