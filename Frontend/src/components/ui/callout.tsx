import { cn } from "@/lib/utils";
import { AlertCircle, Info, Lightbulb, AlertTriangle } from "lucide-react";

interface CalloutProps {
  type: 'warning' | 'tip' | 'info' | 'important';
  children: React.ReactNode;
  className?: string;
}

/**
 * Premium callout boxes for highlighting important content
 * Similar to Notion, Obsidian, and modern documentation sites
 */
export const Callout = ({ type, children, className }: CalloutProps) => {
  const styles = {
    warning: {
      bg: "bg-yellow-50 dark:bg-yellow-950/30",
      border: "border-yellow-400/50 dark:border-yellow-600/50",
      icon: <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-500" />,
      title: "Warning"
    },
    tip: {
      bg: "bg-green-50 dark:bg-green-950/30",
      border: "border-green-400/50 dark:border-green-600/50",
      icon: <Lightbulb className="w-4 h-4 text-green-600 dark:text-green-500" />,
      title: "Tip"
    },
    info: {
      bg: "bg-blue-50 dark:bg-blue-950/30",
      border: "border-blue-400/50 dark:border-blue-600/50",
      icon: <Info className="w-4 h-4 text-blue-600 dark:text-blue-500" />,
      title: "Info"
    },
    important: {
      bg: "bg-red-50 dark:bg-red-950/30",
      border: "border-red-400/50 dark:border-red-600/50",
      icon: <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-500" />,
      title: "Important"
    }
  };

  const style = styles[type];

  return (
    <div 
      className={cn(
        "rounded-lg border-l-4 p-4 my-4",
        style.bg,
        style.border,
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5">
          {style.icon}
        </div>
        <div className="flex-1 text-sm leading-relaxed">
          <div className="font-semibold mb-1">{style.title}</div>
          <div className="text-foreground/90">{children}</div>
        </div>
      </div>
    </div>
  );
};
