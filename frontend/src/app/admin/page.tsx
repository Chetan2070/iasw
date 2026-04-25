"use client";

import { useEffect, useState } from "react";
import { Database, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface TableData {
  columns: string[];
  rows: Record<string, any>[];
}

export default function AdminPage() {
  const [tables, setTables] = useState<Record<string, TableData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set(["pending_requests", "customers"]));

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/admin/tables`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setTables(data);
    } catch (err: any) {
      console.error("Failed to fetch tables:", err);
      setError(err.message || "Failed to load database tables");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return "NULL";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    return String(value);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Database className="h-8 w-8 text-purple-600" />
            <h1 className="text-2xl font-bold text-gray-900">Database Viewer</h1>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
            <p className="text-sm mt-1">Make sure the backend is running and the /admin/tables endpoint exists.</p>
          </div>
        )}

        <div className="space-y-4">
          {Object.entries(tables).map(([tableName, tableData]) => (
            <div key={tableName} className="bg-white rounded-lg shadow overflow-hidden">
              <button
                onClick={() => toggleTable(tableName)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {expandedTables.has(tableName) ? (
                    <ChevronDown className="h-5 w-5 text-gray-600" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-600" />
                  )}
                  <span className="font-semibold text-gray-900">{tableName}</span>
                  <span className="text-sm text-gray-500">({tableData.rows.length} rows)</span>
                </div>
              </button>

              {expandedTables.has(tableName) && (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        {tableData.columns.map((col) => (
                          <th
                            key={col}
                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {tableData.rows.length === 0 ? (
                        <tr>
                          <td
                            colSpan={tableData.columns.length}
                            className="px-4 py-4 text-center text-gray-500"
                          >
                            No data
                          </td>
                        </tr>
                      ) : (
                        tableData.rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            {tableData.columns.map((col) => (
                              <td
                                key={col}
                                className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap max-w-xs truncate"
                                title={formatValue(row[col])}
                              >
                                {formatValue(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>

        {loading && Object.keys(tables).length === 0 && (
          <div className="text-center py-12">
            <RefreshCw className="h-8 w-8 text-purple-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Loading database tables...</p>
          </div>
        )}
      </div>
    </div>
  );
}
