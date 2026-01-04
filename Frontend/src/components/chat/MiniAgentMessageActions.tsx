
import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, Edit2 } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface MiniAgentMessageActionsProps {
    isUser: boolean;
    text: string;
    onEdit?: () => void;
    onRegenerate?: () => void;
}

export const MiniAgentMessageActions = ({
    isUser,
    text,
    onEdit,
    onRegenerate
}: MiniAgentMessageActionsProps) => {
    const [copied, setCopied] = useState(false);
    const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleFeedback = (type: 'up' | 'down') => {
        setFeedback(prev => prev === type ? null : type);
    };

    return (
        <div className={cn(
            "flex items-center gap-1 mt-1.5 px-1 opacity-100 transition-all duration-200 ease-in-out pb-1",
            isUser ? "justify-end" : "justify-start"
        )}>
            {isUser ? (
                <>
                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="p-1 rounded-md text-muted-foreground/40 hover:text-primary hover:bg-primary/5 transition-colors"
                                    onClick={onEdit}
                                >
                                    <Edit2 className="w-3.5 h-3.5" />
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Edit</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.95 }}
                                    className={cn(
                                        "p-1 rounded-md transition-colors",
                                        copied ? "text-green-500 bg-green-500/10" : "text-muted-foreground/40 hover:text-primary hover:bg-primary/5"
                                    )}
                                    onClick={handleCopy}
                                >
                                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">
                                {copied ? "Copied!" : "Copy"}
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </>
            ) : (
                <>
                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.95 }}
                                    className={cn(
                                        "p-1 rounded-md transition-colors",
                                        copied ? "text-green-500 bg-green-500/10" : "text-muted-foreground/40 hover:text-primary hover:bg-primary/5"
                                    )}
                                    onClick={handleCopy}
                                >
                                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">
                                {copied ? "Copied!" : "Copy"}
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="p-1 rounded-md text-muted-foreground/40 hover:text-primary hover:bg-primary/5 transition-colors"
                                    onClick={onRegenerate}
                                >
                                    <RefreshCw className="w-3.5 h-3.5" />
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Regenerate</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <div className="h-3 w-[1px] bg-border/40 mx-1" />

                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1, rotate: -10 }}
                                    whileTap={{ scale: 0.95 }}
                                    className={cn(
                                        "p-1 rounded-md transition-colors",
                                        feedback === 'up' ? "text-green-500 bg-green-500/10" : "text-muted-foreground/40 hover:text-green-500 hover:bg-green-500/10"
                                    )}
                                    onClick={() => handleFeedback('up')}
                                >
                                    <ThumbsUp className={cn("w-3.5 h-3.5", feedback === 'up' && "fill-current")} />
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Helpful</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider delayDuration={200}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <motion.button
                                    whileHover={{ scale: 1.1, rotate: 10 }}
                                    whileTap={{ scale: 0.95 }}
                                    className={cn(
                                        "p-1 rounded-md transition-colors",
                                        feedback === 'down' ? "text-red-500 bg-red-500/10" : "text-muted-foreground/40 hover:text-red-500 hover:bg-red-500/10"
                                    )}
                                    onClick={() => handleFeedback('down')}
                                >
                                    <ThumbsDown className={cn("w-3.5 h-3.5", feedback === 'down' && "fill-current")} />
                                </motion.button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Not Helpful</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </>
            )}
        </div>
    );
};
