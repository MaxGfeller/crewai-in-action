import { redirect } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Navbar from '@/components/navbar';
import { requireAuth } from '@/lib/auth-server';
import { initDatabase } from '@/lib/db';
import db from '@/lib/db';

export default async function DashboardPage() {
  // Ensure database is initialized
  initDatabase();

  // Require authentication - will redirect if not authenticated
  const user = await requireAuth();
  const stats = {
    totalChickens: db
      .prepare('SELECT COUNT(*) as count FROM chickens WHERE user_id = ?')
      .get(user.id) as { count: number },
    activeChickens: db
      .prepare('SELECT COUNT(*) as count FROM chickens WHERE user_id = ? AND status = ?')
      .get(user.id, 'active') as { count: number },
    averageAge: db
      .prepare('SELECT AVG(age_months) as avg FROM chickens WHERE user_id = ? AND age_months IS NOT NULL')
      .get(user.id) as { avg: number | null },
    averageWeight: db
      .prepare('SELECT AVG(weight_kg) as avg FROM chickens WHERE user_id = ? AND weight_kg IS NOT NULL')
      .get(user.id) as { avg: number | null },
    totalWeight: db
      .prepare('SELECT SUM(weight_kg) as total FROM chickens WHERE user_id = ? AND weight_kg IS NOT NULL')
      .get(user.id) as { total: number | null },
    byBreed: db
      .prepare(
        'SELECT breed, COUNT(*) as count FROM chickens WHERE user_id = ? AND breed IS NOT NULL GROUP BY breed'
      )
      .all(user.id) as Array<{ breed: string; count: number }>,
    byStatus: db
      .prepare(
        'SELECT status, COUNT(*) as count FROM chickens WHERE user_id = ? GROUP BY status'
      )
      .all(user.id) as Array<{ status: string; count: number }>,
  };

  return (
    <>
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Total Chickens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.totalChickens.count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Active Chickens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{stats.activeChickens.count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Average Age</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {stats.averageAge.avg ? Math.round(stats.averageAge.avg * 10) / 10 : 0} months
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Total Weight</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {stats.totalWeight.total ? Math.round(stats.totalWeight.total * 100) / 100 : 0} kg
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Chickens by Breed</CardTitle>
              <CardDescription>Distribution of your flock</CardDescription>
            </CardHeader>
            <CardContent>
              {stats.byBreed.length > 0 ? (
                <div className="space-y-2">
                  {stats.byBreed.map((item) => (
                    <div key={item.breed} className="flex justify-between items-center">
                      <span>{item.breed}</span>
                      <span className="font-semibold">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No breed data available</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Chickens by Status</CardTitle>
              <CardDescription>Current status overview</CardDescription>
            </CardHeader>
            <CardContent>
              {stats.byStatus.length > 0 ? (
                <div className="space-y-2">
                  {stats.byStatus.map((item) => (
                    <div key={item.status} className="flex justify-between items-center">
                      <span className="capitalize">{item.status}</span>
                      <span className="font-semibold">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No status data available</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
