"use client";

import { createContext, useContext, ReactNode } from "react";
import { useAuth } from "./AuthContext";

interface CheckerContextType {
  checkerId: string;
  checkerName: string;
}

const CheckerContext = createContext<CheckerContextType | undefined>(undefined);

export function CheckerProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  // Get checker ID from authenticated user
  // For checker users, use their checker_id field
  // For admin users acting as checker, use their user id
  const checkerId = user?.checker_id || user?.id || "";
  const checkerName = user?.username || "";

  return (
    <CheckerContext.Provider value={{ checkerId, checkerName }}>
      {children}
    </CheckerContext.Provider>
  );
}

export function useChecker() {
  const context = useContext(CheckerContext);
  if (!context) {
    throw new Error("useChecker must be used within a CheckerProvider");
  }
  return context;
}
