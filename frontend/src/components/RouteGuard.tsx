"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { UserRole } from "@/types/auth";

// Route permissions
const routeRoles: Record<string, UserRole[]> = {
  "/staff": ["staff", "admin"],
  "/checker": ["checker", "admin"],
  "/admin": ["admin"],
};

// Public routes that don't require authentication
const publicRoutes = ["/", "/login"];

interface RouteGuardProps {
  children: React.ReactNode;
}

export function RouteGuard({ children }: RouteGuardProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;

    // Check if current route is public
    const isPublicRoute = publicRoutes.some(
      (route) => pathname === route || pathname.startsWith(route + "?")
    );

    if (!isAuthenticated && !isPublicRoute) {
      // Redirect to login if not authenticated and trying to access protected route
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      return;
    }

    if (isAuthenticated && pathname === "/login") {
      // Redirect authenticated users away from login page
      router.push("/");
      return;
    }

    if (isAuthenticated && user) {
      // Check role-based access
      for (const [route, roles] of Object.entries(routeRoles)) {
        if (pathname.startsWith(route)) {
          if (!roles.includes(user.role)) {
            // Redirect to home if user doesn't have required role
            router.push("/");
            return;
          }
          break;
        }
      }
    }
  }, [isAuthenticated, isLoading, user, pathname, router]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
