"use client";

import { ReactNode, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    label?: string;
    positive?: boolean;
  };
  variant?: "blue" | "green" | "yellow" | "red" | "purple" | "gray";
  loading?: boolean;
  className?: string;
  animateValue?: boolean;
}

const variants = {
  blue: {
    bg: "bg-blue-50",
    icon: "text-blue-600",
    iconBg: "bg-blue-100",
    gradient: "from-blue-500 to-blue-600",
  },
  green: {
    bg: "bg-green-50",
    icon: "text-green-600",
    iconBg: "bg-green-100",
    gradient: "from-green-500 to-green-600",
  },
  yellow: {
    bg: "bg-amber-50",
    icon: "text-amber-600",
    iconBg: "bg-amber-100",
    gradient: "from-amber-500 to-amber-600",
  },
  red: {
    bg: "bg-red-50",
    icon: "text-red-600",
    iconBg: "bg-red-100",
    gradient: "from-red-500 to-red-600",
  },
  purple: {
    bg: "bg-purple-50",
    icon: "text-purple-600",
    iconBg: "bg-purple-100",
    gradient: "from-purple-500 to-purple-600",
  },
  gray: {
    bg: "bg-gray-50",
    icon: "text-gray-600",
    iconBg: "bg-gray-100",
    gradient: "from-gray-500 to-gray-600",
  },
};

function useAnimatedNumber(value: number, duration: number = 500): number {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const startValue = displayValue;

    const animate = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(startValue + (value - startValue) * easeOut);
      setDisplayValue(current);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return displayValue;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  variant = "blue",
  loading = false,
  className,
  animateValue = true,
}: StatCardProps) {
  const colors = variants[variant];
  const numericValue = typeof value === 'number' ? value : parseInt(value.toString(), 10);
  const isNumeric = !isNaN(numericValue);
  const animatedValue = useAnimatedNumber(isNumeric && animateValue ? numericValue : 0);

  return (
    <div
      className={cn(
        "bg-white rounded-xl shadow-sm border border-gray-100 p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 group",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          {loading ? (
            <div className="h-8 w-20 bg-gray-200 rounded shimmer" />
          ) : (
            <p className="text-3xl font-bold text-gray-900 tabular-nums">
              {isNumeric && animateValue ? animatedValue : value}
            </p>
          )}
          {trend && !loading && (
            <div className="flex items-center gap-1.5">
              {trend.positive !== undefined && (
                trend.positive ? (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                )
              )}
              <span
                className={cn(
                  "text-sm font-medium",
                  trend.positive ? "text-green-600" : "text-red-600"
                )}
              >
                {trend.positive ? "+" : ""}
                {trend.value}%
              </span>
              {trend.label && (
                <span className="text-sm text-gray-400">{trend.label}</span>
              )}
            </div>
          )}
        </div>
        <div className={cn(
          "p-3 rounded-xl transition-transform duration-300 group-hover:scale-110",
          colors.iconBg
        )}>
          <Icon className={cn("h-6 w-6", colors.icon)} />
        </div>
      </div>
    </div>
  );
}

export interface MiniStatProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  variant?: "blue" | "green" | "yellow" | "red" | "purple" | "gray";
}

export function MiniStat({ label, value, icon: Icon, variant = "gray" }: MiniStatProps) {
  const colors = variants[variant];

  return (
    <div className="flex items-center gap-3">
      {Icon && (
        <div className={cn("p-2 rounded-lg", colors.iconBg)}>
          <Icon className={cn("h-4 w-4", colors.icon)} />
        </div>
      )}
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
