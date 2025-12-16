import { NextRequest, NextResponse } from 'next/server';
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
    const chickens = db
      .prepare('SELECT * FROM chickens WHERE user_id = ? ORDER BY created_at DESC')
      .all(user.id);

    return NextResponse.json({ chickens });
  } catch (error) {
    console.error('Get chickens error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    initDatabase();
    const { name, breed, age_months, weight_kg, status, notes } = await request.json();

    if (!name) {
      return NextResponse.json(
        { error: 'Name is required' },
        { status: 400 }
      );
    }

    const result = db
      .prepare(
        `INSERT INTO chickens (user_id, name, breed, age_months, weight_kg, status, notes)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        user.id,
        name,
        breed || null,
        age_months || null,
        weight_kg || null,
        status || 'active',
        notes || null
      );

    const chicken = db
      .prepare('SELECT * FROM chickens WHERE id = ?')
      .get(result.lastInsertRowid) as any;

    return NextResponse.json({ chicken }, { status: 201 });
  } catch (error) {
    console.error('Create chicken error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

