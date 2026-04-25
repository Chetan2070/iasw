"use client";

import { useState } from "react";
import { Activity, Search, Filter, User, FileText, CheckCircle, XCircle, Clock } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
  Pagination,
} from "@/components/ui/Table";
import { cn } from "@/lib/utils";

interface LogEntry {
  id: string;
  timestamp: string;
  user: string;
  userRole: string;
  action: string;
  resource: string;
  resourceId: string;
  status: "success" | "failure" | "pending";
  details: string;
}

const mockLogs: LogEntry[] = [
  {
    id: "1",
    timestamp: "2024-03-15T10:30:00Z",
    user: "admin",
    userRole: "admin",
    action: "LOGIN",
    resource: "auth",
    resourceId: "-",
    status: "success",
    details: "User logged in successfully",
  },
  {
    id: "2",
    timestamp: "2024-03-15T10:25:00Z",
    user: "staff_user",
    userRole: "staff",
    action: "CREATE_REQUEST",
    resource: "request",
    resourceId: "REQ-001",
    status: "success",
    details: "Created change request for account 1234567890",
  },
  {
    id: "3",
    timestamp: "2024-03-15T10:20:00Z",
    user: "checker_user",
    userRole: "checker",
    action: "APPROVE_REQUEST",
    resource: "request",
    resourceId: "REQ-002",
    status: "success",
    details: "Approved legal name change request",
  },
  {
    id: "4",
    timestamp: "2024-03-15T10:15:00Z",
    user: "staff_user",
    userRole: "staff",
    action: "UPLOAD_DOCUMENT",
    resource: "document",
    resourceId: "DOC-001",
    status: "success",
    details: "Uploaded passport.pdf for request REQ-003",
  },
  {
    id: "5",
    timestamp: "2024-03-15T10:10:00Z",
    user: "checker_user",
    userRole: "checker",
    action: "REJECT_REQUEST",
    resource: "request",
    resourceId: "REQ-004",
    status: "success",
    details: "Rejected request due to document mismatch",
  },
  {
    id: "6",
    timestamp: "2024-03-15T10:05:00Z",
    user: "unknown",
    userRole: "-",
    action: "LOGIN",
    resource: "auth",
    resourceId: "-",
    status: "failure",
    details: "Failed login attempt - invalid credentials",
  },
  {
    id: "7",
    timestamp: "2024-03-15T10:00:00Z",
    user: "system",
    userRole: "system",
    action: "AI_PROCESS",
    resource: "document",
    resourceId: "DOC-002",
    status: "success",
    details: "AI verification completed for document",
  },
];

const actionColors: Record<string, string> = {
  LOGIN: "blue",
  CREATE_REQUEST: "green",
  APPROVE_REQUEST: "green",
  REJECT_REQUEST: "red",
  UPLOAD_DOCUMENT: "purple",
  AI_PROCESS: "amber",
};

export default function LogsPage() {
  const [logs] = useState<LogEntry[]>(mockLogs);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [page, setPage] = useState(1);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.details.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = selectedStatus === "all" || log.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failure":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-amber-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Logs</h1>
          <p className="text-gray-500 mt-1">Monitor system activity and user actions</p>
        </div>
        <Button variant="outline" icon={<Filter className="h-4 w-4" />}>
          Export Logs
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-gray-900">{logs.length}</p>
          <p className="text-sm text-gray-500">Total Events</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {logs.filter((l) => l.status === "success").length}
          </p>
          <p className="text-sm text-gray-500">Successful</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-red-600">
            {logs.filter((l) => l.status === "failure").length}
          </p>
          <p className="text-sm text-gray-500">Failed</p>
        </Card>
        <Card padding="md" className="text-center">
          <p className="text-2xl font-bold text-purple-600">
            {new Set(logs.map((l) => l.user)).size}
          </p>
          <p className="text-sm text-gray-500">Unique Users</p>
        </Card>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />
          </div>
          <div className="flex items-center gap-2">
            {["all", "success", "failure"].map((status) => (
              <button
                key={status}
                onClick={() => setSelectedStatus(status)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-lg transition-all",
                  selectedStatus === status
                    ? "bg-purple-100 text-purple-700"
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Logs Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredLogs.length === 0 ? (
            <TableEmpty
              colSpan={6}
              icon={<Activity className="h-8 w-8" />}
              title="No logs found"
              description="Try adjusting your filters"
            />
          ) : (
            filteredLogs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="text-gray-500 font-mono text-xs">
                  {formatDate(log.timestamp)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-gray-400" />
                    <span className="font-medium text-gray-900">{log.user}</span>
                    {log.userRole !== "-" && (
                      <Badge variant="default" size="sm">
                        {log.userRole}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      actionColors[log.action] === "green"
                        ? "success"
                        : actionColors[log.action] === "red"
                        ? "danger"
                        : actionColors[log.action] === "blue"
                        ? "info"
                        : actionColors[log.action] === "purple"
                        ? "purple"
                        : "warning"
                    }
                    size="sm"
                  >
                    {log.action.replace(/_/g, " ")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">{log.resource}</span>
                    {log.resourceId !== "-" && (
                      <span className="text-xs text-gray-400 font-mono">
                        ({log.resourceId})
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(log.status)}
                    <span
                      className={cn(
                        "text-sm font-medium",
                        log.status === "success" && "text-green-600",
                        log.status === "failure" && "text-red-600",
                        log.status === "pending" && "text-amber-600"
                      )}
                    >
                      {log.status}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-gray-600 max-w-xs truncate">
                  {log.details}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
        <Pagination currentPage={page} totalPages={3} onPageChange={setPage} />
      </Table>
    </div>
  );
}
