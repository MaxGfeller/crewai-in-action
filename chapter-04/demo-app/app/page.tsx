import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import db from '@/lib/db';
import { initDatabase } from '@/lib/db';

export default async function Home() {
  initDatabase();

  const cookieStore = await cookies();
  const sessionId = cookieStore.get('session')?.value;

  if (sessionId) {
    const session = db
      .prepare('SELECT user_id, expires_at FROM sessions WHERE id = ?')
      .get(sessionId) as { user_id: number; expires_at: string } | undefined;

    if (session) {
      const expiresAt = new Date(session.expires_at);
      if (expiresAt >= new Date()) {
        redirect('/dashboard');
      }
    }
  }

  redirect('/login');
}
