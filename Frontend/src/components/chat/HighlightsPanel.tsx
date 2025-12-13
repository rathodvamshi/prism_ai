import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, StickyNote, Trash2, Save, Highlighter } from "lucide-react";
import { Highlight } from "@/types/chat";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface HighlightsPanelProps {
  highlights: Highlight[];
  onClose: () => void;
  onUpdateNote: (highlightId: string, note: string) => void;
  onDeleteNote: (highlightId: string) => void;
  onDeleteHighlight: (highlightId: string) => void;
}

export const HighlightsPanel = ({
  highlights,
  onClose,
  onUpdateNote,
  onDeleteNote,
  onDeleteHighlight,
}: HighlightsPanelProps) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const colorMap: Record<string, string> = {
    yellow: "#FEF08A",
    green: "#BBF7D0",
    blue: "#BFDBFE",
    pink: "#FBCFE8",
    orange: "#FED7AA",
    purple: "#E9D5FF",
    teal: "#99F6E4",
    lime: "#D9F99D",
    rose: "#FECDD3",
    cyan: "#A5F3FC",
    amber: "#FDE68A",
    mint: "#A7F3D0",
  };

  const handleSaveNote = (highlightId: string) => {
    if (noteText.trim()) {
      onUpdateNote(highlightId, noteText.trim());
    }
    setEditingId(null);
    setNoteText("");
  };

  const handleStartEdit = (highlight: Highlight) => {
    setEditingId(highlight.id);
    setNoteText(highlight.note || "");
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, []);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        className="w-80 h-full bg-card border-l border-border flex flex-col"
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <Highlighter className="w-4 h-4 text-amber-500" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Highlights</h3>
              <p className="text-xs text-muted-foreground">{highlights.length} highlight{highlights.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Highlights List */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-3">
            {highlights.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Highlighter className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p>No highlights yet</p>
              </div>
            ) : (
              highlights.map((highlight) => (
                <div
                  key={highlight.id}
                  className="bg-secondary/30 rounded-xl p-3 border border-border hover:border-primary/30 transition-colors"
                >
                  {/* Highlighted Text */}
                  <div className="flex items-start gap-2 mb-3">
                    <div
                      className="flex-1 px-3 py-2 rounded-lg text-sm font-medium leading-relaxed"
                      style={{ 
                        backgroundColor: colorMap[highlight.color] || colorMap.yellow,
                        color: 'black'
                      }}
                    >
                      {highlight.text}
                    </div>
                    
                    {/* Delete Highlight Button */}
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => onDeleteHighlight(highlight.id)}
                            className="p-1.5 rounded-lg hover:bg-destructive/20 text-destructive transition-colors shrink-0"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>Delete highlight</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>

                  {/* Note Section */}
                  <div className="space-y-2">
                    {editingId === highlight.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          placeholder="Add a note about why you highlighted this..."
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                          rows={3}
                          autoFocus
                        />
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleSaveNote(highlight.id)}
                            className="flex items-center gap-1.5 h-7 text-xs"
                          >
                            <Save className="w-3 h-3" />
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingId(null);
                              setNoteText("");
                            }}
                            className="h-7 text-xs"
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : highlight.note ? (
                      <div className="flex items-start gap-2 bg-background/50 rounded-lg p-2.5">
                        <StickyNote className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
                        <p className="flex-1 text-xs text-muted-foreground leading-relaxed">{highlight.note}</p>
                        <div className="flex items-center gap-1 shrink-0">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handleStartEdit(highlight)}
                                  className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  <StickyNote className="w-3 h-3" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>Edit note</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => onDeleteNote(highlight.id)}
                                  className="p-1 rounded hover:bg-destructive/20 text-destructive transition-colors"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>Delete note</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleStartEdit(highlight)}
                        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
                      >
                        <StickyNote className="w-3.5 h-3.5" />
                        Add note
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </motion.div>
    </AnimatePresence>
  );
};
