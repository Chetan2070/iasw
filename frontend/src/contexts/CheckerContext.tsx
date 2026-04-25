"use client";

import { createContext, useContext, useState, ReactNode, useEffect } from "react";

interface CheckerContextType {
  checkerId: string;
  checkerName: string;
  setChecker: (id: string, name: string) => void;
}

const CheckerContext = createContext<CheckerContextType | undefined>(undefined);

export function CheckerProvider({ children }: { children: ReactNode }) {
  // Load from localStorage if available, otherwise use defaults
  const [checkerId, setCheckerId] = useState("CHK-001");
  const [checkerName, setCheckerName] = useState("Default Checker");

  // Load from localStorage on mount (client-side only)
  useEffect(() => {
    const savedId = localStorage.getItem("checkerId");
    const savedName = localStorage.getItem("checkerName");
    if (savedId) setCheckerId(savedId);
    if (savedName) setCheckerName(savedName);
  }, []);

  const setChecker = (id: string, name: string) => {
    setCheckerId(id);
    setCheckerName(name);
    // Persist to localStorage
    localStorage.setItem("checkerId", id);
    localStorage.setItem("checkerName", name);
  };

  return (
    <CheckerContext.Provider value={{ checkerId, checkerName, setChecker }}>
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
