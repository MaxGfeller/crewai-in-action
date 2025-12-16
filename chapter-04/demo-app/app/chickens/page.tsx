'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Navbar from '@/components/navbar';

interface Chicken {
  id: number;
  name: string;
  breed: string | null;
  age_months: number | null;
  weight_kg: number | null;
  status: string;
  notes: string | null;
}

export default function ChickensPage() {
  const router = useRouter();
  const [chickens, setChickens] = useState<Chicken[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingChicken, setEditingChicken] = useState<Chicken | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    breed: '',
    age_months: '',
    weight_kg: '',
    status: 'active',
    notes: '',
  });

  useEffect(() => {
    // Check authentication first
    fetch('/api/auth/me')
      .then((res) => {
        if (!res.ok) {
          router.push('/login');
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (!data || !data.user) {
          router.push('/login');
          return;
        }
        // Fetch chickens
        return fetch('/api/chickens');
      })
      .then((res) => res?.json())
      .then((data) => {
        if (data?.chickens) {
          setChickens(data.chickens);
        }
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
        router.push('/login');
      });
  }, [router]);

  const handleOpenDialog = (chicken?: Chicken) => {
    if (chicken) {
      setEditingChicken(chicken);
      setFormData({
        name: chicken.name,
        breed: chicken.breed || '',
        age_months: chicken.age_months?.toString() || '',
        weight_kg: chicken.weight_kg?.toString() || '',
        status: chicken.status,
        notes: chicken.notes || '',
      });
    } else {
      setEditingChicken(null);
      setFormData({
        name: '',
        breed: '',
        age_months: '',
        weight_kg: '',
        status: 'active',
        notes: '',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editingChicken
      ? `/api/chickens/${editingChicken.id}`
      : '/api/chickens';
    const method = editingChicken ? 'PUT' : 'POST';

    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          breed: formData.breed || null,
          age_months: formData.age_months ? parseInt(formData.age_months) : null,
          weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : null,
          status: formData.status,
          notes: formData.notes || null,
        }),
      });

      if (response.ok) {
        setDialogOpen(false);
        // Refresh chickens list
        const res = await fetch('/api/chickens');
        const data = await res.json();
        if (data.chickens) {
          setChickens(data.chickens);
        }
      }
    } catch (error) {
      console.error('Error saving chicken:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this chicken?')) {
      return;
    }

    try {
      const response = await fetch(`/api/chickens/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Refresh chickens list
        const res = await fetch('/api/chickens');
        const data = await res.json();
        if (data.chickens) {
          setChickens(data.chickens);
        }
      }
    } catch (error) {
      console.error('Error deleting chicken:', error);
    }
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">Loading...</div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Chickens</h1>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => handleOpenDialog()}>Add Chicken</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {editingChicken ? 'Edit Chicken' : 'Add New Chicken'}
                </DialogTitle>
                <DialogDescription>
                  {editingChicken
                    ? 'Update the chicken information below.'
                    : 'Enter the details for your new chicken.'}
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="breed">Breed</Label>
                  <Input
                    id="breed"
                    value={formData.breed}
                    onChange={(e) =>
                      setFormData({ ...formData, breed: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="age_months">Age (months)</Label>
                    <Input
                      id="age_months"
                      type="number"
                      value={formData.age_months}
                      onChange={(e) =>
                        setFormData({ ...formData, age_months: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="weight_kg">Weight (kg)</Label>
                    <Input
                      id="weight_kg"
                      type="number"
                      step="0.1"
                      value={formData.weight_kg}
                      onChange={(e) =>
                        setFormData({ ...formData, weight_kg: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <select
                    id="status"
                    value={formData.status}
                    onChange={(e) =>
                      setFormData({ ...formData, status: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="active">Active</option>
                    <option value="retired">Retired</option>
                    <option value="sick">Sick</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <textarea
                    id="notes"
                    value={formData.notes}
                    onChange={(e) =>
                      setFormData({ ...formData, notes: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    rows={3}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit">
                    {editingChicken ? 'Update' : 'Create'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Your Flock</CardTitle>
          </CardHeader>
          <CardContent>
            {chickens.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                No chickens yet. Add your first chicken to get started!
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Breed</TableHead>
                    <TableHead>Age</TableHead>
                    <TableHead>Weight</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {chickens.map((chicken) => (
                    <TableRow key={chicken.id}>
                      <TableCell className="font-medium">{chicken.name}</TableCell>
                      <TableCell>{chicken.breed || '-'}</TableCell>
                      <TableCell>
                        {chicken.age_months ? `${chicken.age_months} months` : '-'}
                      </TableCell>
                      <TableCell>
                        {chicken.weight_kg ? `${chicken.weight_kg} kg` : '-'}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            chicken.status === 'active'
                              ? 'bg-green-100 text-green-800'
                              : chicken.status === 'sick'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {chicken.status}
                        </span>
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {chicken.notes || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenDialog(chicken)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDelete(chicken.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
