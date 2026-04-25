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
  X,
} from "lucide-react";
import { checkerApi } from "@/lib/api";
import {
  QueueItem,
  RiskTier,
  Recommendation,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
} from "@/types";
import { cn, formatPercentage } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";
import { useChecker } from "@/contexts/CheckerContext";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
} from "@/components/ui/Table";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

function QueuePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkerId } = useChecker();
  const { error: showError } = useToast();

  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    risk_tier: RiskTier | "";
    ai_recommendation: Recommendation | "";
  }>({
    risk_tier: (searchParams.get("risk_tier") as RiskTier) || "",
    ai_recommendation: (searchParams.get("ai_recommendation") as Recommendation) || "",
  });

  const fetchQueue = useCallback(async () => {
    try {
      const params: Record<string, any> = {};
      if (filters.risk_tier) params.risk_tier = filters.risk_tier;
      if (filters.ai_recommendation) params.ai_recommendation = filters.ai_recommendation;

      const response = await checkerApi.getQueue(params);
      setItems(response.items);
    } catch (error) {
      console.error("Failed to fetch queue:", error);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  usePolling(fetchQueue, 5000);

  const handleClaim = async (requestId: string) => {
    setClaiming(requestId);
    try {
      await checkerApi.claim(requestId, checkerId);
      router.push(`/checker/review/${requestId}`);
    } catch (error: any) {
      console.error("Failed to claim request:", error);
      const detail = error.response?.data?.detail;
      const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to claim request";
      showError("Claim failed", errorMsg);
    } finally {
      setClaiming(null);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({ risk_tier: "", ai_recommendation: "" });
  };

  const hasActiveFilters = filters.risk_tier || filters.ai_recommendation;

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

  const getRecommendationBadge = (rec: Recommendation) => {
    switch (rec) {
      case "APPROVE":
        return (
          <Badge variant="success" size="sm">
            <CheckCircle className="h-3 w-3 mr-1" />
            Approve
          </Badge>
        );
      case "REJECT":
        return (
          <Badge variant="danger" size="sm">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Reject
          </Badge>
        );
      case "MANUAL_REVIEW":
        return (
          <Badge variant="warning" size="sm">
            <Eye className="h-3 w-3 mr-1" />
            Manual Review
          </Badge>
        );
    }
  };

  const getRowHighlight = (tier: RiskTier): "red" | "yellow" | "green" | undefined => {
    switch (tier) {
      case "HIGH":
        return "red";
      case "MEDIUM":
        return "yellow";
      case "LOW":
        return "green";
      default:
        return undefined;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-gray-500 mt-1">
            {items.length} items waiting for review
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => fetchQueue()}
          loading={loading}
          icon={<RefreshCw className={cn("h-5 w-5", loading && "animate-spin")} />}
        >
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-gray-500">
            <Filter className="h-5 w-5" />
            <span className="text-sm font-medium">Filters</span>
          </div>

          {/* Filter Chips */}
          <div className="flex flex-wrap gap-2">
            {/* Risk Tier Chips */}
            {(["HIGH", "MEDIUM", "LOW"] as RiskTier[]).map((tier) => (
              <button
                key={tier}
                onClick={() =>
                  handleFilterChange("risk_tier", filters.risk_tier === tier ? "" : tier)
                }
                className={cn(
                  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all",
                  filters.risk_tier === tier
                    ? tier === "HIGH"
                      ? "bg-red-100 text-red-700 border-red-300"
                      : tier === "MEDIUM"
                      ? "bg-amber-100 text-amber-700 border-amber-300"
                      : "bg-green-100 text-green-700 border-green-300"
                    : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
                )}
              >
                {getRiskIcon(tier)}
                <span>{tier} Risk</span>
              </button>
            ))}
          </div>

          <div className="h-6 w-px bg-gray-200"></div>

          {/* Recommendation Chips */}
          <div className="flex flex-wrap gap-2">
            {(["APPROVE", "MANUAL_REVIEW", "REJECT"] as Recommendation[]).map((rec) => (
              <button
                key={rec}
                onClick={() =>
                  handleFilterChange("ai_recommendation", filters.ai_recommendation === rec ? "" : rec)
                }
                className={cn(
                  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all",
                  filters.ai_recommendation === rec
                    ? rec === "APPROVE"
                      ? "bg-green-100 text-green-700 border-green-300"
                      : rec === "REJECT"
                      ? "bg-red-100 text-red-700 border-red-300"
                      : "bg-amber-100 text-amber-700 border-amber-300"
                    : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
                )}
              >
                {rec === "APPROVE" && <CheckCircle className="h-3.5 w-3.5" />}
                {rec === "REJECT" && <AlertTriangle className="h-3.5 w-3.5" />}
                {rec === "MANUAL_REVIEW" && <Eye className="h-3.5 w-3.5" />}
                <span>AI: {rec.replace("_", " ")}</span>
              </button>
            ))}
          </div>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} icon={<X className="h-4 w-4" />}>
              Clear
            </Button>
          )}
        </div>
      </Card>

      {/* Queue Table */}
      {loading ? (
        <SkeletonTable rows={8} columns={8} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Request</TableHead>
              <TableHead>Change Type</TableHead>
              <TableHead>Risk Tier</TableHead>
              <TableHead>AI Recommendation</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Flags</TableHead>
              <TableHead>Wait Time</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableEmpty
                colSpan={8}
                icon={<CheckCircle className="h-8 w-8" />}
                title="Queue is empty"
                description={
                  hasActiveFilters
                    ? "No items match your current filters"
                    : "All items have been reviewed"
                }
              />
            ) : (
              items.map((item) => (
                <TableRow key={item.request_id} highlight={getRowHighlight(item.risk_tier)}>
                  <TableCell>
                    <div>
                      <p className="font-medium text-gray-900">
                        {item.request_id.slice(0, 8)}...
                      </p>
                      <p className="text-xs text-gray-500">{item.customer_id}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-gray-900">{CHANGE_TYPE_LABELS[item.change_type]}</p>
                      <p className="text-xs text-gray-500">
                        {DOCUMENT_TYPE_LABELS[item.document_type]}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <RiskBadge tier={item.risk_tier} />
                  </TableCell>
                  <TableCell>{getRecommendationBadge(item.ai_recommendation)}</TableCell>
                  <TableCell>
                    <span className="font-medium text-gray-900">
                      {formatPercentage(item.overall_score)}
                    </span>
                  </TableCell>
                  <TableCell>
                    {item.flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.flags.slice(0, 2).map((flag, idx) => (
                          <Badge key={idx} variant="warning" size="sm">
                            {flag}
                          </Badge>
                        ))}
                        {item.flags.length > 2 && (
                          <Badge variant="default" size="sm">
                            +{item.flags.length - 2}
                          </Badge>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">None</span>
                    )}
                  </TableCell>
                  <TableCell className="text-gray-500">
                    {item.time_in_queue_minutes}m
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      onClick={() => handleClaim(item.request_id)}
                      loading={claiming === item.request_id}
                      icon={<Eye className="h-4 w-4" />}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

export default function QueuePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 text-green-600 animate-spin" />
        </div>
      }
    >
      <QueuePageContent />
    </Suspense>
  );
}
