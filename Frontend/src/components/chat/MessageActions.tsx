import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  RotateCw, 
  Sparkles, 
  Layers, 
  RefreshCw,
  ArrowRight 
} from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageActionsProps {
  onContinue?: () => void;
  onRewrite?: () => void;
  onSummarize?: () => void;
  onExplainSimply?: () => void;
  className?: string;
}

export const MessageActions = ({ 
  onContinue, 
  onRewrite, 
  onSummarize, 
  onExplainSimply,
  className 
}: MessageActionsProps) => {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (action: string, callback?: () => void) => {
    if (!callback) return;
    setLoading(action);
    try {
      await callback();
    } finally {
      setTimeout(() => setLoading(null), 500);
    }
  };

  return (
    <TooltipProvider delayDuration={300}>
      <div className={cn(
        "flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
        className
      )}>
        {/* Continue Writing */}
        {onContinue && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleAction('continue', onContinue)}
                disabled={loading === 'continue'}
                className="h-7 px-2.5 text-xs hover:bg-accent/50"
              >
                {loading === 'continue' ? (
                  <RotateCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <ArrowRight className="w-3 h-3 mr-1" />
                )}
                Continue
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Continue the response
            </TooltipContent>
          </Tooltip>
        )}

        {/* Rewrite */}
        {onRewrite && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleAction('rewrite', onRewrite)}
                disabled={loading === 'rewrite'}
                className="h-7 px-2.5 text-xs hover:bg-accent/50"
              >
                {loading === 'rewrite' ? (
                  <RotateCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3 mr-1" />
                )}
                Rewrite
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Get a different response
            </TooltipContent>
          </Tooltip>
        )}

        {/* Summarize */}
        {onSummarize && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleAction('summarize', onSummarize)}
                disabled={loading === 'summarize'}
                className="h-7 px-2.5 text-xs hover:bg-accent/50"
              >
                {loading === 'summarize' ? (
                  <RotateCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Layers className="w-3 h-3 mr-1" />
                )}
                Summarize
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Get a brief summary
            </TooltipContent>
          </Tooltip>
        )}

        {/* Explain Simply */}
        {onExplainSimply && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleAction('explain', onExplainSimply)}
                disabled={loading === 'explain'}
                className="h-7 px-2.5 text-xs hover:bg-accent/50"
              >
                {loading === 'explain' ? (
                  <RotateCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3 mr-1" />
                )}
                Explain
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Explain in simple terms
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TooltipProvider>
  );
};
