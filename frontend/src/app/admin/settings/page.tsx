"use client";

import { useState } from "react";
import { Settings, Save, Bell, Shield, Database, Mail, Clock, ToggleLeft, ToggleRight } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

interface SettingToggleProps {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}

function SettingToggle({ label, description, enabled, onToggle }: SettingToggleProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-100 last:border-0">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={onToggle}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
          enabled ? "bg-purple-600" : "bg-gray-200"
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm",
            enabled ? "translate-x-6" : "translate-x-1"
          )}
        />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { success } = useToast();
  const [settings, setSettings] = useState({
    emailNotifications: true,
    aiAutoProcess: true,
    requireTwoFactor: false,
    maintenanceMode: false,
    debugMode: false,
    sessionTimeout: "30",
    maxUploadSize: "10",
    retentionDays: "90",
  });

  const handleToggle = (key: keyof typeof settings) => {
    setSettings((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleInputChange = (key: keyof typeof settings, value: string) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = () => {
    success("Settings saved", "Your changes have been saved successfully");
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
          <p className="text-gray-500 mt-1">Configure application settings and preferences</p>
        </div>
        <Button onClick={handleSave} icon={<Save className="h-4 w-4" />}>
          Save Changes
        </Button>
      </div>

      {/* Notification Settings */}
      <Card padding="none">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-purple-500" />
              Notifications
            </div>
          }
          description="Configure how you receive notifications"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <SettingToggle
            label="Email Notifications"
            description="Receive email alerts for important events"
            enabled={settings.emailNotifications}
            onToggle={() => handleToggle("emailNotifications")}
          />
        </CardContent>
      </Card>

      {/* AI Settings */}
      <Card padding="none">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-purple-500" />
              AI Processing
            </div>
          }
          description="Configure AI document verification settings"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <SettingToggle
            label="Auto-Process Documents"
            description="Automatically start AI verification when documents are uploaded"
            enabled={settings.aiAutoProcess}
            onToggle={() => handleToggle("aiAutoProcess")}
          />
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card padding="none">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-purple-500" />
              Security
            </div>
          }
          description="Security and authentication settings"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <SettingToggle
            label="Require Two-Factor Authentication"
            description="Require 2FA for all user accounts"
            enabled={settings.requireTwoFactor}
            onToggle={() => handleToggle("requireTwoFactor")}
          />
          <div className="py-4 border-b border-gray-100">
            <label className="block">
              <span className="font-medium text-gray-900">Session Timeout (minutes)</span>
              <p className="text-sm text-gray-500 mb-2">
                Automatically log out users after inactivity
              </p>
              <Input
                type="number"
                value={settings.sessionTimeout}
                onChange={(e) => handleInputChange("sessionTimeout", e.target.value)}
                className="max-w-xs"
              />
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Storage Settings */}
      <Card padding="none">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-purple-500" />
              Storage
            </div>
          }
          description="File storage and retention settings"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <div className="py-4 border-b border-gray-100">
            <label className="block">
              <span className="font-medium text-gray-900">Max Upload Size (MB)</span>
              <p className="text-sm text-gray-500 mb-2">
                Maximum file size for document uploads
              </p>
              <Input
                type="number"
                value={settings.maxUploadSize}
                onChange={(e) => handleInputChange("maxUploadSize", e.target.value)}
                className="max-w-xs"
              />
            </label>
          </div>
          <div className="py-4">
            <label className="block">
              <span className="font-medium text-gray-900">Data Retention (days)</span>
              <p className="text-sm text-gray-500 mb-2">
                How long to keep completed request data
              </p>
              <Input
                type="number"
                value={settings.retentionDays}
                onChange={(e) => handleInputChange("retentionDays", e.target.value)}
                className="max-w-xs"
              />
            </label>
          </div>
        </CardContent>
      </Card>

      {/* System Settings */}
      <Card padding="none">
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-purple-500" />
              System
            </div>
          }
          description="System maintenance and debugging"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <SettingToggle
            label="Maintenance Mode"
            description="Put the application in maintenance mode (users cannot access)"
            enabled={settings.maintenanceMode}
            onToggle={() => handleToggle("maintenanceMode")}
          />
          <SettingToggle
            label="Debug Mode"
            description="Enable detailed logging for troubleshooting"
            enabled={settings.debugMode}
            onToggle={() => handleToggle("debugMode")}
          />
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card padding="none" className="border-red-200">
        <CardHeader
          title={
            <span className="text-red-600">Danger Zone</span>
          }
          description="Irreversible and destructive actions"
          className="px-6 pt-6 bg-red-50"
        />
        <CardContent className="px-6 pb-6">
          <div className="flex items-center justify-between py-4">
            <div>
              <p className="font-medium text-gray-900">Clear All Logs</p>
              <p className="text-sm text-gray-500">Permanently delete all activity logs</p>
            </div>
            <Button variant="danger" size="sm">
              Clear Logs
            </Button>
          </div>
          <div className="flex items-center justify-between py-4 border-t border-gray-100">
            <div>
              <p className="font-medium text-gray-900">Reset Database</p>
              <p className="text-sm text-gray-500">Reset all data to factory defaults</p>
            </div>
            <Button variant="danger" size="sm">
              Reset Database
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
