"use client";

import { useState } from "react";
import { Users, Search, Plus, Edit2, Trash2, Shield, UserCheck, FileText } from "lucide-react";
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

interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "staff" | "checker";
  status: "active" | "inactive";
  createdAt: string;
  lastLogin: string | null;
}

const mockUsers: User[] = [
  {
    id: "1",
    username: "admin",
    email: "admin@iasw.com",
    role: "admin",
    status: "active",
    createdAt: "2024-01-01T00:00:00Z",
    lastLogin: "2024-03-15T10:30:00Z",
  },
  {
    id: "2",
    username: "staff_user",
    email: "staff@iasw.com",
    role: "staff",
    status: "active",
    createdAt: "2024-01-15T00:00:00Z",
    lastLogin: "2024-03-14T14:20:00Z",
  },
  {
    id: "3",
    username: "checker_user",
    email: "checker@iasw.com",
    role: "checker",
    status: "active",
    createdAt: "2024-02-01T00:00:00Z",
    lastLogin: "2024-03-15T09:00:00Z",
  },
  {
    id: "4",
    username: "inactive_staff",
    email: "inactive@iasw.com",
    role: "staff",
    status: "inactive",
    createdAt: "2024-01-20T00:00:00Z",
    lastLogin: null,
  },
];

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
  const [users] = useState<User[]>(mockUsers);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
        <Button icon={<Plus className="h-4 w-4" />}>Add User</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-gray-900">{users.length}</p>
          <p className="text-sm text-gray-500">Total Users</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-purple-600">
            {users.filter((u) => u.role === "admin").length}
          </p>
          <p className="text-sm text-gray-500">Admins</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-blue-600">
            {users.filter((u) => u.role === "staff").length}
          </p>
          <p className="text-sm text-gray-500">Staff</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {users.filter((u) => u.role === "checker").length}
          </p>
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
          {filteredUsers.length === 0 ? (
            <TableEmpty
              colSpan={6}
              icon={<Users className="h-8 w-8" />}
              title="No users found"
              description={searchQuery ? "Try adjusting your search" : "Add a user to get started"}
            />
          ) : (
            filteredUsers.map((user) => {
              const RoleIcon = roleIcons[user.role];
              return (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-full bg-${roleColors[user.role]}-100`}>
                        <RoleIcon className={`h-4 w-4 text-${roleColors[user.role]}-600`} />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{user.username}</p>
                        <p className="text-sm text-gray-500">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={roleColors[user.role] === "purple" ? "purple" : roleColors[user.role] === "blue" ? "info" : "success"}
                      size="sm"
                    >
                      {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={user.status === "active" ? "success" : "default"}
                      size="sm"
                    >
                      {user.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {formatDate(user.createdAt)}
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {formatDate(user.lastLogin)}
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
