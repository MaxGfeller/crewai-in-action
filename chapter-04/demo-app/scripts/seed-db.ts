import db from '../lib/db';
import { hashPassword } from '../lib/auth';
import { initDatabase } from '../lib/db';

async function seed() {
  console.log('Initializing database...');
  initDatabase();

  console.log('Seeding database...');

  // Create a test user
  const passwordHash = await hashPassword('password123');
  const user = db
    .prepare('INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)')
    .run('demo@example.com', passwordHash, 'Demo User');

  const userId = user.lastInsertRowid as number;

  // Create some example chickens
  const chickens = [
    {
      name: 'Henrietta',
      breed: 'Rhode Island Red',
      age_months: 12,
      weight_kg: 2.5,
      status: 'active',
      notes: 'Lays brown eggs daily',
    },
    {
      name: 'Clucky',
      breed: 'Leghorn',
      age_months: 8,
      weight_kg: 2.1,
      status: 'active',
      notes: 'Very friendly, loves corn',
    },
    {
      name: 'Ginger',
      breed: 'Buff Orpington',
      age_months: 18,
      weight_kg: 3.0,
      status: 'active',
      notes: 'Mother hen, very protective',
    },
    {
      name: 'Pepper',
      breed: 'Plymouth Rock',
      age_months: 6,
      weight_kg: 1.8,
      status: 'active',
      notes: 'Youngest of the flock',
    },
    {
      name: 'Rosie',
      breed: 'Rhode Island Red',
      age_months: 24,
      weight_kg: 2.7,
      status: 'retired',
      notes: 'Retired from laying, still healthy',
    },
  ];

  const insertChicken = db.prepare(`
    INSERT INTO chickens (user_id, name, breed, age_months, weight_kg, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);

  for (const chicken of chickens) {
    insertChicken.run(
      userId,
      chicken.name,
      chicken.breed,
      chicken.age_months,
      chicken.weight_kg,
      chicken.status,
      chicken.notes
    );
  }

  console.log(`Created user: demo@example.com (password: password123)`);
  console.log(`Created ${chickens.length} example chickens`);
  console.log('Seeding complete!');
}

seed().catch(console.error);

