"use client";

import { useState, useEffect } from "react";
import { Activity, Search, Filter, User, FileText, CheckCircle, XCircle, Clock, RefreshCw, Bot, Settings } from "lucide-react";
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
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";
import { adminApi, AuditLogEntry, AuditLogStats } from "@/lib/api";

const eventTypeColors: Record<string, string> = {
  REQUEST_CREATED: "blue",
  DOCUMENT_UPLOADED: "purple",
  AI_PROCESSING_STARTED: "amber",
  AI_PROCESSING_COMPLETED: "amber",
  STATUS_CHANGED: "info",
  DECISION_MADE: "green",
  CLAIM_ACQUIRED: "blue",
  CLAIM_RELEASED: "gray",
};

const actorIcons = {
  human: User,
  ai: Bot,
  system: Settings,
};

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedActorType, setSelectedActorType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getAuditLogs({
        search: searchQuery || undefined,
        actor_type: selectedActorType !== "all" ? selectedActorType : undefined,
        page,
        page_size: 20,
      });
      setLogs(data.logs);
      setStats(data.stats);
      setTotalPages(data.pagination.total_pages);
    } catch (err) {
      setError("Failed to load audit logs. Make sure the backend is running.");
      console.error("Error fetching audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, selectedActorType]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      setPage(1);
      fetchLogs();
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getActorIcon = (actorType: string | null) => {
    const Icon = actorIcons[actorType as keyof typeof actorIcons] || User;
    const colorClass = actorType === "ai" ? "text-amber-500" : actorType === "system" ? "text-gray-500" : "text-blue-500";
    return <Icon className={cn("h-4 w-4", colorClass)} />;
  };

  const getEventBadgeVariant = (eventType: string | null) => {
    if (!eventType) return "default";
    const color = eventTypeColors[eventType];
    if (color === "green") return "success";
    if (color === "red") return "danger";
    if (color === "blue") return "info";
    if (color === "purple") return "purple";
    if (color === "amber") return "warning";
    return "default";
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Logs</h1>
          <p className="text-gray-500 mt-1">Monitor system activity and audit trail</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            icon={<RefreshCw className="h-4 w-4" />}
            onClick={fetchLogs}
            loading={loading}
          >
            Refresh
          </Button>
          <Button variant="outline" icon={<Filter className="h-4 w-4" />}>
            Export Logs
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <p className="text-red-700">{error}</p>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card padding="md" className="text-center">
          {loading && !stats ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">{stats?.total || 0}</p>
          )}
          <p className="text-sm text-gray-500">Total Events</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading && !stats ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-blue-600">{stats?.human || 0}</p>
          )}
          <p className="text-sm text-gray-500">Human Actions</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading && !stats ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-amber-600">{stats?.ai || 0}</p>
          )}
          <p className="text-sm text-gray-500">AI Actions</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading && !stats ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-gray-600">{stats?.system || 0}</p>
          )}
          <p className="text-sm text-gray-500">System Events</p>
        </Card>
        <Card padding="md" className="text-center">
          {loading && !stats ? (
            <Skeleton className="h-8 w-16 mx-auto" />
          ) : (
            <p className="text-2xl font-bold text-purple-600">{stats?.unique_users || 0}</p>
          )}
          <p className="text-sm text-gray-500">Unique Actors</p>
        </Card>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search by actor or request ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />
          </div>
          <div className="flex items-center gap-2">
            {["all", "human", "ai", "system"].map((type) => (
              <button
                key={type}
                onClick={() => {
                  setSelectedActorType(type);
                  setPage(1);
                }}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-lg transition-all",
                  selectedActorType === type
                    ? "bg-purple-100 text-purple-700"
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
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
            <TableHead>Actor</TableHead>
            <TableHead>Event Type</TableHead>
            <TableHead>Request ID</TableHead>
            <TableHead>State Change</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-4 w-4 rounded-full" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                </TableCell>
                <TableCell><Skeleton className="h-6 w-32" /></TableCell>
                <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                <TableCell><Skeleton className="h-4 w-40" /></TableCell>
              </TableRow>
            ))
          ) : logs.length === 0 ? (
            <TableEmpty
              colSpan={6}
              icon={<Activity className="h-8 w-8" />}
              title="No logs found"
              description={searchQuery ? "Try adjusting your search" : "No audit logs recorded yet"}
            />
          ) : (
            logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="text-gray-500 font-mono text-xs">
                  {formatDate(log.timestamp)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {getActorIcon(log.actor_type)}
                    <span className="font-medium text-gray-900">{log.actor_id}</span>
                    {log.actor_type && (
                      <Badge variant="default" size="sm">
                        {log.actor_type}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={getEventBadgeVariant(log.event_type)}
                    size="sm"
                  >
                    {log.event_type?.replace(/_/g, " ") || "-"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span className="text-xs text-gray-400 font-mono">
                    {log.request_id ? log.request_id.slice(0, 8) + "..." : "-"}
                  </span>
                </TableCell>
                <TableCell>
                  {log.previous_state || log.new_state ? (
                    <div className="flex items-center gap-1 text-sm">
                      <span className="text-gray-500">{log.previous_state || "—"}</span>
                      <span className="text-gray-400">→</span>
                      <span className="text-gray-900 font-medium">{log.new_state || "—"}</span>
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
                <TableCell className="text-gray-600 max-w-xs truncate">
                  {log.agent_name ? (
                    <span className="text-amber-600">Agent: {log.agent_name}</span>
                  ) : log.action_details ? (
                    <span className="text-xs">{JSON.stringify(log.action_details).slice(0, 50)}...</span>
                  ) : (
                    "-"
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
        {totalPages > 1 && (
          <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Table>
    </div>
  );
}
