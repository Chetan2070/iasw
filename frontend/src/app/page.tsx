import Link from "next/link";
import { FileText, UserCheck } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-4xl mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Intelligent Account Servicing Workflow
          </h1>
          <p className="text-lg text-gray-600">
            AI-powered document verification with human-in-the-loop
          </p>
        </div>

        {/* Portal Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Staff Portal */}
          <Link href="/staff">
            <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition-shadow cursor-pointer border border-gray-100">
              <div className="flex items-center justify-center w-16 h-16 bg-blue-100 rounded-lg mb-6">
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-3">
                Staff Portal
              </h2>
              <p className="text-gray-600 mb-4">
                Submit new change requests and upload supporting documents for
                customer account modifications.
              </p>
              <div className="flex items-center text-blue-600 font-medium">
                Enter Staff Portal
                <svg
                  className="w-5 h-5 ml-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </Link>

          {/* Checker Workbench */}
          <Link href="/checker">
            <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition-shadow cursor-pointer border border-gray-100">
              <div className="flex items-center justify-center w-16 h-16 bg-green-100 rounded-lg mb-6">
                <UserCheck className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-3">
                Checker Workbench
              </h2>
              <p className="text-gray-600 mb-4">
                Review AI-verified requests, examine confidence scores, and
                approve or reject change requests.
              </p>
              <div className="flex items-center text-green-600 font-medium">
                Enter Checker Workbench
                <svg
                  className="w-5 h-5 ml-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </Link>
        </div>

        {/* Info Section */}
        <div className="mt-12 bg-gray-50 rounded-xl p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            How it works
          </h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm text-gray-600">
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold mr-3">
                1
              </span>
              <div>
                <strong className="text-gray-900">Submit Request</strong>
                <br />
                Staff submits change request with supporting document
              </div>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold mr-3">
                2
              </span>
              <div>
                <strong className="text-gray-900">AI Verification</strong>
                <br />
                AI processes document, extracts data, and generates confidence
                scores
              </div>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold mr-3">
                3
              </span>
              <div>
                <strong className="text-gray-900">Human Review</strong>
                <br />
                Checker reviews AI summary and approves or rejects the request
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
