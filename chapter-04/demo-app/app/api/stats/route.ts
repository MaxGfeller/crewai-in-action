import { NextResponse } from 'next/server';
import db from '@/lib/db';
import { getSession } from '@/lib/auth';
import { initDatabase } from '@/lib/db';

export async function GET() {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    initDatabase();

    // Total chickens
    const totalChickens = db
      .prepare('SELECT COUNT(*) as count FROM chickens WHERE user_id = ?')
      .get(user.id) as { count: number };

    // Active chickens
    const activeChickens = db
      .prepare('SELECT COUNT(*) as count FROM chickens WHERE user_id = ? AND status = ?')
      .get(user.id, 'active') as { count: number };

    // Average age
    const avgAge = db
      .prepare('SELECT AVG(age_months) as avg FROM chickens WHERE user_id = ? AND age_months IS NOT NULL')
      .get(user.id) as { avg: number | null };

    // Average weight
    const avgWeight = db
      .prepare('SELECT AVG(weight_kg) as avg FROM chickens WHERE user_id = ? AND weight_kg IS NOT NULL')
      .get(user.id) as { avg: number | null };

    // Total weight
    const totalWeight = db
      .prepare('SELECT SUM(weight_kg) as total FROM chickens WHERE user_id = ? AND weight_kg IS NOT NULL')
      .get(user.id) as { total: number | null };

    // Chickens by breed
    const byBreed = db
      .prepare(
        'SELECT breed, COUNT(*) as count FROM chickens WHERE user_id = ? AND breed IS NOT NULL GROUP BY breed'
      )
      .all(user.id) as Array<{ breed: string; count: number }>;

    // Chickens by status
    const byStatus = db
      .prepare(
        'SELECT status, COUNT(*) as count FROM chickens WHERE user_id = ? GROUP BY status'
      )
      .all(user.id) as Array<{ status: string; count: number }>;

    return NextResponse.json({
      stats: {
        totalChickens: totalChickens.count,
        activeChickens: activeChickens.count,
        averageAge: avgAge.avg ? Math.round(avgAge.avg * 10) / 10 : 0,
        averageWeight: avgWeight.avg ? Math.round(avgWeight.avg * 100) / 100 : 0,
        totalWeight: totalWeight.total ? Math.round(totalWeight.total * 100) / 100 : 0,
        byBreed,
        byStatus,
      },
    });
  } catch (error) {
    console.error('Get stats error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

