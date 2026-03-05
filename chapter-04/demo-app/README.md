# Chicken CRM Demo App

A minimal CRM application built with Next.js, Tailwind CSS, and shadcn/ui to keep track of chickens. Features user authentication, CRUD operations for chickens, and a dashboard with statistics.

## Tech Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **SQLite** - Database (better-sqlite3)
- **bcryptjs** - Password hashing

## Getting Started

### Installation

```bash
npm install
```

### Database Setup

First, initialize the database:

```bash
npm run setup-db
```

Then, seed it with example data:

```bash
npm run seed-db
```

This will create:
- A demo user: `demo@example.com` / `password123`
- 5 example chickens

### Development

Start the development server:

```bash
npm run dev
```

Open [http://localhost:4100](http://localhost:4100) in your browser.

## Features

- **Authentication**: Sign up and login with session management
- **Chicken Management**: Add, edit, and delete chickens
- **Dashboard**: View statistics about your flock including:
  - Total and active chickens
  - Average age and weight
  - Distribution by breed and status

## Database Schema

- **users**: User accounts with email, password hash, and name
- **sessions**: Session management for authentication
- **chickens**: Chicken records with name, breed, age, weight, status, and notes

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run setup-db` - Initialize database schema
- `npm run seed-db` - Seed database with example data

## Project Structure

```
demo-app/
├── app/
│   ├── api/          # API routes
│   ├── dashboard/    # Dashboard page
│   ├── chickens/     # Chickens management page
│   ├── login/        # Login page
│   └── signup/       # Signup page
├── components/       # React components
├── lib/              # Utilities and database
└── scripts/          # Database setup and seeding scripts
```
