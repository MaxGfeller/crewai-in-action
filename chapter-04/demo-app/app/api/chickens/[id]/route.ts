import { NextRequest, NextResponse } from 'next/server';
import db from '@/lib/db';
import { getSession } from '@/lib/auth';
import { initDatabase } from '@/lib/db';
import { isSameOrigin } from '@/lib/validation';

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
    if (!isSameOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const { id } = await params;
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
    ).run(name, breed, age_months, weight_kg, status, notes, id, user.id);

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
    if (!isSameOrigin(request)) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }
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

