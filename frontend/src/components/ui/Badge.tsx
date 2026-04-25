import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps {
  variant?:
    | "default"
    | "success"
    | "warning"
    | "danger"
    | "info"
    | "purple"
    | "outline";
  size?: "sm" | "md";
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

const variants = {
  default: "bg-gray-100 text-gray-800 border-gray-200",
  success: "bg-green-50 text-green-700 border-green-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
  info: "bg-blue-50 text-blue-700 border-blue-200",
  purple: "bg-purple-50 text-purple-700 border-purple-200",
  outline: "bg-white text-gray-700 border-gray-300",
};

const sizes = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export function Badge({
  variant = "default",
  size = "sm",
  icon,
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-medium rounded-full border",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
}

export interface RiskBadgeProps {
  tier: "HIGH" | "MEDIUM" | "LOW";
  size?: "sm" | "md";
  showIcon?: boolean;
}

export function RiskBadge({ tier, size = "sm", showIcon = true }: RiskBadgeProps) {
  const config = {
    HIGH: { variant: "danger" as const, label: "High Risk" },
    MEDIUM: { variant: "warning" as const, label: "Medium Risk" },
    LOW: { variant: "success" as const, label: "Low Risk" },
  };

  const { variant, label } = config[tier];

  return (
    <Badge variant={variant} size={size}>
      {showIcon && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full",
            tier === "HIGH" && "bg-red-500",
            tier === "MEDIUM" && "bg-amber-500",
            tier === "LOW" && "bg-green-500"
          )}
        />
      )}
      {tier}
    </Badge>
  );
}

export interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

const statusVariants: Record<string, "success" | "warning" | "danger" | "info" | "default"> = {
  APPROVED: "success",
  COMPLETED: "success",
  REJECTED: "danger",
  FAILED: "danger",
  IN_REVIEW: "info",
  AI_VERIFIED_PENDING_HUMAN: "info",
  PENDING: "warning",
  SUBMITTED: "warning",
};

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const variant = statusVariants[status] || "default";
  const label = status.replace(/_/g, " ");

  return (
    <Badge variant={variant} size={size}>
      {label}
    </Badge>
  );
}
