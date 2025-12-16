import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import db from './db';
import { User } from './auth';

export async function requireAuth(): Promise<User> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get('session')?.value;

  if (!sessionId) {
    redirect('/login');
  }

  const session = db
    .prepare('SELECT user_id, expires_at FROM sessions WHERE id = ?')
    .get(sessionId) as { user_id: number; expires_at: string } | undefined;

  if (!session) {
    redirect('/login');
  }

  const expiresAt = new Date(session.expires_at);
  if (expiresAt < new Date()) {
    // Session expired, delete it
    db.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
    redirect('/login');
  }

  const user = db
    .prepare('SELECT id, email, name FROM users WHERE id = ?')
    .get(session.user_id) as User | undefined;

  if (!user) {
    redirect('/login');
  }

  return user;
}

export async function getAuthUser(): Promise<User | null> {
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
    db.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
    return null;
  }

  const user = db
    .prepare('SELECT id, email, name FROM users WHERE id = ?')
    .get(session.user_id) as User | undefined;

  return user || null;
}

