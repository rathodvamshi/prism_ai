import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
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

  // Auto-resize textarea smoothly
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to get accurate scrollHeight
      textareaRef.current.style.height = "auto";
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
      textareaRef.current.style.height = `${newHeight}px`;
      textareaRef.current.style.transition = "height 0.1s ease-out";
    }
  }, [input]);

  // Clear and focus on new session
  useEffect(() => {
    if (resetSignal !== undefined) {
      setInput("");
      setAttachments([]);
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.style.height = "auto";
      }
    }
  }, [resetSignal]);

  const handleSubmit = () => {
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    onSend(input, attachments);
    setInput("");
    attachments.forEach((a) => {
      if (a.url?.startsWith("blob:")) URL.revokeObjectURL(a.url);
      if (a.thumbUrl?.startsWith("blob:")) URL.revokeObjectURL(a.thumbUrl);
    });
    setAttachments([]);
    
    // Smoothly reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.transition = "height 0.15s ease-out";
      textareaRef.current.style.height = "auto";
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
    } catch {}
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="shrink-0 p-2 sm:p-3 md:p-4 bg-background border-t border-transparent"
    >
      <div className="max-w-3xl mx-auto w-full">
        {/* Attachment Previews */}
        {attachments.length > 0 && (
          <div className="mb-2">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Attachments ({attachments.length})</span>
              <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => {
                attachments.forEach((a) => { if (a.url.startsWith("blob:")) URL.revokeObjectURL(a.url); });
                setAttachments([]);
              }}>Clear all</button>
            </div>
            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-1.5 sm:gap-2">
            {attachments.map((a, i) => (
              <div key={a.id} className="relative group">
                {a.type === "image" ? (
                  <button type="button" onClick={() => openViewer(i)} className="block w-full aspect-square overflow-hidden rounded-lg bg-secondary">
                    <img src={a.url} alt={a.name} className="w-full h-full object-cover" />
                  </button>
                ) : (
                  <div className="w-full aspect-square rounded-lg bg-secondary border border-border flex items-center justify-center text-[10px] text-muted-foreground p-2 text-center break-words">
                    <File className="w-4 h-4 mb-1" />
                    <span className="line-clamp-3">{a.name}</span>
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setAttachments((prev) => prev.filter((x) => x.id !== a.id))}
                  className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-background border border-border text-foreground text-[10px] flex items-center justify-center shadow-card"
                  aria-label="Remove attachment"
                >
                  ×
                </button>
              </div>
            ))}
            </div>
          </div>
        )}
        <div
          className="relative bg-card rounded-xl sm:rounded-2xl shadow-soft overflow-hidden"
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }}
          onDrop={(e) => { e.preventDefault(); onPickFiles(e.dataTransfer.files); }}
        >
          <div className="flex items-end gap-1.5 sm:gap-2 p-1.5 sm:p-2">
            {/* Left Actions */}
            <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
              {/* Hidden pickers */}
              <input ref={galleryInputRef} type="file" multiple className="hidden" accept="image/*" onChange={(e) => onPickFiles(e.target.files)} />
              <input ref={filesInputRef} type="file" multiple className="hidden" onChange={(e) => onPickFiles(e.target.files)} accept="image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/zip,application/x-zip-compressed,application/x-7z-compressed,text/plain,application/json" />
              <input ref={cameraInputRef} type="file" className="hidden" accept="image/*" capture="environment" onChange={(e) => onPickFiles(e.target.files)} />
              <input ref={driveInputRef} type="file" multiple className="hidden" onChange={(e) => onPickFiles(e.target.files)} />

              {/* Attachments menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="text-muted-foreground">
                    <Paperclip className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem className="gap-2" onClick={() => galleryInputRef.current?.click()}>
                    <Image className="w-4 h-4" />
                    Gallery
                  </DropdownMenuItem>
                  <DropdownMenuItem className="gap-2" onClick={() => filesInputRef.current?.click()}>
                    <File className="w-4 h-4" />
                    Files
                  </DropdownMenuItem>
                  <DropdownMenuItem className="gap-2" onClick={() => cameraInputRef.current?.click()}>
                    <Mic className="w-4 h-4" />
                    Camera
                  </DropdownMenuItem>
                  <DropdownMenuItem className="gap-2" onClick={() => driveInputRef.current?.click()}>
                    <Cloud className="w-4 h-4" />
                    Drive
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Model Selector (hidden on mobile; shown on desktop) */}
              {!isMobile && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-1 text-xs text-muted-foreground"
                    >
                      {selectedModel.name}
                      <ChevronDown className="w-3 h-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {models.map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => handleModelSelect(model)}
                        className={cn(
                          "gap-2",
                          !model.available && "opacity-60"
                        )}
                      >
                        {model.available ? (
                          <Check className="w-4 h-4 text-success" />
                        ) : (
                          <Lock className="w-4 h-4 text-muted-foreground" />
                        )}
                        {model.name}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>

            {/* Textarea */}
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message PRISM..."
              className="flex-1 min-h-[36px] sm:min-h-[40px] max-h-[160px] sm:max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 py-2 sm:py-2.5 text-sm sm:text-base px-1"
              rows={1}
            />

            {/* Right Actions */}
            <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
              <Button variant="ghost" size="icon-sm" className="text-muted-foreground h-8 w-8 sm:h-9 sm:w-9">
                <Mic className="w-4 h-4" />
              </Button>
              <Button
                size="icon-sm"
                onClick={handleSubmit}
                disabled={(!input.trim() && attachments.length === 0) || isLoading}
                className={cn(
                  "transition-all h-8 w-8 sm:h-9 sm:w-9",
                  (input.trim() || attachments.length > 0) && "bg-primary shadow-soft"
                )}
              >
                <Send className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
            </div>
          </div>
        </div>

        <p className="text-[10px] sm:text-xs text-muted-foreground text-center mt-1.5 sm:mt-2 px-2">
          PRISM can make mistakes. Consider checking important information.
        </p>
      </div>

      {/* Image Viewer */}
      <Dialog open={viewerOpen} onOpenChange={setViewerOpen}>
        <DialogContent className="p-0 max-w-full w-full h-dvh bg-black/95 border-0">
          <div className="relative w-full h-full flex items-center justify-center">
            <button type="button" className="absolute top-3 right-3 z-10 text-white/90 text-xl" onClick={() => setViewerOpen(false)}>×</button>
            <button type="button" className="absolute left-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.max(0, i - 1))}>‹</button>
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.min(attachments.filter(a=>a.type==='image').length - 1, i + 1))}>›</button>
            <div className="flex flex-col items-center gap-3">
              <img
                src={attachments.filter(a=>a.type==='image')[viewerIndex]?.url}
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
