"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Filter, Trash2, Plus, FileText, X } from "lucide-react";
import { requestsApi } from "@/lib/api";
import {
  RequestSummary,
  ChangeType,
  RequestStatus,
  STATUS_LABELS,
  CHANGE_TYPE_LABELS,
} from "@/types";
import { cn, formatDate, formatPercentage } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { StatusBadge, RiskBadge } from "@/components/ui/Badge";
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
import { SkeletonTable } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

export default function RequestsListPage() {
  const router = useRouter();
  const { success, error: showError } = useToast();
  const [requests, setRequests] = useState<RequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    change_type: "" as ChangeType | "",
    status: "" as RequestStatus | "",
    customer_id: "",
  });

  const fetchRequests = useCallback(async () => {
    try {
      const params: Record<string, any> = { page, limit: 10 };
      if (filters.change_type) params.change_type = filters.change_type;
      if (filters.status) params.status = filters.status;
      if (filters.customer_id) params.customer_id = filters.customer_id;

      const response = await requestsApi.list(params);
      setRequests(response.items);
      setTotalPages(response.pages);
    } catch (error) {
      console.error("Failed to fetch requests:", error);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  usePolling(fetchRequests, 5000);

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({ change_type: "", status: "", customer_id: "" });
    setPage(1);
  };

  const hasActiveFilters = filters.change_type || filters.status || filters.customer_id;

  const handleRowClick = (requestId: string) => {
    router.push(`/staff/requests/${requestId}`);
  };

  const handleDelete = async (e: React.MouseEvent, requestId: string) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to delete request ${requestId.slice(0, 8)}...?`)) {
      return;
    }

    setDeletingId(requestId);
    try {
      await requestsApi.delete(requestId);
      setRequests((prev) => prev.filter((r) => r.request_id !== requestId));
      success("Request deleted", "The request has been successfully removed.");
    } catch (error) {
      console.error("Failed to delete request:", error);
      showError("Delete failed", "Could not delete the request. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Requests</h1>
          <p className="text-gray-500 mt-1">Manage and track all your submitted requests</p>
        </div>
        <Link href="/staff/requests/new">
          <Button icon={<Plus className="h-5 w-5" />}>
            New Request
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-gray-500">
            <Filter className="h-5 w-5" />
            <span className="text-sm font-medium">Filters</span>
          </div>

          <div className="flex-1 min-w-[200px] max-w-xs">
            <Input
              placeholder="Search by Customer ID"
              value={filters.customer_id}
              onChange={(e) => handleFilterChange("customer_id", e.target.value)}
              icon={<Search className="h-4 w-4" />}
              fullWidth
            />
          </div>

          <select
            value={filters.change_type}
            onChange={(e) => handleFilterChange("change_type", e.target.value)}
            className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">All Change Types</option>
            {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={filters.status}
            onChange={(e) => handleFilterChange("status", e.target.value)}
            className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">All Statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} icon={<X className="h-4 w-4" />}>
              Clear
            </Button>
          )}
        </div>
      </Card>

      {/* Table */}
      {loading ? (
        <SkeletonTable rows={10} columns={8} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Request ID</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Change Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Risk Tier</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requests.length === 0 ? (
              <TableEmpty
                colSpan={8}
                icon={<FileText className="h-8 w-8" />}
                title="No requests found"
                description={hasActiveFilters ? "Try adjusting your filters" : "Create your first request to get started"}
                action={
                  !hasActiveFilters && (
                    <Link href="/staff/requests/new">
                      <Button size="sm" icon={<Plus className="h-4 w-4" />}>
                        New Request
                      </Button>
                    </Link>
                  )
                }
              />
            ) : (
              requests.map((request) => (
                <TableRow
                  key={request.request_id}
                  clickable
                  onClick={() => handleRowClick(request.request_id)}
                >
                  <TableCell>
                    <span className="font-medium text-blue-600 hover:text-blue-700">
                      {request.request_id.slice(0, 12)}...
                    </span>
                  </TableCell>
                  <TableCell className="text-gray-900 font-medium">
                    {request.customer_id}
                  </TableCell>
                  <TableCell className="text-gray-700">
                    {CHANGE_TYPE_LABELS[request.change_type]}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={request.status} />
                  </TableCell>
                  <TableCell>
                    {request.risk_tier ? (
                      <RiskBadge tier={request.risk_tier} />
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {formatPercentage(request.overall_confidence)}
                  </TableCell>
                  <TableCell className="text-gray-500">
                    {formatDate(request.created_at)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleDelete(e, request.request_id)}
                      loading={deletingId === request.request_id}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </Table>
      )}
    </div>
  );
}
