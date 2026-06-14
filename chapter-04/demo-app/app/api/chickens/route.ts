import { NextRequest, NextResponse } from 'next/server';
import db from '@/lib/db';
import { getSession } from '@/lib/auth';
import { initDatabase } from '@/lib/db';
import { isSameOrigin } from '@/lib/validation';

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
    if (!isSameOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    initDatabase();
    const body = await request.json();
    const name = typeof body?.name === 'string' ? body.name.trim() : '';
    if (!name || name.length > 120) {
      return NextResponse.json(
        { error: 'Name is required and must be at most 120 characters' },
        { status: 400 }
      );
    }
    const breed = typeof body?.breed === 'string' && body.breed.trim() ? body.breed.trim() : null;
    const notes = typeof body?.notes === 'string' && body.notes.trim() ? body.notes.trim() : null;
    const status = typeof body?.status === 'string' && body.status.trim() ? body.status.trim() : 'active';
    const age_months = Number.isFinite(body?.age_months) ? Math.trunc(body.age_months) : null;
    const weight_kg = Number.isFinite(body?.weight_kg) ? body.weight_kg : null;

    const result = db
      .prepare(
        `INSERT INTO chickens (user_id, name, breed, age_months, weight_kg, status, notes)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        user.id,
        name,
        breed,
        age_months,
        weight_kg,
        status,
        notes
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

