import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that don't require authentication
const publicRoutes = ["/login", "/"];

// Role-based route permissions
const routeRoles: Record<string, string[]> = {
  "/staff": ["staff", "admin"],
  "/checker": ["checker", "admin"],
  "/admin": ["admin"],
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (publicRoutes.includes(pathname)) {
    return NextResponse.next();
  }

  // Check for auth token in localStorage via cookie
  // Note: We store auth data in localStorage, but we need to use a cookie for middleware
  // We'll check for a special cookie that gets set when user logs in
  const authCookie = request.cookies.get("iasw_auth");

  if (!authCookie) {
    // For now, let the client-side handle auth redirection
    // This allows the AuthContext to check localStorage
    return NextResponse.next();
  }

  try {
    const authData = JSON.parse(authCookie.value);
    const userRole = authData.role;

    // Check if user has permission for this route
    for (const [route, roles] of Object.entries(routeRoles)) {
      if (pathname.startsWith(route)) {
        if (!roles.includes(userRole)) {
          // Redirect to home if unauthorized
          return NextResponse.redirect(new URL("/", request.url));
        }
        break;
      }
    }

    return NextResponse.next();
  } catch {
    // Invalid cookie, let client handle it
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
