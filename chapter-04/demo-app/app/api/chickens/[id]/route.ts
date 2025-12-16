import { NextRequest, NextResponse } from 'next/server';
import db from '@/lib/db';
import { getSession } from '@/lib/auth';
import { initDatabase } from '@/lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const { id } = await params;
    initDatabase();
    const chicken = db
      .prepare('SELECT * FROM chickens WHERE id = ? AND user_id = ?')
      .get(id, user.id);

    if (!chicken) {
      return NextResponse.json({ error: 'Chicken not found' }, { status: 404 });
    }

    return NextResponse.json({ chicken });
  } catch (error) {
    console.error('Get chicken error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const { id } = await params;
    initDatabase();
    const { name, breed, age_months, weight_kg, status, notes } = await request.json();

    // Check if chicken exists and belongs to user
    const existing = db
      .prepare('SELECT id FROM chickens WHERE id = ? AND user_id = ?')
      .get(id, user.id);

    if (!existing) {
      return NextResponse.json({ error: 'Chicken not found' }, { status: 404 });
    }

    db.prepare(
      `UPDATE chickens
       SET name = ?, breed = ?, age_months = ?, weight_kg = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
       WHERE id = ? AND user_id = ?`
    ).run(name, breed || null, age_months || null, weight_kg || null, status || 'active', notes || null, id, user.id);

    const chicken = db.prepare('SELECT * FROM chickens WHERE id = ?').get(id);
    return NextResponse.json({ chicken });
  } catch (error) {
    console.error('Update chicken error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const { id } = await params;
    initDatabase();

    // Check if chicken exists and belongs to user
    const existing = db
      .prepare('SELECT id FROM chickens WHERE id = ? AND user_id = ?')
      .get(id, user.id);

    if (!existing) {
      return NextResponse.json({ error: 'Chicken not found' }, { status: 404 });
    }

    db.prepare('DELETE FROM chickens WHERE id = ? AND user_id = ?').run(id, user.id);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete chicken error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

