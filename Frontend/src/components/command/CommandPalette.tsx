import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Command,
  Plus,
  Settings,
  Mic,
  User,
  Search,
  Highlighter,
  Brain,
  Bot,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";

interface CommandItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  description: string;
  action: () => void;
}

interface CommandPaletteProps {
  onOpenSettings: () => void;
}

export const CommandPalette = ({ onOpenSettings }: CommandPaletteProps) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const { createChat } = useChatStore();

  const commands: CommandItem[] = [
    {
      id: "new-chat",
      icon: <Plus className="w-4 h-4" />,
      label: "New Chat",
      description: "Start a new conversation",
      action: () => {
        createChat();
        setOpen(false);
      },
    },
    {
      id: "settings",
      icon: <Settings className="w-4 h-4" />,
      label: "Open Settings",
      description: "Configure your preferences",
      action: () => {
        onOpenSettings();
        setOpen(false);
      },
    },
    {
      id: "voice",
      icon: <Mic className="w-4 h-4" />,
      label: "Toggle Voice Mode",
      description: "Enable speech input/output",
      action: () => setOpen(false),
    },
    {
      id: "profile",
      icon: <User className="w-4 h-4" />,
      label: "Open Profile",
      description: "View and edit your profile",
      action: () => {
        navigate("/profile");
        setOpen(false);
      },
    },
    {
      id: "search",
      icon: <Search className="w-4 h-4" />,
      label: "Search History",
      description: "Find previous conversations",
      action: () => setOpen(false),
    },
    {
      id: "highlights",
      icon: <Highlighter className="w-4 h-4" />,
      label: "Jump to Highlights",
      description: "View all your highlights",
      action: () => setOpen(false),
    },
    {
      id: "memory",
      icon: <Brain className="w-4 h-4" />,
      label: "Open Memory Map",
      description: "Visualize your knowledge graph",
      action: () => setOpen(false),
    },
    {
      id: "agents",
      icon: <Bot className="w-4 h-4" />,
      label: "Mini-Agent Threads",
      description: "View all mini-agent conversations",
      action: () => setOpen(false),
    },
  ];

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(search.toLowerCase()) ||
      cmd.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    },
    []
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-50"
            onClick={() => setOpen(false)}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-1/4 left-1/2 -translate-x-1/2 w-full max-w-lg bg-card border border-border rounded-2xl shadow-card overflow-hidden z-50"
          >
            {/* Search */}
            <div className="flex items-center gap-3 p-4 border-b border-border">
              <Command className="w-5 h-5 text-muted-foreground" />
              <Input
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Type a command or search..."
                className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
              />
              <kbd className="hidden sm:inline-flex h-6 items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-xs text-muted-foreground">
                ESC
              </kbd>
            </div>

            {/* Commands */}
            <div className="max-h-80 overflow-y-auto p-2">
              {filteredCommands.map((cmd) => (
                <button
                  key={cmd.id}
                  onClick={cmd.action}
                  className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-secondary transition-colors text-left"
                >
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-foreground">
                    {cmd.icon}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{cmd.label}</p>
                    <p className="text-xs text-muted-foreground">{cmd.description}</p>
                  </div>
                </button>
              ))}
              {filteredCommands.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No commands found
                </p>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border bg-secondary/30 flex items-center justify-between text-xs text-muted-foreground">
              <span>
                <kbd className="inline-flex h-5 items-center rounded border border-border bg-muted px-1 font-mono text-[10px]">
                  ↑↓
                </kbd>{" "}
                Navigate
              </span>
              <span>
                <kbd className="inline-flex h-5 items-center rounded border border-border bg-muted px-1 font-mono text-[10px]">
                  ↵
                </kbd>{" "}
                Select
              </span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
