/**
 * Tests for utility functions
 */

import { cn, formatDate, formatPercentage, getTimeAgo } from "@/lib/utils";

describe("cn (className merge utility)", () => {
  it("should merge class names", () => {
    expect(cn("class1", "class2")).toBe("class1 class2");
  });

  it("should handle conditional classes", () => {
    expect(cn("base", true && "active", false && "hidden")).toBe("base active");
  });

  it("should handle undefined values", () => {
    expect(cn("base", undefined, null, "end")).toBe("base end");
  });

  it("should merge Tailwind classes correctly", () => {
    expect(cn("p-4", "p-2")).toBe("p-2");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("should handle arrays", () => {
    expect(cn(["class1", "class2"])).toBe("class1 class2");
  });

  it("should handle objects", () => {
    expect(cn({ active: true, disabled: false })).toBe("active");
  });
});

describe("formatDate", () => {
  it("should format ISO date string", () => {
    const date = "2024-03-15T10:30:00Z";
    const result = formatDate(date);
    expect(result).toContain("2024");
  });

  it("should handle different date formats", () => {
    const date = "2024-01-01T00:00:00.000Z";
    const result = formatDate(date);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("formatPercentage", () => {
  it("should format decimal as percentage", () => {
    expect(formatPercentage(0.95)).toBe("95%");
    expect(formatPercentage(0.5)).toBe("50%");
    expect(formatPercentage(1.0)).toBe("100%");
  });

  it("should round to nearest integer", () => {
    expect(formatPercentage(0.956)).toBe("96%");
    expect(formatPercentage(0.954)).toBe("95%");
  });

  it("should handle null values", () => {
    expect(formatPercentage(null)).toBe("N/A");
  });

  it("should handle undefined values", () => {
    expect(formatPercentage(undefined)).toBe("N/A");
  });

  it("should handle zero", () => {
    expect(formatPercentage(0)).toBe("0%");
  });
});

describe("getTimeAgo", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("should return 'Just now' for very recent times", () => {
    const now = new Date();
    jest.setSystemTime(now);

    const recentDate = new Date(now.getTime() - 30000).toISOString(); // 30 seconds ago
    expect(getTimeAgo(recentDate)).toBe("Just now");
  });

  it("should return minutes ago", () => {
    const now = new Date();
    jest.setSystemTime(now);

    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60000).toISOString();
    expect(getTimeAgo(fiveMinutesAgo)).toBe("5m ago");
  });

  it("should return hours ago", () => {
    const now = new Date();
    jest.setSystemTime(now);

    const twoHoursAgo = new Date(now.getTime() - 2 * 3600000).toISOString();
    expect(getTimeAgo(twoHoursAgo)).toBe("2h ago");
  });

  it("should return days ago", () => {
    const now = new Date();
    jest.setSystemTime(now);

    const threeDaysAgo = new Date(now.getTime() - 3 * 86400000).toISOString();
    expect(getTimeAgo(threeDaysAgo)).toBe("3d ago");
  });
});
