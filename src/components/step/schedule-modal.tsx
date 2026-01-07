"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Calendar, Clock, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScheduleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  issueId: string;
  onSchedule: (scheduledTime: Date) => Promise<void>;
  isScheduling?: boolean;
}

export function ScheduleModal({
  open,
  onOpenChange,
  issueId,
  onSchedule,
  isScheduling = false,
}: ScheduleModalProps) {
  // Default to 5:00 AM ET next day
  const getDefaultDateTime = () => {
    const now = new Date();
    // Convert to ET
    const etNow = new Date(
      now.toLocaleString("en-US", { timeZone: "America/New_York" })
    );

    // Set to next day at 5:00 AM
    const tomorrow = new Date(etNow);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(5, 0, 0, 0);

    return tomorrow;
  };

  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedTime, setSelectedTime] = useState<string>("05:00");
  const [error, setError] = useState<string | null>(null);

  // Initialize with default values when modal opens
  useEffect(() => {
    if (open) {
      const defaultDate = getDefaultDateTime();
      setSelectedDate(defaultDate.toISOString().split("T")[0]);
      setSelectedTime("05:00");
      setError(null);
    }
  }, [open]);

  const handleSchedule = async () => {
    setError(null);

    if (!selectedDate || !selectedTime) {
      setError("Please select both date and time");
      return;
    }

    // Parse the selected date and time
    const [year, month, day] = selectedDate.split("-").map(Number);
    const [hours, minutes] = selectedTime.split(":").map(Number);

    // Create the scheduled time in ET
    // Note: We're creating a Date that represents the ET time
    const scheduledDate = new Date(year, month - 1, day, hours, minutes, 0, 0);

    // Validate that the time is in the future
    const now = new Date();
    if (scheduledDate <= now) {
      setError("Scheduled time must be in the future");
      return;
    }

    try {
      await onSchedule(scheduledDate);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to schedule");
    }
  };

  const formatPreviewTime = () => {
    if (!selectedDate || !selectedTime) return "";

    const [year, month, day] = selectedDate.split("-").map(Number);
    const [hours, minutes] = selectedTime.split(":").map(Number);
    const date = new Date(year, month - 1, day, hours, minutes);

    return date.toLocaleString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Schedule Newsletter
          </DialogTitle>
          <DialogDescription>
            Schedule this newsletter to be sent via Mautic at a specific time.
            Default is 5:00 AM ET the next day.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Issue ID display */}
          <div className="text-sm text-muted-foreground">
            Issue ID: <span className="font-mono">{issueId}</span>
          </div>

          {/* Date picker */}
          <div className="space-y-2">
            <Label htmlFor="schedule-date" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Date
            </Label>
            <Input
              id="schedule-date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className="w-full"
            />
          </div>

          {/* Time picker */}
          <div className="space-y-2">
            <Label htmlFor="schedule-time" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Time (Eastern Time)
            </Label>
            <Input
              id="schedule-time"
              type="time"
              value={selectedTime}
              onChange={(e) => setSelectedTime(e.target.value)}
              className="w-full"
            />
          </div>

          {/* Preview */}
          {selectedDate && selectedTime && (
            <div className="p-3 bg-muted/50 rounded-lg">
              <p className="text-sm">
                <span className="text-muted-foreground">Send at: </span>
                <span className="font-medium">{formatPreviewTime()}</span>
              </p>
            </div>
          )}

          {/* Quick time buttons */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Quick select:</Label>
            <div className="flex flex-wrap gap-2">
              {["05:00", "06:00", "07:00", "08:00"].map((time) => (
                <Button
                  key={time}
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedTime(time)}
                  className={cn(
                    "text-xs",
                    selectedTime === time && "bg-primary text-primary-foreground"
                  )}
                >
                  {time.replace(":00", "")} AM
                </Button>
              ))}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isScheduling}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSchedule}
            disabled={isScheduling || !selectedDate || !selectedTime}
            className="gap-2"
          >
            {isScheduling ? (
              <>
                <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Scheduling...
              </>
            ) : (
              <>
                <Calendar className="h-4 w-4" />
                Schedule Send
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Helper component for displaying scheduling status
interface SchedulingStatusBannerProps {
  scheduledTime: string;
  onCancel?: () => void;
  isCancelling?: boolean;
}

export function SchedulingStatusBanner({
  scheduledTime,
  onCancel,
  isCancelling = false,
}: SchedulingStatusBannerProps) {
  const formatScheduledTime = (timeString: string) => {
    const date = new Date(timeString);
    return date.toLocaleString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  return (
    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100">
            <Calendar className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <p className="font-medium text-emerald-900">Newsletter Scheduled</p>
            <p className="text-sm text-emerald-700">
              Scheduled via Mautic for {formatScheduledTime(scheduledTime)}
            </p>
          </div>
        </div>
        {onCancel && (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isCancelling}
            className="border-emerald-300 text-emerald-700 hover:bg-emerald-100"
          >
            {isCancelling ? "Cancelling..." : "Cancel Schedule"}
          </Button>
        )}
      </div>
    </div>
  );
}
