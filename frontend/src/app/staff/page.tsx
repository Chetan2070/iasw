"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Plus, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from "lucide-react";
import { requestsApi } from "@/lib/api";
import { RequestSummary, STATUS_LABELS, CHANGE_TYPE_LABELS } from "@/types";
import { getTimeAgo } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";

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
      // Fetch recent requests and stats in parallel
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

  // Auto-refresh every 10 seconds
  usePolling(fetchData, 10000);

  const getStatusIcon = (status: string) => {
    if (status === "APPROVED" || status === "COMPLETED") {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (status === "REJECTED" || status === "FAILED") {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }
    return <Clock className="h-5 w-5 text-yellow-500" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Link
          href="/staff/requests/new"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-5 w-5 mr-2" />
          New Request
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-lg">
              <AlertCircle className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Requests</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : stats.total}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <Clock className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : stats.pending}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Approved</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : stats.approved}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-red-100 rounded-lg">
              <XCircle className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Rejected</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : stats.rejected}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Requests */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Requests
            </h2>
            <Link
              href="/staff/requests"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              View all
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : recentRequests.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No requests yet.{" "}
            <Link href="/staff/requests/new" className="text-blue-600 hover:underline">
              Create your first request
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {recentRequests.map((request) => (
              <div
                key={request.request_id}
                className="px-6 py-4 hover:bg-gray-50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(request.status)}
                    <div>
                      <p className="font-medium text-gray-900">
                        {CHANGE_TYPE_LABELS[request.change_type]}
                      </p>
                      <p className="text-sm text-gray-500">
                        Customer: {request.customer_id}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {STATUS_LABELS[request.status]}
                    </span>
                    <p className="text-sm text-gray-500 mt-1">
                      {getTimeAgo(request.created_at)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
