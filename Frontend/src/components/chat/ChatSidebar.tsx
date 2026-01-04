import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { useProfileStore } from "@/stores/profileStore";
import { Button } from "@/components/ui/button";
import type { Chat } from "@/types/chat";
import { ChatListSkeleton, TaskSkeleton } from "@/components/chat/LoadingSkeletons";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  MessageSquare,
  CheckSquare,
  Search,
  Trash2,
  ChevronLeft,
  ChevronRight,
  User,
  Settings,
  LogOut,
  Sparkles,
  Sun,
  Moon,
  MoreVertical,
  Pin,
  Calendar as CalendarIcon,
} from "lucide-react";
import { useEffect, useState, useRef, useCallback, memo, forwardRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { format, startOfToday } from "date-fns";
import { useIsMobile } from "@/hooks/use-mobile";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useToast } from "@/components/ui/use-toast";
// (already imported above)

interface ChatSidebarProps {
  onOpenSettings: () => void;
}

const TypingTitle = ({ text }: { text: string }) => {
  const [displayedText, setDisplayedText] = useState(text);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    // Only animate if text changed AND it's not the initial mount or empty
    if (text !== displayedText) {
      // If changing from "Untitled" or "New Chat" or empty -> animate
      // If just a minor correction, maybe strict replace?
      // Let's always animate for the "wow" factor user requested.
      setIsTyping(true);

      let i = 0;
      setDisplayedText(""); // Reset
      const speed = 30; // ms per char

      const interval = setInterval(() => {
        setDisplayedText(text.slice(0, i + 1));
        i++;
        if (i >= text.length) {
          clearInterval(interval);
          setIsTyping(false);
          setDisplayedText(text); // Ensure full match
        }
      }, speed);

      return () => clearInterval(interval);
    }
  }, [text]);

  return <span className="block truncate min-h-[1.25em]">{displayedText}{(isTyping || !displayedText) && <span className="animate-pulse font-bold text-primary">|</span>}</span>;
};

interface SidebarChatItemProps {
  chat: Chat;
  isActive: boolean;
  expanded: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onPin: (id: string, isPinned: boolean) => void;
  onSave: (id: string, isSaved: boolean) => void;
  onDelete: (id: string) => void;
  historyFilter: "recent" | "saved";
}

const SidebarChatItem = memo(forwardRef<HTMLDivElement, SidebarChatItemProps>(({
  chat, isActive, expanded, onSelect, onRename, onPin, onSave, onDelete, historyFilter
}, ref) => {
  return (
    <motion.div
      ref={ref}
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        "group flex items-center gap-1 md:gap-1.5 p-1 md:p-1.5 rounded-lg cursor-pointer transition-all w-full",
        isActive
          ? "bg-sidebar-accent/50 border border-primary/30 shadow-sm"
          : "hover:bg-sidebar-accent/25"
      )}
      onClick={() => onSelect(chat.id)}
    >
      <MessageSquare className={cn(
        "w-3 h-3 md:w-3.5 md:h-3.5 shrink-0",
        isActive ? "text-primary" : "text-muted-foreground"
      )} />
      {expanded && (
        <>
          <div className="flex-1 min-w-0 max-w-[120px] overflow-hidden text-left pr-2">
            <p className={cn(
              "text-xs md:text-sm truncate leading-tight transition-all",
              isActive ? "font-semibold text-sidebar-foreground" : "font-medium text-sidebar-foreground/80"
            )}>
              <TypingTitle text={chat.title} />
            </p>
            <p className="text-[10px] md:text-[11px] text-muted-foreground truncate opacity-70">
              {format(new Date(chat.updatedAt), "MMM d")}
            </p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {chat.isPinned && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Pin className="w-3 h-3 text-primary rotate-45" />
                  </TooltipTrigger>
                  <TooltipContent>Pinned</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" sideOffset={4}>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onRename(chat.id, chat.title);
                  }}
                >
                  Rename
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onPin(chat.id, !chat.isPinned);
                  }}
                >
                  <Pin className="w-3 h-3 mr-2" /> {chat.isPinned ? "Unpin" : "Pin"}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onSave(chat.id, !chat.isSaved);
                  }}
                >
                  {historyFilter === "saved" || chat.isSaved ? "Unsave" : "Save"}
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(chat.id);
                  }}
                >
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </>
      )}
    </motion.div>
  );
}));
SidebarChatItem.displayName = "SidebarChatItem";

