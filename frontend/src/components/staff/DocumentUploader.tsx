"use client";

import { useState, useCallback } from "react";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface DocumentUploaderProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  disabled?: boolean;
  error?: string;
  accept?: string;
}

export default function DocumentUploader({
  onFileSelect,
  selectedFile,
  disabled = false,
  error,
  accept = ".pdf,.jpg,.jpeg,.png",
}: DocumentUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (validateFile(file)) {
          onFileSelect(file);
        }
      }
    },
    [disabled, onFileSelect]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (validateFile(file)) {
        onFileSelect(file);
      }
    }
  };

  const validateFile = (file: File): boolean => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/jpg",
      "image/png",
    ];

    if (file.size > maxSize) {
      alert("File size must be less than 10MB");
      return false;
    }

    if (!allowedTypes.includes(file.type)) {
      alert("Only PDF, JPG, and PNG files are allowed");
      return false;
    }

    return true;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const removeFile = () => {
    onFileSelect(null);
  };

  return (
    <div className="space-y-2">
      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
            isDragOver
              ? "border-blue-500 bg-blue-50"
              : error
              ? "border-red-300 bg-red-50"
              : "border-gray-300 hover:border-gray-400",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <Upload
            className={cn(
              "mx-auto h-12 w-12 mb-4",
              isDragOver ? "text-blue-500" : "text-gray-400"
            )}
          />
          <p className="text-sm text-gray-600 mb-2">
            Drag and drop your document here, or{" "}
            <label
              className={cn(
                "text-blue-600 hover:text-blue-700 cursor-pointer",
                disabled && "pointer-events-none"
              )}
            >
              browse
              <input
                type="file"
                className="hidden"
                accept={accept}
                onChange={handleFileChange}
                disabled={disabled}
              />
            </label>
          </p>
          <p className="text-xs text-gray-500">
            Supported formats: PDF, JPG, PNG (max 10MB)
          </p>
        </div>
      ) : (
        <div
          className={cn(
            "border rounded-lg p-4 flex items-center justify-between",
            error ? "border-red-300 bg-red-50" : "border-green-300 bg-green-50"
          )}
        >
          <div className="flex items-center space-x-3">
            <div
              className={cn(
                "p-2 rounded-lg",
                error ? "bg-red-100" : "bg-green-100"
              )}
            >
              {error ? (
                <AlertCircle className="h-6 w-6 text-red-600" />
              ) : (
                <FileText className="h-6 w-6 text-green-600" />
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {!error && (
              <CheckCircle className="h-5 w-5 text-green-500" />
            )}
            <button
              type="button"
              onClick={removeFile}
              disabled={disabled}
              className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 flex items-center gap-1">
          <AlertCircle className="h-4 w-4" />
          {error}
        </p>
      )}
    </div>
  );
}
