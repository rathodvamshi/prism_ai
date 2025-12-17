import { motion } from "framer-motion";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";

// State machine for confirmation card
export enum ActionCardState {
  IDLE = "idle",
  ASK_CONFIRM = "ask_confirm",
  CONFIRMED = "confirmed",
  CANCELLED = "cancelled",
  TIME_PASSED = "time_passed",
  AUTO_DISMISSED = "auto_dismissed",
  RESCHEDULING = "rescheduling",
}

interface ActionCardProps {
  state: ActionCardState;
  taskDescription?: string;
  dueDate?: string;
  dueDateHumanReadable?: string;
  confirmedAt?: string;
  isDuplicate?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
  onReschedule?: () => void;
}

export const ActionCard = ({
  state,
  taskDescription = "Task",
  dueDate,
  dueDateHumanReadable,
  confirmedAt,
  isDuplicate = false,
  onConfirm,
  onCancel,
  onReschedule,
}: ActionCardProps) => {
  // Auto-dismissed state
  if (state === ActionCardState.AUTO_DISMISSED) {
    return (
      <motion.div 
        className="mt-2 text-[11px] sm:text-xs"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <button
          onClick={onReschedule}
          className="text-blue-600 dark:text-blue-400 hover:underline underline-offset-2"
        >
          ⏰ Auto-dismissed (no response)
        </button>
        <span className="ml-2 text-muted-foreground">• Click to reschedule</span>
      </motion.div>
    );
  }

  // Rescheduling prompt
  if (state === ActionCardState.RESCHEDULING) {
    return (
      <motion.div 
        className="mt-2 sm:mt-3 w-full rounded-md sm:rounded-lg border border-blue-200 dark:border-blue-800/40 bg-blue-50/60 dark:bg-blue-950/30 p-2.5 sm:p-3 text-xs sm:text-sm shadow-sm"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <p className="font-medium text-blue-700 dark:text-blue-400 mb-2">⏰ When do you want to schedule?</p>
        <p className="text-[11px] sm:text-xs text-muted-foreground">Please tell me your preferred date and time.</p>
      </motion.div>
    );
  }

  // Main card for all other states
  return (
    <motion.div 
      className="mt-2 sm:mt-3 w-full rounded-md sm:rounded-lg border border-border bg-card/60 p-2.5 sm:p-3 text-xs sm:text-sm flex flex-col gap-1.5 sm:gap-2 shadow-sm"
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      {/* Header */}
      <div className="font-semibold flex items-center gap-1.5 sm:gap-2">
        <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary" />
        <span>
          {state === ActionCardState.CONFIRMED ? "✅ Reminder Created" : 
           state === ActionCardState.CANCELLED ? "❌ Cancelled" :
           state === ActionCardState.TIME_PASSED ? "⏰ Time Passed" :
           "📋 New Reminder"}
        </span>
      </div>

      {/* Content based on state */}
      {state === ActionCardState.CANCELLED && (
        <motion.div
          className="text-[11px] sm:text-xs text-muted-foreground bg-muted/30 rounded p-2 border border-border/40"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <p>❌ You chose not to set this reminder. Feel free to ask me again with a different time!</p>
        </motion.div>
      )}

      {state === ActionCardState.TIME_PASSED && (
        <motion.div
          className="text-[11px] sm:text-xs bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800/40 rounded p-2.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <p className="text-red-700 dark:text-red-400 font-medium mb-1">⏰ The scheduled time has already passed</p>
          <p className="text-red-600/80 dark:text-red-400/80">Please set a reminder with a future time.</p>
        </motion.div>
      )}

      {state === ActionCardState.ASK_CONFIRM && (
        <>
          <p className="text-[11px] sm:text-xs text-muted-foreground mt-0.5 sm:mt-1 font-medium">
            Does this look right? 👇
          </p>
          <div className="text-foreground mt-0.5 sm:mt-1 bg-gradient-to-r from-blue-50/60 to-cyan-50/60 dark:from-blue-950/30 dark:to-cyan-950/30 border border-blue-200/50 dark:border-blue-800/30 rounded-lg p-2.5 sm:p-3">
            <div className="font-semibold text-sm sm:text-base mb-1.5">{taskDescription}</div>
            <div className="text-[11px] sm:text-xs text-muted-foreground flex items-center gap-1.5">
              <Calendar className="w-3 h-3" />
              <span>{dueDateHumanReadable || dueDate}</span>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-1.5 sm:gap-2 mt-1.5 sm:mt-2">
            <Button
              size="sm"
              variant="default"
              className="bg-green-600 hover:bg-green-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
              onClick={onConfirm}
            >
              <svg className="w-3 h-3 sm:w-3.5 sm:h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              Confirm
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onCancel}
            >
              ❌ No
            </Button>
          </div>
        </>
      )}

      {state === ActionCardState.CONFIRMED && (
        <>
          <motion.div 
            className="mt-0.5 sm:mt-1 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border border-green-200 dark:border-green-800/40 rounded-lg p-3 sm:p-4 shadow-sm"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <div className="flex items-start gap-2 mb-2">
              <motion.div 
                className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-green-500 flex items-center justify-center shadow-md"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
              >
                <svg className="w-4 h-4 sm:w-5 sm:h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </motion.div>
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-bold text-green-700 dark:text-green-400 mb-1">
                  {isDuplicate ? "⚠️ Already Scheduled" : "🎉 Perfect! Your reminder is all set."}
                </p>
                <p className="text-[11px] sm:text-xs text-green-600/80 dark:text-green-400/80">
                  {isDuplicate 
                    ? "This reminder already exists. No duplicate created."
                    : "I'll send an email to your registered address when it's time."
                  }
                </p>
              </div>
            </div>
            
            <div className="space-y-2 mt-3 pt-3 border-t border-green-200/50 dark:border-green-800/30">
              <div className="flex items-start gap-2">
                <span className="text-base sm:text-lg">📝</span>
                <div className="flex-1">
                  <p className="text-[10px] sm:text-xs text-green-600/60 dark:text-green-400/60 uppercase tracking-wide font-medium mb-0.5">Task</p>
                  <p className="text-xs sm:text-sm font-medium text-foreground">{taskDescription}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-2">
                <span className="text-base sm:text-lg">⏰</span>
                <div className="flex-1">
                  <p className="text-[10px] sm:text-xs text-green-600/60 dark:text-green-400/60 uppercase tracking-wide font-medium mb-0.5">Scheduled For</p>
                  <p className="text-xs sm:text-sm font-medium text-foreground">{dueDateHumanReadable || dueDate}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-2">
                <span className="text-base sm:text-lg">📧</span>
                <div className="flex-1">
                  <p className="text-[10px] sm:text-xs text-green-600/60 dark:text-green-400/60 uppercase tracking-wide font-medium mb-0.5">Notification</p>
                  <p className="text-xs sm:text-sm text-foreground/80">Email reminder will be sent to your account</p>
                </div>
              </div>
            </div>
          </motion.div>
          
          <motion.div 
            className="flex items-center justify-between mt-2 px-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.3 }}
          >
            <div className="flex items-center gap-1.5 text-[11px] sm:text-xs text-green-600 dark:text-green-400 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              <span>Active & Scheduled</span>
            </div>
            {confirmedAt && (
              <span className="text-[10px] sm:text-xs text-muted-foreground">
                Confirmed {new Date(confirmedAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
              </span>
            )}
          </motion.div>
        </>
      )}
    </motion.div>
  );
};
