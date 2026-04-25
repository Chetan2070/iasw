"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserCheck, ClipboardList, Clock, Home, User, LogOut, Bell, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { CheckerProvider, useChecker } from "@/contexts/CheckerContext";
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";
import { checkerApi } from "@/lib/api";

const navigation = [
  { name: "Dashboard", href: "/checker", icon: Home },
  { name: "Review Queue", href: "/checker/queue", icon: ClipboardList, showBadge: true },
  { name: "My Reviews", href: "/checker/reviews", icon: Clock },
];

function CheckerLayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { checkerId } = useChecker();
  const { user, logout } = useAuth();
  const [queueCount, setQueueCount] = useState<number>(0);

  useEffect(() => {
    const fetchQueueCount = async () => {
      try {
        const response = await checkerApi.getQueue({ limit: 1000 });
        setQueueCount(response.items.length);
      } catch (error) {
        console.error("Failed to fetch queue count:", error);
      }
    };
    fetchQueueCount();
    const interval = setInterval(fetchQueueCount, 30000);
    return () => clearInterval(interval);
  }, []);

  const getBreadcrumbs = () => {
    const paths = pathname.split("/").filter(Boolean);
    const breadcrumbs = [{ name: "Checker", href: "/checker" }];

    if (paths.length > 1) {
      if (paths[1] === "queue") {
        breadcrumbs.push({ name: "Review Queue", href: "/checker/queue" });
      } else if (paths[1] === "reviews") {
        breadcrumbs.push({ name: "My Reviews", href: "/checker/reviews" });
      } else if (paths[1] === "review" && paths[2]) {
        breadcrumbs.push({ name: "Review Details", href: pathname });
      }
    }

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <div className="min-h-screen bg-gradient-subtle">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center group">
                <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                  <UserCheck className="h-6 w-6 text-green-600" />
                </div>
                <span className="ml-3 text-xl font-bold text-gray-900">
                  IASW
                </span>
              </Link>
              <span className="px-3 py-1 bg-gradient-to-r from-green-500 to-green-600 text-white text-sm font-medium rounded-full shadow-sm">
                Checker Workbench
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors relative">
                <Bell className="h-5 w-5" />
                {queueCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center px-1">
                    {queueCount > 99 ? "99+" : queueCount}
                  </span>
                )}
              </button>
              <div className="h-6 w-px bg-gray-200"></div>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center text-white font-semibold text-sm">
                  {user?.username?.charAt(0).toUpperCase() || checkerId.charAt(0).toUpperCase()}
                </div>
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-medium text-gray-900">
                    {user?.username || checkerId}
                  </p>
                  <p className="text-xs text-gray-500">Checker</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-gray-200 hover:border-red-200"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white/50 backdrop-blur-sm min-h-[calc(100vh-64px)] border-r border-gray-200/50 sticky top-16 self-start">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/checker" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200",
                    isActive
                      ? "bg-green-50 text-green-700 shadow-sm"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  <item.icon
                    className={cn(
                      "mr-3 h-5 w-5 transition-colors",
                      isActive ? "text-green-600" : "text-gray-400"
                    )}
                  />
                  {item.name}
                  {item.showBadge && queueCount > 0 && (
                    <span className={cn(
                      "ml-auto px-2 py-0.5 text-xs font-bold rounded-full",
                      isActive
                        ? "bg-green-600 text-white"
                        : "bg-gray-200 text-gray-700"
                    )}>
                      {queueCount}
                    </span>
                  )}
                  {isActive && !item.showBadge && (
                    <ChevronRight className="ml-auto h-4 w-4 text-green-400" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Guidelines Section */}
          <div className="absolute bottom-4 left-4 right-4">
            <div className="p-4 bg-green-50 rounded-xl border border-green-100">
              <h4 className="text-sm font-medium text-green-900">Review Tips</h4>
              <p className="text-xs text-green-700 mt-1">
                Always verify document authenticity before approving.
              </p>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6">
          {/* Breadcrumbs */}
          {breadcrumbs.length > 1 && (
            <nav className="mb-4 flex items-center gap-2 text-sm">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.href} className="flex items-center gap-2">
                  {index > 0 && <ChevronRight className="h-4 w-4 text-gray-400" />}
                  {index === breadcrumbs.length - 1 ? (
                    <span className="text-gray-600 font-medium">{crumb.name}</span>
                  ) : (
                    <Link
                      href={crumb.href}
                      className="text-gray-500 hover:text-green-600 transition-colors"
                    >
                      {crumb.name}
                    </Link>
                  )}
                </div>
              ))}
            </nav>
          )}
          <div className="animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default function CheckerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <CheckerProvider>
      <CheckerLayoutContent>{children}</CheckerLayoutContent>
    </CheckerProvider>
  );
}
