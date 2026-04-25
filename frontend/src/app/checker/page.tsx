"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardList, CheckCircle, Clock, AlertTriangle } from "lucide-react";
import { checkerApi } from "@/lib/api";
import { QueueItem } from "@/types";

export default function CheckerDashboard() {
  const [queueStats, setQueueStats] = useState({
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await checkerApi.getQueue({ limit: 1000 });
        const items = response.items;

        setQueueStats({
          total: items.length,
          high: items.filter((i) => i.risk_tier === "HIGH").length,
          medium: items.filter((i) => i.risk_tier === "MEDIUM").length,
          low: items.filter((i) => i.risk_tier === "LOW").length,
        });
      } catch (error) {
        console.error("Failed to fetch queue stats:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Checker Dashboard</h1>
        <Link
          href="/checker/queue"
          className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <ClipboardList className="h-5 w-5 mr-2" />
          View Queue
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-lg">
              <ClipboardList className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total in Queue</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : queueStats.total}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-red-100 rounded-lg">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">High Risk</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : queueStats.high}
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
              <p className="text-sm font-medium text-gray-500">Medium Risk</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : queueStats.medium}
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
              <p className="text-sm font-medium text-gray-500">Low Risk</p>
              <p className="text-2xl font-bold text-gray-900">
                {loading ? "-" : queueStats.low}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/checker/queue?risk_tier=HIGH"
            className="p-4 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
          >
            <div className="flex items-center">
              <AlertTriangle className="h-8 w-8 text-red-600" />
              <div className="ml-4">
                <p className="font-medium text-gray-900">Review High Risk</p>
                <p className="text-sm text-gray-500">
                  Priority items requiring attention
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/checker/queue?ai_recommendation=APPROVE"
            className="p-4 border border-green-200 rounded-lg hover:bg-green-50 transition-colors"
          >
            <div className="flex items-center">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="font-medium text-gray-900">AI Recommends Approve</p>
                <p className="text-sm text-gray-500">
                  Items with high confidence
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/checker/queue?ai_recommendation=MANUAL_REVIEW"
            className="p-4 border border-yellow-200 rounded-lg hover:bg-yellow-50 transition-colors"
          >
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-yellow-600" />
              <div className="ml-4">
                <p className="font-medium text-gray-900">Manual Review</p>
                <p className="text-sm text-gray-500">
                  Items needing human judgment
                </p>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <h3 className="font-medium text-green-800 mb-2">Review Guidelines</h3>
        <ul className="text-sm text-green-700 space-y-1">
          <li>
            • Always verify document authenticity before approving
          </li>
          <li>
            • Check AI confidence scores and field match details
          </li>
          <li>
            • Flag any suspicious documents for escalation
          </li>
          <li>
            • Add detailed reasons when rejecting requests
          </li>
        </ul>
      </div>
    </div>
  );
}
