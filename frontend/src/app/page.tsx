"use client";

import Link from "next/link";
import { FileText, UserCheck, Shield, LogIn, LogOut, ArrowRight, Sparkles, CheckCircle, Clock } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function Home() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const canAccessStaff = user?.role === "staff" || user?.role === "admin";
  const canAccessChecker = user?.role === "checker" || user?.role === "admin";
  const canAccessAdmin = user?.role === "admin";

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-subtle">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-subtle">
      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full text-blue-700 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            AI-Powered Document Verification
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-4 tracking-tight">
            Intelligent Account
            <br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Servicing Workflow
            </span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Streamline document verification with AI-powered analysis and human-in-the-loop review for secure account servicing.
          </p>

          {/* Auth Status */}
          <div className="mt-8">
            {isAuthenticated ? (
              <div className="inline-flex items-center gap-4 bg-white px-6 py-3 rounded-2xl shadow-sm border border-gray-100">
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
                    {user?.username?.charAt(0).toUpperCase()}
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-semibold text-gray-900">
                      {user?.username}
                    </p>
                    <Badge variant="info" size="sm">
                      {user?.role}
                    </Badge>
                  </div>
                </div>
                <div className="h-8 w-px bg-gray-200"></div>
                <button
                  onClick={logout}
                  className="flex items-center gap-2 text-sm text-red-600 hover:text-red-700 font-medium transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            ) : (
              <Link href="/login">
                <Button size="lg" icon={<LogIn className="w-5 h-5" />}>
                  Login to Continue
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* Portal Cards */}
        <div className={`grid gap-6 ${canAccessAdmin ? "md:grid-cols-3" : "md:grid-cols-2"} mb-12`}>
          {/* Staff Portal */}
          {canAccessStaff && (
            <Link href="/staff" className="group animate-fade-in-up stagger-1" style={{ animationFillMode: 'both' }}>
              <Card variant="interactive" padding="lg" className="h-full hover-lift">
                <div className="flex items-center justify-center w-14 h-14 bg-blue-100 rounded-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
                  <FileText className="w-7 h-7 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  Staff Portal
                </h2>
                <p className="text-gray-600 mb-6">
                  Submit change requests and upload documents for customer account modifications.
                </p>
                <div className="flex items-center text-blue-600 font-semibold group-hover:gap-3 transition-all duration-200">
                  Enter Portal
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform duration-200" />
                </div>
              </Card>
            </Link>
          )}

          {/* Checker Workbench */}
          {canAccessChecker && (
            <Link href="/checker" className="group animate-fade-in-up stagger-2" style={{ animationFillMode: 'both' }}>
              <Card variant="interactive" padding="lg" className="h-full hover-lift">
                <div className="flex items-center justify-center w-14 h-14 bg-green-100 rounded-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
                  <UserCheck className="w-7 h-7 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  Checker Workbench
                </h2>
                <p className="text-gray-600 mb-6">
                  Review AI-verified requests, examine confidence scores, and make decisions.
                </p>
                <div className="flex items-center text-green-600 font-semibold group-hover:gap-3 transition-all duration-200">
                  Enter Workbench
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform duration-200" />
                </div>
              </Card>
            </Link>
          )}

          {/* Admin Panel */}
          {canAccessAdmin && (
            <Link href="/admin" className="group animate-fade-in-up stagger-3" style={{ animationFillMode: 'both' }}>
              <Card variant="interactive" padding="lg" className="h-full hover-lift">
                <div className="flex items-center justify-center w-14 h-14 bg-purple-100 rounded-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
                  <Shield className="w-7 h-7 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  Admin Panel
                </h2>
                <p className="text-gray-600 mb-6">
                  Manage users, view system logs, and configure application settings.
                </p>
                <div className="flex items-center text-purple-600 font-semibold group-hover:gap-3 transition-all duration-200">
                  Enter Admin
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform duration-200" />
                </div>
              </Card>
            </Link>
          )}
        </div>

        {/* Not Authenticated Message */}
        {!isAuthenticated && (
          <Card className="bg-amber-50 border-amber-200 mb-12">
            <div className="text-center py-2">
              <p className="text-amber-800 font-medium">
                Please login to access the portals. Your available portals will be shown based on your role.
              </p>
            </div>
          </Card>
        )}

        {/* How it Works Section */}
        <Card padding="lg" className="bg-white/80 backdrop-blur animate-fade-in-up stagger-4" style={{ animationFillMode: 'both' }}>
          <h3 className="text-xl font-bold text-gray-900 mb-8 text-center">
            How It Works
          </h3>
          <div className="relative">
            {/* Connecting line */}
            <div className="hidden md:block absolute top-8 left-1/6 right-1/6 h-0.5 bg-gradient-to-r from-blue-200 via-purple-200 to-green-200"></div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center relative">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-200 transform hover:scale-105 transition-transform">
                  <span className="text-white font-bold text-xl">1</span>
                </div>
                <h4 className="font-semibold text-gray-900 mb-2">Submit Request</h4>
                <p className="text-sm text-gray-600">
                  Staff submits change request with supporting documents for verification.
                </p>
              </div>
              <div className="text-center relative">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-200 transform hover:scale-105 transition-transform">
                  <Sparkles className="w-7 h-7 text-white" />
                </div>
                <h4 className="font-semibold text-gray-900 mb-2">AI Verification</h4>
                <p className="text-sm text-gray-600">
                  AI processes documents, extracts data, and generates confidence scores.
                </p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-green-200 transform hover:scale-105 transition-transform">
                  <CheckCircle className="w-7 h-7 text-white" />
                </div>
                <h4 className="font-semibold text-gray-900 mb-2">Human Review</h4>
                <p className="text-sm text-gray-600">
                  Checker reviews AI summary and approves or rejects the request.
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
