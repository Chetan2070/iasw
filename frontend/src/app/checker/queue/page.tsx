"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Eye,
  Filter,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { checkerApi } from "@/lib/api";
import {
  QueueItem,
  RiskTier,
  Recommendation,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
  RISK_TIER_COLORS,
  RECOMMENDATION_COLORS,
} from "@/types";
import { cn, formatPercentage } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";
import { useChecker } from "@/contexts/CheckerContext";

function QueuePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkerId } = useChecker();

  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    risk_tier: RiskTier | "";
    ai_recommendation: Recommendation | "";
  }>({
    risk_tier: (searchParams.get("risk_tier") as RiskTier) || "",
    ai_recommendation:
      (searchParams.get("ai_recommendation") as Recommendation) || "",
  });

  const fetchQueue = useCallback(async () => {
    try {
      const params: Record<string, any> = {};
      if (filters.risk_tier) params.risk_tier = filters.risk_tier;
      if (filters.ai_recommendation)
        params.ai_recommendation = filters.ai_recommendation;

      const response = await checkerApi.getQueue(params);
      setItems(response.items);
    } catch (error) {
      console.error("Failed to fetch queue:", error);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Auto-refresh every 5 seconds
  usePolling(fetchQueue, 5000);

  const handleClaim = async (requestId: string) => {
    setClaiming(requestId);
    try {
      await checkerApi.claim(requestId, checkerId);
      router.push(`/checker/review/${requestId}`);
    } catch (error: any) {
      console.error("Failed to claim request:", error);
      const detail = error.response?.data?.detail;
      const errorMsg = typeof detail === 'string' ? detail : detail?.message || "Failed to claim request";
      alert(errorMsg);
    } finally {
      setClaiming(null);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const getRiskIcon = (tier: RiskTier) => {
    switch (tier) {
      case "HIGH":
        return <AlertTriangle className="h-4 w-4" />;
      case "MEDIUM":
        return <Clock className="h-4 w-4" />;
      case "LOW":
        return <CheckCircle className="h-4 w-4" />;
    }
  };

  const getRecommendationIcon = (rec: Recommendation) => {
    switch (rec) {
      case "APPROVE":
        return <CheckCircle className="h-4 w-4" />;
      case "REJECT":
        return <AlertTriangle className="h-4 w-4" />;
      case "MANUAL_REVIEW":
        return <Eye className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
        <button
          onClick={fetchQueue}
          disabled={loading}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw
            className={cn("h-5 w-5 mr-2", loading && "animate-spin")}
          />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <select
            value={filters.risk_tier}
            onChange={(e) => handleFilterChange("risk_tier", e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="">All Risk Tiers</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <select
            value={filters.ai_recommendation}
            onChange={(e) =>
              handleFilterChange("ai_recommendation", e.target.value)
            }
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="">All Recommendations</option>
            <option value="APPROVE">AI: Approve</option>
            <option value="REJECT">AI: Reject</option>
            <option value="MANUAL_REVIEW">AI: Manual Review</option>
          </select>

          {(filters.risk_tier || filters.ai_recommendation) && (
            <button
              onClick={() => setFilters({ risk_tier: "", ai_recommendation: "" })}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Queue Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Request
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Change Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  AI Recommendation
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Flags
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Wait Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                    Loading queue...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                    No items in queue
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.request_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {item.request_id.slice(0, 8)}...
                        </p>
                        <p className="text-xs text-gray-500">
                          {item.customer_id}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <p className="text-sm text-gray-900">
                          {CHANGE_TYPE_LABELS[item.change_type]}
                        </p>
                        <p className="text-xs text-gray-500">
                          {DOCUMENT_TYPE_LABELS[item.document_type]}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium",
                          RISK_TIER_COLORS[item.risk_tier]
                        )}
                      >
                        {getRiskIcon(item.risk_tier)}
                        {item.risk_tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 text-sm font-medium",
                          RECOMMENDATION_COLORS[item.ai_recommendation]
                        )}
                      >
                        {getRecommendationIcon(item.ai_recommendation)}
                        {item.ai_recommendation.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatPercentage(item.overall_score)}
                    </td>
                    <td className="px-6 py-4">
                      {item.flags.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {item.flags.slice(0, 2).map((flag, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-orange-100 text-orange-800"
                            >
                              {flag}
                            </span>
                          ))}
                          {item.flags.length > 2 && (
                            <span className="text-xs text-gray-500">
                              +{item.flags.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">None</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.time_in_queue_minutes}m
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleClaim(item.request_id)}
                        disabled={claiming === item.request_id}
                        className={cn(
                          "inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                          claiming === item.request_id
                            ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                            : "bg-green-600 text-white hover:bg-green-700"
                        )}
                      >
                        {claiming === item.request_id ? (
                          "Claiming..."
                        ) : (
                          <>
                            <Eye className="h-4 w-4 mr-1" />
                            Review
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function QueuePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-green-600 animate-spin" />
      </div>
    }>
      <QueuePageContent />
    </Suspense>
  );
}
