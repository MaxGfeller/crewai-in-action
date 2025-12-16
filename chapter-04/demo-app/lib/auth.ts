import { cookies } from 'next/headers';
import db from './db';
import bcrypt from 'bcryptjs';
import { randomBytes } from 'crypto';

export interface User {
  id: number;
  email: string;
  name: string;
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

export function createSession(userId: number): string {
  const sessionId = randomBytes(32).toString('hex');
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + 7); // 7 days

  db.prepare(
    'INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)'
  ).run(sessionId, userId, expiresAt.toISOString());

  return sessionId;
}

export async function getSession(): Promise<User | null> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get('session')?.value;

  if (!sessionId) {
    return null;
  }

  const session = db
    .prepare('SELECT user_id, expires_at FROM sessions WHERE id = ?')
    .get(sessionId) as { user_id: number; expires_at: string } | undefined;

  if (!session) {
    return null;
  }

  const expiresAt = new Date(session.expires_at);
  if (expiresAt < new Date()) {
    // Session expired, delete it
    db.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
    return null;
  }

  const user = db
    .prepare('SELECT id, email, name FROM users WHERE id = ?')
    .get(session.user_id) as User | undefined;

  return user || null;
}

export function deleteSession(sessionId: string) {
  db.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
}

export function cleanupExpiredSessions() {
  db.prepare('DELETE FROM sessions WHERE expires_at < ?').run(new Date().toISOString());
}

