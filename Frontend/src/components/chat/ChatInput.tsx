import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Paperclip,
  ChevronDown,
  Mic,
  Send,
  Check,
  Lock,
  Image,
  File,
  Cloud,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Attachment } from "@/types/chat";

interface ChatInputProps {
  onSend: (message: string, attachments?: Attachment[]) => void;
  isLoading?: boolean;
  onOpenApiSettings?: () => void;
  resetSignal?: number; // triggers input clear and focus on new session
}

const models = [
  { id: "gpt-4o-mini", name: "GPT-4o Mini", available: true },
  { id: "gpt-4o", name: "GPT-4o", available: false },
  { id: "claude-3", name: "Claude 3", available: false },
];

export const ChatInput = ({ onSend, isLoading, onOpenApiSettings, resetSignal }: ChatInputProps) => {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerIndex, setViewerIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [selectedModel, setSelectedModel] = useState(models[0]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const filesInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const driveInputRef = useRef<HTMLInputElement>(null);
  const isMobile = useIsMobile();

  // Auto-resize when text reaches width and grows up to 200px
  const autoResize = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to get accurate scrollHeight
    textarea.style.height = "auto";

    // Calculate new height - starts growing when text wraps
    const minHeight = 52;
    const maxHeight = 200;

    // Get the scroll height (actual content height)
    let newHeight = Math.max(textarea.scrollHeight, minHeight);

    // Clamp to max height
    newHeight = Math.min(newHeight, maxHeight);

    // Apply the height
    textarea.style.height = `${newHeight}px`;
  }, []);

  // Handle input changes with auto-resize
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Trigger resize after state update
    requestAnimationFrame(() => {
      autoResize();
    });
  }, [autoResize]);

  // Clear and focus on new session
  useEffect(() => {
    if (resetSignal !== undefined) {
      setInput("");
      setAttachments([]);
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.style.height = "52px";
      }
    }
  }, [resetSignal]);

  // Initial setup
  useEffect(() => {
    autoResize();
  }, [autoResize]);

  const handleSubmit = () => {
    if ((!input.trim() && attachments.length === 0) || isLoading) return;

    onSend(input, attachments);
    setInput("");

    // Clean up attachment URLs
    attachments.forEach((a) => {
      if (a.url?.startsWith("blob:")) URL.revokeObjectURL(a.url);
      if (a.thumbUrl?.startsWith("blob:")) URL.revokeObjectURL(a.thumbUrl);
    });
    setAttachments([]);

    // Reset textarea height and focus
    if (textareaRef.current) {
      textareaRef.current.style.height = "52px";
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleModelSelect = (model: typeof models[0]) => {
    if (model.available) {
      setSelectedModel(model);
    } else {
      onOpenApiSettings?.();
    }
  };

  const createImageBitmapSafe = async (blob: Blob) => {
    try {
      // @ts-ignore older Safari may not support
      if (typeof createImageBitmap === "function") {
        // @ts-ignore
        return await createImageBitmap(blob);
      }
    } catch { }
    return new Promise<HTMLImageElement>((resolve, reject) => {
      const img = document.createElement('img');
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = URL.createObjectURL(blob);
    });
  };

  const resizeImage = async (file: File, maxSide: number, quality = 0.8) => {
    const bmp = await createImageBitmapSafe(file);
    const w = (bmp as any).width as number;
    const h = (bmp as any).height as number;
    const ratio = Math.min(1, maxSide / Math.max(w, h));
    const targetW = Math.round(w * ratio);
    const targetH = Math.round(h * ratio);
    const canvas = document.createElement("canvas");
    canvas.width = targetW;
    canvas.height = targetH;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas not supported");
    ctx.drawImage(bmp as any, 0, 0, targetW, targetH);
    const blob: Blob | null = await new Promise((res) => canvas.toBlob(res, "image/jpeg", quality));
    if (!blob) throw new Error("toBlob failed");
    const url = URL.createObjectURL(blob);
    return { url, width: targetW, height: targetH };
  };

  const onPickFiles = async (files: FileList | null) => {
    if (!files) return;
    const pending: Promise<Attachment>[] = Array.from(files).map(async (f) => {
      const isImage = f.type.startsWith("image/");
      if (!isImage) {
        return {
          id: Math.random().toString(36).slice(2),
          type: "file",
          url: URL.createObjectURL(f),
          name: f.name,
          size: f.size,
          mime: f.type,
        } as Attachment;
      }
      try {
        const full = await resizeImage(f, 1600, 0.82);
        const thumb = await resizeImage(f, 480, 0.75);
        return {
          id: Math.random().toString(36).slice(2),
          type: "image",
          url: full.url,
          thumbUrl: thumb.url,
          name: f.name,
          size: f.size,
          mime: f.type,
          width: full.width,
          height: full.height,
        } as Attachment;
      } catch {
        // Fallback to original blob URL
        return {
          id: Math.random().toString(36).slice(2),
          type: "image",
          url: URL.createObjectURL(f),
          name: f.name,
          size: f.size,
          mime: f.type,
        } as Attachment;
      }
    });
    const list = await Promise.all(pending);
    setAttachments((prev) => [...prev, ...list]);
  };

  const openViewer = (index: number) => {
    setViewerIndex(index);
    setZoom(1);
    setViewerOpen(true);
  };

  const viewAttachment = (index: number) => {
    openViewer(index);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="shrink-0 bg-background/95 backdrop-blur-sm sticky bottom-0 left-0 right-0 z-10 w-full"
    >
      <div className="w-full max-w-[800px] mx-auto px-4 lg:px-0 pb-4">
        {/* Attachment Previews */}
        {attachments.length > 0 && (
          <div className="mb-2 px-1">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground/80">Attachments ({attachments.length})</span>
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-destructive transition-colors px-2 py-0.5 rounded-full hover:bg-muted"
                onClick={() => {
                  attachments.forEach((a) => { if (a.url.startsWith("blob:")) URL.revokeObjectURL(a.url); });
                  setAttachments([]);
                }}
              >
                Clear all
              </button>
            </div>
            <div className="flex gap-2 pb-2 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20">
              {attachments.map((a) => (
                <div key={a.id} className="relative group shrink-0">
                  {a.type === "image" ? (
                    <button type="button" onClick={() => viewAttachment(attachments.findIndex(x => x.id === a.id))} className="relative overflow-hidden rounded-xl border border-border/50 shadow-sm transition-transform active:scale-95">
                      <img src={a.url} alt={a.name} className="w-16 h-16 object-cover" />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                    </button>
                  ) : (
                    <div className="w-16 h-16 rounded-xl bg-card border border-border/50 shadow-sm flex flex-col items-center justify-center p-1 gap-1 text-center">
                      <File className="w-5 h-5 text-muted-foreground" />
                      <span className="text-[9px] text-muted-foreground/80 leading-tight line-clamp-2 px-0.5 break-all">{a.name}</span>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => setAttachments((prev) => prev.filter((x) => x.id !== a.id))}
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-destructive-foreground text-[10px] flex items-center justify-center shadow-sm opacity-0 group-hover:opacity-100 transition-opacity scale-90 hover:scale-100"
                    aria-label="Remove"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Responsive Input Container */}
        <div className="relative group w-full">
          <div
            className={cn(
              "relative flex flex-col w-full rounded-2xl sm:rounded-3xl border border-border/60 bg-secondary/30 backdrop-blur-md shadow-sm transition-all duration-200",
              // On hover/focus: slightly stronger border and shadow
              "hover:border-primary/20 hover:shadow-md hover:bg-secondary/40",
              input || attachments.length > 0 ? "border-primary/30 bg-secondary/50 shadow-md" : ""
            )}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }}
            onDrop={(e) => { e.preventDefault(); onPickFiles(e.dataTransfer.files); }}
          >
            {/* Auto-Growing Textarea */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Message Prism..."
              rows={1}
              disabled={isLoading}
              className="w-full min-h-[52px] max-h-[200px] bg-transparent border-0 outline-none resize-none px-4 py-3.5 text-base text-foreground placeholder:text-muted-foreground/50 scrollbar-thin scrollbar-thumb-muted"
            />

            {/* Icons Bar */}
            <div className="flex items-center justify-between px-2 pb-2">
              <div className="flex items-center gap-0.5">
                {/* Add Attachment Button */}
                <DropdownMenu>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors">
                            <div className="relative">
                              <span className="absolute -inset-2 bg-primary/10 rounded-full opacity-0 hover:opacity-100 transition-opacity" />
                              <svg className="w-5 h-5 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                              </svg>
                            </div>
                          </Button>
                        </DropdownMenuTrigger>
                      </TooltipTrigger>
                      <TooltipContent>Add attachments</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <DropdownMenuContent align="start" className="w-56 p-1.5 rounded-xl border border-border/50 bg-popover/95 backdrop-blur-xl shadow-xl animate-in fade-in zoom-in-95 duration-100">
                    <DropdownMenuItem className="gap-3 rounded-lg py-2.5 px-3 cursor-pointer focus:bg-accent/50" onClick={() => galleryInputRef.current?.click()}>
                      <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                        <Image className="w-4 h-4" />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium text-sm">Gallery</span>
                        <span className="text-[10px] text-muted-foreground">Upload images</span>
                      </div>
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-3 rounded-lg py-2.5 px-3 cursor-pointer focus:bg-accent/50" onClick={() => filesInputRef.current?.click()}>
                      <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-500">
                        <File className="w-4 h-4" />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium text-sm">Files</span>
                        <span className="text-[10px] text-muted-foreground">PDF, Docs, spreadsheets</span>
                      </div>
                    </DropdownMenuItem>
                    {!isMobile && (
                      <DropdownMenuItem className="gap-3 rounded-lg py-2.5 px-3 cursor-pointer focus:bg-accent/50" onClick={() => driveInputRef.current?.click()}>
                        <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center text-green-500">
                          <Cloud className="w-4 h-4" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium text-sm">Drive</span>
                          <span className="text-[10px] text-muted-foreground">Connect Google Drive</span>
                        </div>
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Model Selector Pill */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 ml-1 rounded-full text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all border border-transparent hover:border-border/40">
                      <span className="w-2 h-2 rounded-full bg-primary/80 animate-pulse" />
                      {selectedModel.name}
                      <ChevronDown className="w-3 h-3 opacity-50" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-56 p-1 rounded-xl shadow-xl">
                    {models.map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => handleModelSelect(model)}
                        className={cn(
                          "gap-2.5 py-2.5 rounded-lg cursor-pointer",
                          selectedModel.id === model.id ? "bg-accent/50" : ""
                        )}
                        disabled={!model.available}
                      >
                        <div className={cn(
                          "w-4 h-4 rounded-full border flex items-center justify-center",
                          selectedModel.id === model.id ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/30"
                        )}>
                          {selectedModel.id === model.id && <div className="w-2 h-2 rounded-full bg-current" />}
                        </div>
                        <div className="flex flex-col gap-0.5">
                          <span className={cn("text-xs font-medium", !model.available && "opacity-50")}>{model.name}</span>
                          {!model.available && <span className="text-[10px] text-muted-foreground">Coming soon</span>}
                        </div>
                        {model.available && selectedModel.id === model.id && <Check className="w-3.5 h-3.5 ml-auto text-primary" />}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <div className="flex items-center gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                      >
                        <Mic className="w-4 h-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Voice input</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <Button
                  size="icon"
                  className={cn(
                    "h-9 w-9 rounded-full shadow-md transition-all duration-300",
                    (input.trim() || attachments.length > 0)
                      ? "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 hover:shadow-lg"
                      : "bg-muted text-muted-foreground hover:bg-muted/80 cursor-not-allowed"
                  )}
                  onClick={handleSubmit}
                  disabled={!input.trim() && attachments.length === 0 || isLoading}
                >
                  <Send className={cn("w-4 h-4", (input.trim() || attachments.length > 0) && "ml-0.5")} />
                </Button>
              </div>
            </div>
          </div>
        </div>

        <p className="text-[9px] sm:text-xs text-muted-foreground text-center px-2 sm:px-3 py-1 sm:py-2 mb-1.5 sm:mb-3">
          PRISM can make mistakes. Consider checking important information.
        </p>
      </div>

      {/* Image Viewer */}
      <Dialog open={viewerOpen} onOpenChange={setViewerOpen}>
        <DialogContent className="p-0 max-w-full w-full h-dvh bg-black/95 border-0">
          <div className="relative w-full h-full flex items-center justify-center">
            <button type="button" className="absolute top-3 right-3 z-10 text-white/90 text-xl" onClick={() => setViewerOpen(false)}>×</button>
            <button type="button" className="absolute left-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.max(0, i - 1))}>‹</button>
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.min(attachments.filter(a => a.type === 'image').length - 1, i + 1))}>›</button>
            <div className="flex flex-col items-center gap-3">
              <img
                src={attachments.filter(a => a.type === 'image')[viewerIndex]?.url}
                alt="preview"
                style={{ transform: `scale(${zoom})` }}
                className="max-h-[80vh] w-auto object-contain rounded"
              />
              <div className="flex items-center gap-3 text-white/80">
                <Button size="sm" variant="secondary" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}>-</Button>
                <span>{Math.round(zoom * 100)}%</span>
                <Button size="sm" variant="secondary" onClick={() => setZoom((z) => Math.min(3, z + 0.25))}>+</Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
};
