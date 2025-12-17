import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, StickyNote, Trash2, Save, Highlighter, Search } from "lucide-react";
import { Highlight } from "@/types/chat";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";

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
  const [searchQuery, setSearchQuery] = useState("");
  const [panelWidth, setPanelWidth] = useState(320); // Default 320px (20rem)
  const [isResizing, setIsResizing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Helper function to get the display color (supports both HEX and color names)
  const getDisplayColor = (color: string): string => {
    // If it's already a HEX color, use it directly
    if (color.startsWith('#')) {
      return color;
    }
    
    // Legacy color name mapping (for backwards compatibility)
    const colorMap: Record<string, string> = {
      yellow: "#FFD93D",
      green: "#3ED174",
      blue: "#4B9CFF",
      pink: "#FBCFE8",
      orange: "#FED7AA",
      purple: "#C36BFF",
      teal: "#99F6E4",
      lime: "#D9F99D",
      rose: "#FECDD3",
      red: "#FF4B4B",
      cyan: "#A5F3FC",
      amber: "#FDE68A",
      mint: "#A7F3D0",
    };
    
    return colorMap[color.toLowerCase()] || "#FFD93D"; // Default to yellow if not found
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

  // Handle resize
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      
      const newWidth = window.innerWidth - e.clientX;
      // Min width: 280px, Max width: 600px
      const clampedWidth = Math.max(280, Math.min(600, newWidth));
      setPanelWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Filter and sort highlights (newest first)
  const filteredHighlights = [...highlights]
    .filter(h => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      // Search by text content or color
      return h.text.toLowerCase().includes(query) || 
             h.color.toLowerCase().includes(query) ||
             getDisplayColor(h.color).toLowerCase().includes(query);
    })
    .reverse(); // Reverse to show newest first

  return (
    <AnimatePresence>
      <motion.div
        ref={panelRef}
        initial={{ x: "100%", opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: "100%", opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        style={{ width: `${panelWidth}px` }}
        className="h-full bg-card border-l border-border flex flex-col relative"
      >
        {/* Resize Handle */}
        <div
          onMouseDown={handleMouseDown}
          className={`absolute left-0 top-0 bottom-0 w-1 hover:w-1.5 bg-transparent hover:bg-primary/50 cursor-col-resize transition-all z-50 ${isResizing ? 'bg-primary w-1.5' : ''}`}
          title="Drag to resize"
        />
        {/* Header */}
        <div className="p-4 border-b border-border shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Highlighter className="w-4 h-4 text-amber-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">Highlights</h3>
                <p className="text-xs text-muted-foreground">{filteredHighlights.length} of {highlights.length}</p>
              </div>
            </div>
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onClose}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left" className="text-xs py-1 px-2">
                  Close
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search text or color..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 h-8 text-xs bg-secondary/50 border-border/50 focus:bg-background"
            />
          </div>
        </div>

        {/* Highlights List */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-3">
            {filteredHighlights.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Highlighter className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">{searchQuery ? 'No matches found' : 'No highlights yet'}</p>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="text-xs text-primary hover:underline mt-2"
                  >
                    Clear search
                  </button>
                )}
              </div>
            ) : (
              filteredHighlights.map((highlight) => (
                <div
                  key={highlight.id}
                  className="bg-secondary/30 rounded-xl p-3 border border-border hover:border-primary/30 transition-colors"
                >
                  {/* Highlighted Text */}
                  <div className="flex items-start gap-2 mb-3">
                    <div
                      className="flex-1 px-3 py-2 rounded-lg text-sm font-medium leading-relaxed shadow-sm"
                      style={{ 
                        backgroundColor: getDisplayColor(highlight.color),
                        color: '#000000',
                        border: '1px solid rgba(0,0,0,0.1)'
                      }}
                    >
                      {highlight.text}
                    </div>
                    
                    {/* Delete Highlight Button */}
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => onDeleteHighlight(highlight.id)}
                            className="p-1.5 rounded-lg hover:bg-destructive/20 text-destructive transition-colors shrink-0"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="left" className="text-xs py-1 px-2">
                          Delete
                        </TooltipContent>
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
