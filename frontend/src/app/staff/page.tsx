"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Plus, Clock, CheckCircle, XCircle, AlertCircle, ArrowRight, TrendingUp } from "lucide-react";
import { requestsApi } from "@/lib/api";
import { RequestSummary, STATUS_LABELS, CHANGE_TYPE_LABELS } from "@/types";
import { getTimeAgo } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/Badge";
import { SkeletonCard, SkeletonList } from "@/components/ui/Skeleton";

export default function StaffDashboard() {
  const [recentRequests, setRecentRequests] = useState<RequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    approved: 0,
    rejected: 0,
  });

  const fetchData = useCallback(async () => {
    try {
      const [recentResponse, statsResponse] = await Promise.all([
        requestsApi.list({ limit: 5 }),
        requestsApi.getStats(),
      ]);

      setRecentRequests(recentResponse.items);
      setStats(statsResponse);
    } catch (error) {
      console.error("Failed to fetch requests:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  usePolling(fetchData, 10000);

  const getStatusIcon = (status: string) => {
    if (status === "APPROVED" || status === "COMPLETED") {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (status === "REJECTED" || status === "FAILED") {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }
    return <Clock className="h-5 w-5 text-amber-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of your request activity</p>
        </div>
        <Link href="/staff/requests/new">
          <Button icon={<Plus className="h-5 w-5" />}>
            New Request
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            title="Total Requests"
            value={stats.total}
            icon={AlertCircle}
            variant="blue"
          />
          <StatCard
            title="Pending"
            value={stats.pending}
            icon={Clock}
            variant="yellow"
          />
          <StatCard
            title="Approved"
            value={stats.approved}
            icon={CheckCircle}
            variant="green"
          />
          <StatCard
            title="Rejected"
            value={stats.rejected}
            icon={XCircle}
            variant="red"
          />
        </div>
      )}

      {/* Recent Requests */}
      <Card padding="none">
        <CardHeader
          title="Recent Requests"
          description="Your latest submitted requests"
          action={
            <Link href="/staff/requests">
              <Button variant="ghost" size="sm" icon={<ArrowRight className="h-4 w-4" />} iconPosition="right">
                View all
              </Button>
            </Link>
          }
          className="px-6 pt-6"
        />
        <CardContent className="px-0 pt-0">
          {loading ? (
            <div className="px-6 pb-6">
              <SkeletonList items={5} />
            </div>
          ) : recentRequests.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="h-8 w-8 text-gray-400" />
              </div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">No requests yet</h3>
              <p className="text-sm text-gray-500 mb-4">
                Get started by creating your first request
              </p>
              <Link href="/staff/requests/new">
                <Button size="sm" icon={<Plus className="h-4 w-4" />}>
                  Create Request
                </Button>
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {recentRequests.map((request) => (
                <Link
                  key={request.request_id}
                  href={`/staff/requests/${request.request_id}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-gray-100 rounded-lg">
                        {getStatusIcon(request.status)}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {CHANGE_TYPE_LABELS[request.change_type]}
                        </p>
                        <p className="text-sm text-gray-500">
                          Customer: {request.customer_id}
                        </p>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-4">
                      <StatusBadge status={request.status} />
                      <p className="text-sm text-gray-500">
                        {getTimeAgo(request.created_at)}
                      </p>
                      <ArrowRight className="h-4 w-4 text-gray-400" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card variant="interactive" className="hover-lift">
          <Link href="/staff/requests/new" className="block">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-xl">
                <Plus className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Submit New Request</h3>
                <p className="text-sm text-gray-500">Create a new change request with documents</p>
              </div>
              <ArrowRight className="h-5 w-5 text-gray-400 ml-auto" />
            </div>
          </Link>
        </Card>
        <Card variant="interactive" className="hover-lift">
          <Link href="/staff/requests" className="block">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-xl">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Track Requests</h3>
                <p className="text-sm text-gray-500">View all your submitted requests</p>
              </div>
              <ArrowRight className="h-5 w-5 text-gray-400 ml-auto" />
            </div>
          </Link>
        </Card>
      </div>
    </div>
  );
}
