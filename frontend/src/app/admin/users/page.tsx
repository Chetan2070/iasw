"use client";

import { useState, useEffect } from "react";
import { Users, Search, Plus, Edit2, Trash2, Shield, UserCheck, FileText, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
} from "@/components/ui/Table";
import { Skeleton } from "@/components/ui/Skeleton";
import { adminApi, AdminUser, AdminUserStats } from "@/lib/api";

const roleIcons = {
  admin: Shield,
  staff: FileText,
  checker: UserCheck,
};

const roleColors = {
  admin: "purple",
  staff: "blue",
  checker: "green",
} as const;

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<AdminUserStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getUsers({
        search: searchQuery || undefined,
      });
      setUsers(data.users);
      setStats(data.stats);
    } catch (err) {
      setError("Failed to load users. Make sure the backend is running.");
      console.error("Error fetching users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (searchQuery !== "") {
        fetchUsers();
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-500 mt-1">Manage system users and their roles</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            icon={<RefreshCw className="h-4 w-4" />}
            onClick={fetchUsers}
            loading={loading}
          >
            Refresh
          </Button>
          <Button icon={<Plus className="h-4 w-4" />}>Add User</Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <p className="text-red-700">{error}</p>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card padding="md" className="text-center">
          {loading ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">{stats?.total || 0}</p>
          )}
          <p className="text-sm text-gray-500">Total Users</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-purple-600">{stats?.admin || 0}</p>
          )}
          <p className="text-sm text-gray-500">Admins</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-blue-600">{stats?.staff || 0}</p>
          )}
          <p className="text-sm text-gray-500">Staff</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-green-600">{stats?.checker || 0}</p>
          )}
          <p className="text-sm text-gray-500">Checkers</p>
        </Card>
      </div>

      {/* Search */}
      <Card padding="md">
        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search users by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />
          </div>
        </div>
      </Card>

      {/* Users Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>User</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Last Login</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div>
                      <Skeleton className="h-4 w-32 mb-1" />
                      <Skeleton className="h-3 w-40" />
                    </div>
                  </div>
                </TableCell>
                <TableCell><Skeleton className="h-6 w-16" /></TableCell>
                <TableCell><Skeleton className="h-6 w-16" /></TableCell>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-8 w-20" /></TableCell>
              </TableRow>
            ))
          ) : users.length === 0 ? (
            <TableEmpty
              colSpan={6}
              icon={<Users className="h-8 w-8" />}
              title="No users found"
              description={searchQuery ? "Try adjusting your search" : "No users in the system yet"}
            />
          ) : (
            users.map((user) => {
              const RoleIcon = roleIcons[user.role] || FileText;
              const roleColor = roleColors[user.role] || "gray";
              return (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-full bg-${roleColor}-100`}>
                        <RoleIcon className={`h-4 w-4 text-${roleColor}-600`} />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{user.username}</p>
                        <p className="text-sm text-gray-500">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={roleColor === "purple" ? "purple" : roleColor === "blue" ? "info" : "success"}
                      size="sm"
                    >
                      {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={user.is_active ? "success" : "default"}
                      size="sm"
                    >
                      {user.is_active ? "active" : "inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {formatDate(user.created_at)}
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {formatDate(user.last_login)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" icon={<Edit2 className="h-4 w-4" />}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={<Trash2 className="h-4 w-4" />}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
