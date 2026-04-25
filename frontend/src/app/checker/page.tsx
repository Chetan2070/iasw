"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ClipboardList, CheckCircle, Clock, AlertTriangle, ArrowRight, Eye, Zap } from "lucide-react";
import { checkerApi } from "@/lib/api";
import { QueueItem } from "@/types";
import { usePolling } from "@/hooks/usePolling";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatCard } from "@/components/ui/StatCard";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function CheckerDashboard() {
  const [queueStats, setQueueStats] = useState({
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
  });
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
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
  }, []);

  usePolling(fetchStats, 10000);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Checker Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of pending reviews</p>
        </div>
        <Link href="/checker/queue">
          <Button variant="primary" icon={<ClipboardList className="h-5 w-5" />} className="bg-green-600 hover:bg-green-700">
            View Queue
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
            title="Total in Queue"
            value={queueStats.total}
            icon={ClipboardList}
            variant="blue"
          />
          <StatCard
            title="High Risk"
            value={queueStats.high}
            icon={AlertTriangle}
            variant="red"
          />
          <StatCard
            title="Medium Risk"
            value={queueStats.medium}
            icon={Clock}
            variant="yellow"
          />
          <StatCard
            title="Low Risk"
            value={queueStats.low}
            icon={CheckCircle}
            variant="green"
          />
        </div>
      )}

      {/* Quick Actions */}
      <Card padding="none">
        <CardHeader
          title="Quick Actions"
          description="Jump to filtered queue views"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6 pt-2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/checker/queue?risk_tier=HIGH"
              className="group"
            >
              <div className="p-5 border-2 border-red-100 rounded-xl hover:border-red-200 hover:bg-red-50/50 transition-all">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-red-100 rounded-xl group-hover:scale-110 transition-transform">
                    <AlertTriangle className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-gray-900">High Risk Items</p>
                      {queueStats.high > 0 && (
                        <Badge variant="danger" size="sm">{queueStats.high}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-500">
                      Priority items requiring attention
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-gray-400 group-hover:text-red-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </Link>

            <Link
              href="/checker/queue?ai_recommendation=APPROVE"
              className="group"
            >
              <div className="p-5 border-2 border-green-100 rounded-xl hover:border-green-200 hover:bg-green-50/50 transition-all">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-100 rounded-xl group-hover:scale-110 transition-transform">
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-gray-900">AI: Approve</p>
                      <Badge variant="success" size="sm">
                        <Zap className="h-3 w-3 mr-1" />
                        High Confidence
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">
                      Items with high AI confidence
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-gray-400 group-hover:text-green-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </Link>

            <Link
              href="/checker/queue?ai_recommendation=MANUAL_REVIEW"
              className="group"
            >
              <div className="p-5 border-2 border-amber-100 rounded-xl hover:border-amber-200 hover:bg-amber-50/50 transition-all">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-amber-100 rounded-xl group-hover:scale-110 transition-transform">
                    <Eye className="h-6 w-6 text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">Manual Review</p>
                    <p className="text-sm text-gray-500">
                      Items needing human judgment
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-gray-400 group-hover:text-amber-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Review Guidelines */}
      <Card className="bg-green-50 border-green-200">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-green-100 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-green-900 mb-2">Review Guidelines</h3>
            <ul className="text-sm text-green-800 space-y-1">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                Always verify document authenticity before approving
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                Check AI confidence scores and field match details
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                Flag any suspicious documents for escalation
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                Add detailed reasons when rejecting requests
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
