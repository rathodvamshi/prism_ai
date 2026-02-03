import { FileCode, Eye, Copy, Download, Check } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface VirtualFileCardProps {
    filename: string;
    language: string;
    code: string;
    onOpen: (code: string, language: string, filename: string) => void;
}

export const VirtualFileCard = ({ filename, language, code, onOpen }: VirtualFileCardProps) => {
    const [copied, setCopied] = useState(false);
    const lineCount = code.split("\n").length;

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownload = (e: React.MouseEvent) => {
        e.stopPropagation();
        const blob = new Blob([code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div
            className="group bg-card/40 border border-border/40 hover:border-primary/20 backdrop-blur-sm rounded-lg p-2.5 sm:p-3 my-2 cursor-pointer transition-all hover:bg-card/60 hover:shadow-sm w-full max-w-full"
            onClick={() => onOpen(code, language, filename)}
        >
            <div className="flex items-center gap-2 sm:gap-3">
                {/* Icon Container */}
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 border border-primary/5">
                    <FileCode className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                        <h4 className="text-xs sm:text-sm font-medium text-foreground/90 truncate max-w-[120px] sm:max-w-none">{filename}</h4>
                        <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 bg-muted/30 px-1 sm:px-1.5 py-0.5 rounded tracking-wide">
                            {language}
                        </span>
                    </div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground/70 truncate flex items-center gap-1 sm:gap-1.5 mt-0.5">
                        <span>{lineCount} lines</span>
                        <span className="w-1 h-1 rounded-full bg-border" />
                        <span className="hidden sm:inline group-hover:text-primary/80 transition-colors">Click to open</span>
                        <span className="sm:hidden text-primary/70">Tap to open</span>
                    </p>
                </div>

                {/* Actions (Visible on hover) */}
                <div className="flex items-center gap-0.5 sm:gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={handleCopy}
                        className="h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                        title="Copy Code"
                    >
                        {copied ? <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-green-500" /> : <Copy className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={handleDownload}
                        className="h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                        title="Download File"
                    >
                        <Download className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                    </Button>
                </div>
            </div>
        </div>
    );
};
