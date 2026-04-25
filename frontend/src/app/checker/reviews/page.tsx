"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Clock, XCircle } from "lucide-react";
import {
  CHANGE_TYPE_LABELS,
  STATUS_LABELS,
} from "@/types";
import { cn, formatDate } from "@/lib/utils";

interface ReviewHistoryItem {
  request_id: string;
  customer_id: string;
  change_type: string;
  decision: string;
  decided_at: string;
}

export default function MyReviewsPage() {
  const [reviews, setReviews] = useState<ReviewHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - in production this would come from an API
    setReviews([
      {
        request_id: "req-001",
        customer_id: "CUST-001",
        change_type: "LEGAL_NAME",
        decision: "APPROVED",
        decided_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        request_id: "req-002",
        customer_id: "CUST-002",
        change_type: "ADDRESS",
        decision: "REJECTED",
        decided_at: new Date(Date.now() - 7200000).toISOString(),
      },
      {
        request_id: "req-003",
        customer_id: "CUST-003",
        change_type: "DOB",
        decision: "ESCALATE",
        decided_at: new Date(Date.now() - 86400000).toISOString(),
      },
    ]);
    setLoading(false);
  }, []);

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case "APPROVED":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "REJECTED":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case "APPROVED":
        return "bg-green-100 text-green-800";
      case "REJECTED":
        return "bg-red-100 text-red-800";
      default:
        return "bg-yellow-100 text-yellow-800";
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">My Reviews</h1>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Request
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Customer
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Change Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Decision
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : reviews.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  No reviews yet
                </td>
              </tr>
            ) : (
              reviews.map((review) => (
                <tr key={review.request_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">
                      {review.request_id}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {review.customer_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {CHANGE_TYPE_LABELS[review.change_type as keyof typeof CHANGE_TYPE_LABELS] || review.change_type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium",
                        getDecisionColor(review.decision)
                      )}
                    >
                      {getDecisionIcon(review.decision)}
                      {review.decision}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(review.decided_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
