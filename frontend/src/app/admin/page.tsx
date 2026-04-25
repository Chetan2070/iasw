"use client";

import { useEffect, useState } from "react";
import { Database, RefreshCw, ChevronDown, ChevronRight, Search, Table2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface TableData {
  columns: string[];
  rows: Record<string, any>[];
}

export default function AdminPage() {
  const [tables, setTables] = useState<Record<string, TableData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(
    new Set(["pending_requests", "customers"])
  );
  const [searchQuery, setSearchQuery] = useState("");

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

  const filteredTables = Object.entries(tables).filter(([tableName]) =>
    tableName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalRows = Object.values(tables).reduce((sum, t) => sum + t.rows.length, 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Database Viewer</h1>
          <p className="text-gray-500 mt-1">
            {Object.keys(tables).length} tables, {totalRows} total rows
          </p>
        </div>
        <Button
          onClick={fetchData}
          loading={loading}
          icon={<RefreshCw className={cn("h-5 w-5", loading && "animate-spin")} />}
          className="bg-purple-600 hover:bg-purple-700"
        >
          Refresh
        </Button>
      </div>

      {/* Search */}
      <Card padding="md">
        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search tables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpandedTables(new Set(Object.keys(tables)))}
            >
              Expand All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpandedTables(new Set())}
            >
              Collapse All
            </Button>
          </div>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="bg-red-50 border-red-200">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Database className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <h3 className="font-medium text-red-800">{error}</h3>
              <p className="text-sm text-red-700 mt-1">
                Make sure the backend is running and the /admin/tables endpoint exists.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Loading State */}
      {loading && Object.keys(tables).length === 0 && (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} padding="none">
              <div className="p-4 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-5 w-5" />
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-5 w-16 ml-2" />
                </div>
              </div>
              <div className="p-4">
                <Skeleton className="h-32 w-full" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Tables */}
      <div className="space-y-4">
        {filteredTables.map(([tableName, tableData]) => (
          <Card key={tableName} padding="none" className="overflow-hidden">
            <button
              onClick={() => toggleTable(tableName)}
              className="w-full flex items-center justify-between px-6 py-4 bg-gray-50 hover:bg-gray-100 transition-colors border-b border-gray-200"
            >
              <div className="flex items-center gap-3">
                {expandedTables.has(tableName) ? (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-500" />
                )}
                <Table2 className="h-5 w-5 text-purple-500" />
                <span className="font-semibold text-gray-900">{tableName}</span>
                <Badge variant="purple" size="sm">
                  {tableData.rows.length} rows
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="default" size="sm">
                  {tableData.columns.length} columns
                </Badge>
              </div>
            </button>

            {expandedTables.has(tableName) && (
              <div className="overflow-x-auto animate-fade-in">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {tableData.columns.map((col) => (
                        <th
                          key={col}
                          className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {tableData.rows.length === 0 ? (
                      <tr>
                        <td
                          colSpan={tableData.columns.length}
                          className="px-4 py-8 text-center text-gray-500"
                        >
                          <div className="flex flex-col items-center">
                            <Database className="h-8 w-8 text-gray-300 mb-2" />
                            <span>No data in this table</span>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      tableData.rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                          {tableData.columns.map((col) => (
                            <td
                              key={col}
                              className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap max-w-xs truncate"
                              title={formatValue(row[col])}
                            >
                              {formatValue(row[col]) === "NULL" ? (
                                <span className="text-gray-400 italic">NULL</span>
                              ) : (
                                formatValue(row[col])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* No Results */}
      {searchQuery && filteredTables.length === 0 && (
        <Card className="text-center py-12">
          <Database className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No tables found</h3>
          <p className="text-gray-500 mt-1">
            No tables match "{searchQuery}"
          </p>
        </Card>
      )}
    </div>
  );
}
