"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, Clock, XCircle, Eye, RefreshCw, History } from "lucide-react";
import { checkerApi } from "@/lib/api";
import { CHANGE_TYPE_LABELS } from "@/types";
import { formatDate, formatPercentage } from "@/lib/utils";
import { useChecker } from "@/contexts/CheckerContext";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
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

interface ReviewHistoryItem {
  request_id: string;
  customer_id: string;
  change_type: string;
  document_type: string;
  decision: string;
  decision_reason: string | null;
  decided_at: string;
  reviewed_by: string;
  ai_recommendation: string | null;
  risk_tier: string | null;
  overall_score: number | null;
}

export default function ReviewsPage() {
  const router = useRouter();
  const { checkerId } = useChecker();
  const [reviews, setReviews] = useState<ReviewHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchReviews = useCallback(async () => {
    try {
      setError(null);
      const response = await checkerApi.getReviewHistory(checkerId, { page, limit: 20 });
      setReviews(response.items);
      setTotalPages(Math.ceil(response.total / 20));
    } catch (err: any) {
      console.error("Failed to fetch reviews:", err);
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to load review history";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [checkerId, page]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleViewDetails = (requestId: string) => {
    router.push(`/checker/review/${requestId}?readonly=true`);
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case "APPROVE":
        return (
          <Badge variant="success" size="sm">
            <CheckCircle className="h-3 w-3 mr-1" />
            Approved
          </Badge>
        );
      case "REJECT":
        return (
          <Badge variant="danger" size="sm">
            <XCircle className="h-3 w-3 mr-1" />
            Rejected
          </Badge>
        );
      default:
        return (
          <Badge variant="warning" size="sm">
            <Clock className="h-3 w-3 mr-1" />
            {decision}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Reviews</h1>
          <p className="text-gray-500 mt-1">History of your completed reviews</p>
        </div>
        <Button
          variant="outline"
          onClick={() => fetchReviews()}
          loading={loading}
          icon={<RefreshCw className="h-4 w-4" />}
        >
          Refresh
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <Card className="bg-red-50 border-red-200">
          <p className="text-red-700">{error}</p>
        </Card>
      )}

      {/* Reviews Table */}
      {loading ? (
        <SkeletonTable rows={10} columns={8} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Request</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Change Type</TableHead>
              <TableHead>Decision</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Reviewed By</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {reviews.length === 0 ? (
              <TableEmpty
                colSpan={8}
                icon={<History className="h-8 w-8" />}
                title="No reviews yet"
                description="Complete some reviews to see them here"
              />
            ) : (
              reviews.map((review) => (
                <TableRow key={review.request_id}>
                  <TableCell>
                    <span className="font-medium text-blue-600">
                      {review.request_id.slice(0, 12)}...
                    </span>
                  </TableCell>
                  <TableCell className="text-gray-900 font-medium">
                    {review.customer_id}
                  </TableCell>
                  <TableCell className="text-gray-700">
                    {CHANGE_TYPE_LABELS[review.change_type as keyof typeof CHANGE_TYPE_LABELS] || review.change_type}
                  </TableCell>
                  <TableCell>
                    {getDecisionBadge(review.decision)}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {formatPercentage(review.overall_score)}
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {review.reviewed_by}
                  </TableCell>
                  <TableCell className="text-gray-500">
                    {formatDate(review.decided_at)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewDetails(review.request_id)}
                      icon={<Eye className="h-4 w-4" />}
                      className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                    >
                      View
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