export const ChatSidebar = ({ onOpenSettings }: ChatSidebarProps) => {
  const isMobile = useIsMobile();
  const { toast } = useToast();
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const {
    chats,
    currentChatId,
    tasks,
    sidebarExpanded,
    activeTab,
    createChat,
    createTask,
    setCurrentChat,
    deleteChat,
    renameChat,
    pinChat,
    saveChat,
    toggleTask,
    deleteTask,
    toggleSidebar,
    setActiveTab,
    isLoadingChats,
    hasMore,
    loadChatsFromBackend,
  } = useChatStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [isDark, setIsDark] = useState(false);
  const [profileAvatar, setProfileAvatar] = useState<string | null>(null);
  const [profileName, setProfileName] = useState<string>("User");
  const [historyFilter, setHistoryFilter] = useState<"recent" | "saved">("recent");
  const [tasksFilter, setTasksFilter] = useState<"pending" | "completed">("pending");
  // Removed chatMeta - using chat.isPinned and chat.isSaved from MongoDB
  const [renameChatId, setRenameChatId] = useState<string | null>(null);
  const [renameTitle, setRenameTitle] = useState<string>("");
  const [confirmDeleteChatId, setConfirmDeleteChatId] = useState<string | null>(null);
  const [taskMeta, setTaskMeta] = useState<Record<string, { pinned?: boolean; description?: string; date?: Date; timeSeconds?: number; imageUrl?: string }>>({});
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskDate, setTaskDate] = useState<Date | undefined>(undefined);
  const [taskTimeSeconds, setTaskTimeSeconds] = useState<number>(0);
  const [taskImageUrl, setTaskImageUrl] = useState<string | undefined>(undefined);
  const [savingTask, setSavingTask] = useState(false);
  const [datePopoverOpen, setDatePopoverOpen] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Infinite scroll observer
  const observer = useRef<IntersectionObserver>();
  const lastChatElementRef = useCallback((node: HTMLDivElement | null) => {
    if (isLoadingChats || isLoadingMore) return;
    if (observer.current) observer.current.disconnect();

    observer.current = new IntersectionObserver(async entries => {
      if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
        setIsLoadingMore(true);
        try {
          await loadChatsFromBackend(true);
        } finally {
          setIsLoadingMore(false);
        }
      }
    });

    if (node) observer.current.observe(node);
  }, [isLoadingChats, hasMore, loadChatsFromBackend, isLoadingMore]);

  // Lock body scroll when mobile sidebar is open (overlay mode)
  useEffect(() => {
    if (isMobile) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = sidebarExpanded ? "hidden" : originalOverflow || "";
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isMobile, sidebarExpanded]);

  // Apply theme globally without refresh
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [isDark]);

  const { profile } = useProfileStore();

  // Load profile info for sidebar
  useEffect(() => {
    setProfileAvatar(profile.avatarUrl || "");
    setProfileName(profile.name || "User");
  }, [profile]);

  // Remove duplicates by ID - MongoDB is source of truth
  const uniqueChats = chats.reduce((acc: Chat[], chat: Chat) => {
    if (!acc.find(c => c.id === chat.id)) {
      acc.push(chat);
    }
    return acc;
  }, []);

  const filteredChats = uniqueChats
    // Hide empty sessions from history - check both loaded messages and MongoDB count
    .filter((chat) => {
      // Show chat if it has messages loaded OR has messages in MongoDB
      const hasMessages = chat.messages.length > 0 || (chat.messageCount && chat.messageCount > 0);
      return hasMessages;
    })
    .filter((chat) => chat.title.toLowerCase().includes(searchQuery.toLowerCase()))
    // Sort by pinned first, then by updatedAt (MongoDB data)
    .sort((a, b) => {
      if (a.isPinned && !b.isPinned) return -1;
      if (!a.isPinned && b.isPinned) return 1;
      return b.updatedAt.getTime() - a.updatedAt.getTime();
    });

  const pendingTasks = tasks
    .map((t) => ({
      ...t,
      pinned: !!taskMeta[t.id]?.pinned,
    }))
    .filter((t) => !t.completed)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned));
  const completedTasks = tasks
    .map((t) => ({
      ...t,
      pinned: !!taskMeta[t.id]?.pinned,
    }))
    .filter((t) => t.completed)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned));

  // Logout handler
  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleSelectChat = useCallback((id: string) => {
    setCurrentChat(id);
    navigate(`/chat/${id}`);
  }, [navigate, setCurrentChat]);

  const handleRenameChat = useCallback((id: string, title: string) => {
    setRenameChatId(id);
    setRenameTitle(title);
  }, []);

  const handlePinChat = useCallback((id: string, pinned: boolean) => pinChat(id, pinned), [pinChat]);
  const handleSaveChat = useCallback((id: string, saved: boolean) => saveChat(id, saved), [saveChat]);
  const handleDeleteChat = useCallback((id: string) => setConfirmDeleteChatId(id), []);

  return (
    <>
      {/* Mobile backdrop overlay */}
      <AnimatePresence>
        {isMobile && sidebarExpanded && (
          <motion.div
            key="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={toggleSidebar}
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={
          isMobile
            ? { x: sidebarExpanded ? 0 : -320 }
            : { width: sidebarExpanded ? 260 : 64 }
        }
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className={cn(
          "h-screen bg-sidebar border-r border-sidebar-border flex flex-col",
          isMobile
            ? "fixed top-0 left-0 z-50 w-[85vw] max-w-[240px]"
            : "relative",
          !isMobile && !sidebarExpanded && "cursor-e-resize hover:bg-sidebar/80 transition-colors"
        )}
        drag={isMobile && sidebarExpanded ? "x" : false}
        dragConstraints={isMobile && sidebarExpanded ? { left: -320, right: 0 } : undefined}
        dragElastic={0.1}
        onDragEnd={(e, info) => {
          if (!isMobile) return;
          const shouldClose = info.offset.x < -80 || info.velocity.x < -500;
          if (shouldClose) toggleSidebar();
        }}
        style={{ pointerEvents: isMobile && !sidebarExpanded ? "none" : "auto" }}
        onClick={() => {
          if (!isMobile && !sidebarExpanded) {
            toggleSidebar();
          }
        }}
      >
        {/* Header */}
        <div className="p-3 sm:p-3 md:p-4">
          <div className="flex items-center justify-between">
            {sidebarExpanded && (
              <div className="flex items-center gap-2 select-none">
                <img src="/pyramid.svg" alt="Prism" className="w-8 h-8 rounded-lg" />
                <span className="font-bold text-sidebar-foreground tracking-wide">PRISM</span>
              </div>
            )}
            {sidebarExpanded ? (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => { e.stopPropagation(); toggleSidebar(); }}
                      className="text-sidebar-foreground relative z-10"
                      type="button"
                      aria-label="Collapse sidebar"
                      aria-expanded={sidebarExpanded}
                      role="button"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">Collapse</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ) : (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => { e.stopPropagation(); if (!isMobile) toggleSidebar(); }}
                      className="text-sidebar-foreground relative group z-10"
                      type="button"
                      aria-label="Expand sidebar"
                      aria-expanded={sidebarExpanded}
                      role="button"
                    >
                      {/* Default state: logo on desktop, three dots on mobile */}
                      {isMobile ? (
                        <span className="absolute inset-0 flex items-center justify-center transition-opacity duration-200 group-hover:opacity-0">
                          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                            <circle cx="5" cy="12" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="19" cy="12" r="2" />
                          </svg>
                        </span>
                      ) : (
                        <span className="absolute inset-0 flex items-center justify-center transition-opacity duration-200 group-hover:opacity-0">
                          <img src="/pyramid.svg" alt="Prism" className="w-6 h-6 rounded" />
                        </span>
                      )}
                      {/* Chevron appears on hover */}
                      <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <ChevronRight className="w-4 h-4" />
                      </span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">Expand</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>

        {/* New Chat Button (expanded sidebar) */}
        {sidebarExpanded && (
          <div className="p-3 sm:p-3 md:p-4">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={async () => {
                      // Create new session and navigate
                      const newSessionId = await useChatStore.getState().startNewSession();
                      if (newSessionId) {
                        navigate(`/chat/${newSessionId}`);
                      }
                    }}
                    className={cn("w-full gap-2 btn-responsive", "justify-center")}
                    size="default"
                  >
                    <Plus className="w-4 h-4 md:w-5 md:h-5" />
                    New Chat
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">New Chat</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* Tabs / Icons */}
        <div className="px-3 flex gap-1">
          {sidebarExpanded ? (
            <>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => setActiveTab("history")}
                      className={cn(
                        "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                        activeTab === "history"
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                      )}
                    >
                      <MessageSquare className="w-4 h-4 inline-block mr-1.5" />
                      History
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">History</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => setActiveTab("tasks")}
                      className={cn(
                        "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                        activeTab === "tasks"
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                      )}
                    >
                      <CheckSquare className="w-4 h-4 inline-block mr-1.5" />
                      Tasks
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">Tasks</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </>
          ) : (
            <div className="flex flex-col gap-2">
              {/* New Chat (collapsed) */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={async () => {
                        const newSessionId = await useChatStore.getState().startNewSession();
                        if (newSessionId) {
                          navigate(`/chat/${newSessionId}`);
                        }
                      }}
                      className={cn(
                        "text-sidebar-foreground rounded-full",
                        "bg-sidebar-accent/20 hover:bg-sidebar-accent/30",
                        "shadow-soft",
                        "transition-all hover:scale-[0.97]",
                      )}
                      style={{ backdropFilter: "blur(8px)" }}
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8} align="center">
                    <p>New Chat</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setActiveTab("history")}
                      className={cn(
                        "text-sidebar-foreground rounded-full",
                        activeTab === "history" && "bg-sidebar-accent"
                      )}
                    >
                      <MessageSquare className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8} align="center">
                    <p>History</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setActiveTab("tasks")}
                      className={cn(
                        "text-sidebar-foreground rounded-full",
                        activeTab === "tasks" && "bg-sidebar-accent"
                      )}
                    >
                      <CheckSquare className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8} align="center">
                    <p>Tasks</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          )}
        </div>

        {/* Search (hidden when collapsed) */}
        {sidebarExpanded && (
          <div className="p-3 sm:p-3 md:p-4">
            <div className="flex items-center gap-1.5 md:gap-2 bg-sidebar-accent rounded-full px-2.5 py-1.5 md:px-3 md:py-2 h-9 md:h-10">
              <Search className="w-4 h-4 md:w-5 md:h-5 text-muted-foreground shrink-0" />
              <Input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-0 text-sm placeholder:text-muted-foreground placeholder:opacity-80"
                aria-label="Search chats and tasks"
              />
            </div>
            {/* Sub-tabs under search */}
            {activeTab === "history" ? (
              <div className="mt-3 flex gap-1">
                <button
                  onClick={() => setHistoryFilter("recent")}
                  className={cn(
                    "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                    historyFilter === "recent"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  Recent
                </button>
                <button
                  onClick={() => setHistoryFilter("saved")}
                  className={cn(
                    "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                    historyFilter === "saved"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  Saved
                </button>
              </div>
            ) : (
              <div className="mt-3 flex gap-1">
                <button
                  onClick={() => setTasksFilter("pending")}
                  className={cn(
                    "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                    tasksFilter === "pending"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  Pending
                </button>
                <button
                  onClick={() => setTasksFilter("completed")}
                  className={cn(
                    "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                    tasksFilter === "completed"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  Completed
                </button>
              </div>
            )}
          </div>
        )}

        {/* Content (hidden when collapsed) */}
        {sidebarExpanded && (
          <ScrollArea className="flex-1 px-3 sm:px-3 md:px-4 no-scrollbar">
            <AnimatePresence mode="wait">
              {activeTab === "history" ? (
                <motion.div
                  key="history"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-1 md:space-y-2 pb-4"
                >
                  {/* Loading skeleton for chat history */}
                  {isLoadingChats ? (
                    <ChatListSkeleton />
                  ) : (
                    <>
                      {filteredChats
                        .filter((chat: any) => (historyFilter === "recent" ? !chat.isSaved : !!chat.isSaved))
                        .map((chat: any, index: number, array: any[]) => (
                          <SidebarChatItem
                            key={chat.id}
                            ref={index === array.length - 1 ? lastChatElementRef : null}
                            chat={chat}
                            isActive={currentChatId === chat.id}
                            expanded={sidebarExpanded}
                            onSelect={handleSelectChat}
                            onRename={handleRenameChat}
                            onPin={handlePinChat}
                            onSave={handleSaveChat}
                            onDelete={handleDeleteChat}
                            historyFilter={historyFilter}
                          />
                        ))}
                      {filteredChats.length === 0 && sidebarExpanded && (
                        <p className="text-sm text-muted-foreground text-center py-8">
                          No chats yet
                        </p>
                      )}

                      {isLoadingMore && (
                        <div className="py-2 flex justify-center animate-in fade-in duration-300">
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/70" />
                        </div>
                      )}
                    </>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="tasks"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4 pb-4"
                >
                  {sidebarExpanded && (
                    <>
                      {tasksFilter === "pending" && pendingTasks.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-2">
                            Pending ({pendingTasks.length})
                          </p>
                          <div className="space-y-1">
                            {pendingTasks.map((task) => (
                              <div
                                key={task.id}
                                className="group flex items-center gap-2 md:gap-3 p-2 rounded-lg bg-sidebar-accent/50 w-full"
                              >
                                <input
                                  type="checkbox"
                                  checked={task.completed}
                                  onChange={() => toggleTask(task.id)}
                                  className="rounded border-border shrink-0"
                                />
                                <div className="flex-1 min-w-0 overflow-hidden">
                                  <p className="text-sm text-sidebar-foreground truncate">{task.title}</p>
                                  {/* ☁️ Show due date from task if available, otherwise show taskMeta */}
                                  {(task.dueDate || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds || taskMeta[task.id]?.imageUrl) && (
                                    <p className="text-xs text-muted-foreground truncate">
                                      {task.dueDate
                                        ? format(task.dueDate, "MMM dd, yyyy 'at' h:mm a")
                                        : taskMeta[task.id]?.date
                                          ? `${format(taskMeta[task.id]!.date!, "dd/MM/yy")}`
                                          : ""}
                                      {taskMeta[task.id]?.timeSeconds ? `${(task.dueDate || taskMeta[task.id]?.date) ? " • " : ""}${taskMeta[task.id]!.timeSeconds}s` : ""}
                                      {taskMeta[task.id]?.imageUrl ? `${(task.dueDate || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds) ? " • " : ""}image attached` : ""}
                                    </p>
                                  )}
                                </div>
                                <DropdownMenu>
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <DropdownMenuTrigger asChild>
                                          <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            className={cn(isMobile ? "opacity-100" : "opacity-0 group-hover:opacity-100", "shrink-0")}
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <MoreVertical className="w-3.5 h-3.5" />
                                          </Button>
                                        </DropdownMenuTrigger>
                                      </TooltipTrigger>
                                      <TooltipContent side="right" sideOffset={8}>More</TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                  <DropdownMenuContent align="end" sideOffset={4}>
                                    <DropdownMenuItem
                                      onClick={() => {
                                        setEditTaskId(task.id);
                                        setTaskTitle(task.title);
                                        setTaskDescription(taskMeta[task.id]?.description || "");
                                        setTaskDate(taskMeta[task.id]?.date);
                                        setTaskTimeSeconds(taskMeta[task.id]?.timeSeconds || 0);
                                        setTaskImageUrl(taskMeta[task.id]?.imageUrl);
                                        setTaskDialogOpen(true);
                                      }}
                                    >
                                      Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => {
                                        setTaskMeta((prev) => ({
                                          ...prev,
                                          [task.id]: { ...prev[task.id], pinned: !prev[task.id]?.pinned },
                                        }));
                                      }}
                                    >
                                      <Pin className="w-3 h-3 mr-2" /> {taskMeta[task.id]?.pinned ? "Unpin" : "Pin"}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => navigator.clipboard?.writeText(`Task: ${task.title}`)}
                                    >
                                      Share
                                    </DropdownMenuItem>
                                    <DropdownMenuItem className="text-destructive" onClick={() => deleteTask(task.id)}>
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {tasksFilter === "completed" && completedTasks.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-2">
                            Completed ({completedTasks.length})
                          </p>
                          <div className="space-y-1">
                            {completedTasks.map((task) => (
                              <div
                                key={task.id}
                                className="group flex items-center gap-2 p-2 rounded-lg w-full"
                              >
                                <input
                                  type="checkbox"
                                  checked={task.completed}
                                  onChange={() => toggleTask(task.id)}
                                  className="rounded border-border shrink-0"
                                />
                                <div className="flex-1 min-w-0 overflow-hidden">
                                  <p className="text-sm text-muted-foreground line-through truncate">{task.title}</p>
                                  {/* ☁️ Show due date from task if available, otherwise show taskMeta */}
                                  {(task.dueDate || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds || taskMeta[task.id]?.imageUrl) && (
                                    <p className="text-xs text-muted-foreground truncate">
                                      {task.dueDate
                                        ? format(task.dueDate, "MMM dd, yyyy 'at' h:mm a")
                                        : taskMeta[task.id]?.date
                                          ? `${format(taskMeta[task.id]!.date!, "dd/MM/yy")}`
                                          : ""}
                                      {taskMeta[task.id]?.timeSeconds ? `${(task.dueDate || taskMeta[task.id]?.date) ? " • " : ""}${taskMeta[task.id]!.timeSeconds}s` : ""}
                                      {taskMeta[task.id]?.imageUrl ? `${(task.dueDate || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds) ? " • " : ""}image attached` : ""}
                                    </p>
                                  )}
                                </div>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon-sm"
                                      className={cn(isMobile ? "opacity-100" : "opacity-0 group-hover:opacity-100", "shrink-0")}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreVertical className="w-3.5 h-3.5" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" sideOffset={4}>
                                    <DropdownMenuItem onClick={() => toggleTask(task.id)}>
                                      Continue (mark pending)
                                    </DropdownMenuItem>
                                    <DropdownMenuItem className="text-destructive" onClick={() => deleteTask(task.id)}>
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {((tasksFilter === "pending" && pendingTasks.length === 0) ||
                        (tasksFilter === "completed" && completedTasks.length === 0)) && (
                          <p className="text-sm text-muted-foreground text-center py-8">
                            {tasksFilter === "pending" ? "No pending tasks" : "No completed tasks"}
                          </p>
                        )}
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </ScrollArea>
        )}

        {/* Floating add task button in tasks view */}
        {sidebarExpanded && activeTab === "tasks" && (
          <div className="p-3">
            <div className="relative">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      className="absolute right-0 bottom-0 rounded-full w-10 h-10"
                      variant="default"
                      size="icon"
                      onClick={() => {
                        setEditTaskId(null);
                        setTaskTitle("");
                        setTaskDescription("");
                        setTaskDate(undefined);
                        setTaskTimeSeconds(0);
                        setTaskImageUrl(undefined);
                        setTaskDialogOpen(true);
                      }}
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" sideOffset={8}>Add Task</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        )}

        {/* Add/Edit Task Dialog */}
        <Dialog open={taskDialogOpen} onOpenChange={setTaskDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editTaskId ? "Edit task" : "Add task"}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Title *</label>
                <Input placeholder="Enter title" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Description *</label>
                <Textarea placeholder="Enter description" value={taskDescription} onChange={(e) => setTaskDescription(e.target.value)} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                <div className="space-y-1">
                  <label className="text-sm text-muted-foreground">Date (MM/YY) *</label>
                  <Popover open={datePopoverOpen} onOpenChange={setDatePopoverOpen}>
                    <PopoverTrigger asChild>
                      <div className="relative">
                        <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 md:w-5 md:h-5 text-muted-foreground" />
                        <Input
                          readOnly
                          placeholder="Select date (dd/MM/yy)"
                          value={taskDate ? format(taskDate, "dd/MM/yy") : ""}
                          className="pl-9 input-responsive"
                          onClick={() => setDatePopoverOpen(true)}
                        />
                      </div>
                    </PopoverTrigger>
                    <PopoverContent className="p-2 w-auto" align="start">
                      <Calendar
                        selected={taskDate}
                        onSelect={(date?: Date) => {
                          if (date) {
                            setTaskDate(date);
                            setDatePopoverOpen(false);
                          }
                        }}
                        disabled={(date: Date) => date < startOfToday()}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Time (seconds) *</label>
                  <Input
                    type="number"
                    min={1}
                    value={taskTimeSeconds}
                    onChange={(e) => setTaskTimeSeconds(Number(e.target.value) || 0)}
                    className="input-responsive"
                  />
                  <label className="text-sm text-muted-foreground">Image URL</label>
                  <Input
                    placeholder="https://..."
                    value={taskImageUrl || ""}
                    onChange={(e) => setTaskImageUrl(e.target.value || undefined)}
                    className="input-responsive"
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                disabled={savingTask}
                onClick={async () => {
                  // Required validations
                  if (!taskTitle.trim()) return;
                  if (!taskDescription.trim()) return;
                  if (!taskDate) return;
                  if (!taskTimeSeconds || taskTimeSeconds < 1) return;

                  setSavingTask(true);
                  await new Promise((res) => setTimeout(res, 1000)); // simulate 1s load

                  if (editTaskId) {
                    setTaskMeta((prev) => ({
                      ...prev,
                      [editTaskId]: {
                        ...prev[editTaskId],
                        description: taskDescription,
                        date: taskDate,
                        timeSeconds: taskTimeSeconds,
                        imageUrl: taskImageUrl,
                      },
                    }));
                  } else {
                    const newId = createTask(taskTitle);
                    setTaskMeta((prev) => ({
                      ...prev,
                      [newId]: {
                        description: taskDescription,
                        date: taskDate,
                        timeSeconds: taskTimeSeconds,
                        imageUrl: taskImageUrl,
                      },
                    }));
                  }
                  setSavingTask(false);
                  setTaskDialogOpen(false);
                  toast({ title: "Task saved" });
                }}
              >
                {savingTask ? "Saving..." : "Save"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Theme toggle moved to Settings > General */}

        {/* Rename Dialog */}
        <Dialog open={!!renameChatId} onOpenChange={() => setRenameChatId(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rename chat</DialogTitle>
            </DialogHeader>
            <Input
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              placeholder="Enter a new title"
            />
            <DialogFooter>
              <Button
                onClick={async () => {
                  if (!renameChatId) return;
                  await renameChat(renameChatId, renameTitle);
                  setRenameChatId(null);
                }}
              >
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirm */}
        <AlertDialog open={!!confirmDeleteChatId} onOpenChange={() => setConfirmDeleteChatId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  if (!confirmDeleteChatId) return;
                  try {
                    await deleteChat(confirmDeleteChatId);
                    toast({ title: "Chat deleted successfully" });
                  } catch (error) {
                    toast({
                      title: "Failed to delete chat",
                      variant: "destructive"
                    });
                  }
                  setConfirmDeleteChatId(null);
                }}
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* User Section */}
        <div className="p-3 sm:p-3 md:p-4 mt-auto">
          <div
            className={cn(
              "flex items-center gap-2",
              !sidebarExpanded && "justify-center"
            )}
          >
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-full overflow-hidden bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center border border-border">
                    {profileAvatar ? (
                      <img src={profileAvatar} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-4 h-4 md:w-5 md:h-5 text-primary-foreground" />
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side={sidebarExpanded ? "bottom" : "right"} sideOffset={8} align="center">
                  <p>{profileName || "Profile"}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {sidebarExpanded && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-sidebar-foreground truncate">
                    {profileName || "User"}
                  </p>
                  <p className="text-xs text-muted-foreground">Free Plan</p>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onOpenSettings}
                    className="text-muted-foreground"
                  >
                    <Settings className="w-4 h-4 md:w-5 md:h-5" />
                  </Button>
                  <AlertDialog>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground"
                              >
                                <LogOut className="w-4 h-4 md:w-5 md:h-5" />
                              </Button>
                            </AlertDialogTrigger>
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Log out</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Log out?</AlertDialogTitle>
                        <AlertDialogDescription>
                          You will be signed out of PRISM. Continue?
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleLogout}>
                          Log out
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </>
            )}
          </div>
        </div>
      </motion.aside>
    </>
  );
};
