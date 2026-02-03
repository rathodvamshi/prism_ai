import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { useProfileStore } from "@/stores/profileStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
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
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { format, startOfToday, isToday, isYesterday, isThisWeek, subDays } from "date-fns";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  MessageSquare,
  CheckSquare,
  Search,
  MoreVertical,
  Pin,
  Save,
  Trash2,
  Calendar as CalendarIcon,
  Lock,
  Clock8,
  Music,
  Loader2,
  LogOut,
  User,
  Sparkles,
  Sun,
  Moon,
  Clock,
  Bookmark,
  CircleDot,
  CheckCircle2,
  LayoutGrid,
  Heart,
  Code,
  FileText,
  Image as ImageIcon,
  Video,
  Settings,
  Zap,
  Key,
  RefreshCw,
  Monitor,
  Check,
  RotateCcw,
  Edit,
  Share2,
} from "lucide-react";
import { useState, useEffect, useCallback, memo, useRef, forwardRef } from "react"; // Added forwardRef
import { useNavigate, Link } from "react-router-dom"; // Added Link
import { UserProfileModal } from "@/components/profile/UserProfileModal";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import { useIsMobile } from "@/hooks/use-mobile";
import { MediaLibrary } from "@/components/media/MediaLibrary";
import { apiKeysAPI } from "@/lib/api";
import type { Theme } from "@/lib/theme";
import type { Chat } from "@/types/chat";
import { ChatListSkeleton } from "@/components/chat/LoadingSkeletons";
import { useDebouncedCallback } from "@/hooks/useDebounce";

// Helper: Get date group label
const getDateGroup = (date: Date): string => {
  if (isToday(date)) return "Today";
  if (isYesterday(date)) return "Yesterday";
  if (isThisWeek(date)) return "This Week";
  return "Older";
};

// Helper: Detect chat intent for icon
const detectChatIntent = (title: string): 'music' | 'code' | 'image' | 'video' | 'chat' => {
  const t = title.toLowerCase();
  if (/\b(song|music|play|audio|spotify|mp3)\b/.test(t)) return 'music';
  if (/\b(code|function|api|debug|error|javascript|python|react)\b/.test(t)) return 'code';
  if (/\b(image|photo|picture|draw|design|logo)\b/.test(t)) return 'image';
  if (/\b(video|youtube|watch|movie|stream|4k)\b/.test(t)) return 'video';
  return 'chat';
};

// Intent icon mapping
const IntentIcon = ({ intent, isActive }: { intent: ReturnType<typeof detectChatIntent>; isActive: boolean }) => {
  const className = cn("w-3 h-3 shrink-0", isActive ? "text-primary" : "text-muted-foreground/70");
  switch (intent) {
    case 'music': return <Music className={className} />;
    case 'code': return <Code className={className} />;
    case 'image': return <ImageIcon className={className} />;
    case 'video': return <Video className={className} />;
    default: return <MessageSquare className={className} />;
  }
};

// Draft session indicator - shows when user is in "New Chat" mode
const DraftSessionItem = memo(({ isCreating, expanded }: { isCreating: boolean; expanded: boolean }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        "group relative flex items-center gap-1.5 px-2 py-1.5 rounded-md",
        "bg-primary/10 border border-primary/30",
        "shadow-sm"
      )}
    >
      {/* Animated icon */}
      {isCreating ? (
        <Loader2 className="w-3 h-3 shrink-0 text-primary animate-spin" />
      ) : (
        <Sparkles className="w-3 h-3 shrink-0 text-primary animate-pulse" />
      )}

      {expanded && (
        <div className="flex-1 min-w-0 overflow-hidden">
          <p className="text-[12px] leading-tight truncate font-medium text-primary">
            {isCreating ? "Creating..." : "New Chat"}
          </p>
          <p className="text-[9px] text-primary/60 mt-0.5">
            {isCreating ? "Setting up session" : "Start typing to begin"}
          </p>
        </div>
      )}
    </motion.div>
  );
});
DraftSessionItem.displayName = "DraftSessionItem";

const TypingTitle = ({ text }: { text: string }) => {
  const [displayedText, setDisplayedText] = useState(text);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    // Only animate if text changed AND it's not the initial mount or empty
    if (text !== displayedText) {
      setIsTyping(true);
      let i = 0;
      setDisplayedText("");
      const speed = 30;

      const interval = setInterval(() => {
        setDisplayedText(text.slice(0, i + 1));
        i++;
        if (i >= text.length) {
          clearInterval(interval);
          setIsTyping(false);
          setDisplayedText(text);
        }
      }, speed);

      return () => clearInterval(interval);
    }
  }, [text]);

  return (
    <>
      {displayedText}
      {(isTyping || !displayedText) && <span className="animate-pulse font-bold text-primary">|</span>}
    </>
  );
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
  const intent = detectChatIntent(chat.title);
  const isAutoTitle = chat.title === "New Chat" || chat.title === "Untitled";

  return (
    <motion.div
      ref={ref}
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        "group relative flex items-center gap-1.5 px-2 py-1.5 rounded-md cursor-pointer transition-all",
        isActive
          ? "bg-sidebar-accent/70 border border-primary/20"
          : "hover:bg-sidebar-accent/40"
      )}
      onClick={() => onSelect(chat.id)}
    >
      {/* Intent-based Icon */}
      <IntentIcon intent={intent} isActive={isActive} />

      {expanded && (
        <>
          {/* Text Content - fixed width constraints */}
          <div className="flex-1 min-w-0 overflow-hidden">
            {/* Session Title with Tooltip */}
            <TooltipProvider delayDuration={500}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <p
                    className={cn(
                      "text-[12px] leading-tight truncate block w-full",
                      isActive ? "font-medium text-sidebar-foreground" : "text-sidebar-foreground/90",
                      isAutoTitle && "text-muted-foreground italic"
                    )}
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '100%'
                    }}
                  >
                    <TypingTitle text={chat.title} />
                  </p>
                </TooltipTrigger>
                <TooltipContent side="right" className="max-w-[280px] break-words">
                  <p className="text-xs">{chat.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    {format(new Date(chat.updatedAt), "MMM d, yyyy 'at' h:mm a")}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {/* Date - subtle */}
            <p className="text-[9px] text-muted-foreground/50 mt-0.5">
              {format(new Date(chat.updatedAt), "MMM d")}
            </p>
          </div>

          {/* Pin indicator */}
          {chat.isPinned && (
            <Pin className="w-2.5 h-2.5 text-primary/60 rotate-45 shrink-0" />
          )}

          {/* Three dots menu - visible on hover */}
          <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity rounded-md hover:bg-sidebar-accent"
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

export const ChatSidebar = () => {
  const isMobile = useIsMobile();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showAllTasks, setShowAllTasks] = useState(false);
  const { logout } = useAuthStore();
  const {
    chats,
    currentChatId,
    isDraftSession,
    isCreatingSession,
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
    isStreaming,
    hasMore,
    loadChatsFromBackend,
    loadTasksFromBackend,
  } = useChatStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [isDark, setIsDark] = useState(false);
  const [profileAvatar, setProfileAvatar] = useState<string | null>(null);
  const [profileName, setProfileName] = useState<string>("User");
  const [historyFilter, setHistoryFilter] = useState<"recent" | "saved">("recent");
  const [tasksFilter, setTasksFilter] = useState<"pending" | "completed">("pending");
  const [mediaFilter, setMediaFilter] = useState<"all" | "favorite">("all");
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
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [isRefreshingTasks, setIsRefreshingTasks] = useState(false);

  // Usage stats for sidebar - default to 0 used, no warning
  // FREE_LIMIT: 50 requests/day - users need own API key after
  const [usageStats, setUsageStats] = useState<{
    free_requests_remaining: number;
    free_requests_used: number;
    free_limit: number;
    warning_level: string | null;
    has_personal_keys: boolean;
    total_keys_count: number;
    reset_time_formatted: string | null;
    current_key_source: "platform" | "user" | "none";
    active_key_label: string | null;
    total_requests_today: number;
  }>({
    free_requests_remaining: 50,
    free_requests_used: 0,
    free_limit: 50,
    warning_level: null,
    has_personal_keys: false,
    total_keys_count: 0,
    reset_time_formatted: null,
    current_key_source: "platform",
    active_key_label: null,
    total_requests_today: 0,
  });

  // Theme from store
  const { theme, setTheme } = useThemeStore();

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

  // Defensive access to store state
  const { profile } = useProfileStore();

  // Load profile info for sidebar
  useEffect(() => {
    setProfileAvatar(profile?.avatarUrl || "");
    setProfileName(profile?.name || "User");
  }, [profile]);

  // Load usage stats for sidebar
  const loadUsageStats = useCallback(async () => {
    try {
      const res = await apiKeysAPI.getUsage();
      if (!res.error && res.data) {
        setUsageStats({
          free_requests_remaining: res.data.free_requests_remaining,
          free_requests_used: res.data.free_requests_used,
          free_limit: res.data.free_limit,
          warning_level: res.data.warning_level || null,
          has_personal_keys: res.data.has_personal_keys || false,
          total_keys_count: res.data.total_keys_count || 0,
          reset_time_formatted: res.data.reset_time_formatted || null,
          current_key_source: res.data.current_key_source || "platform",
          active_key_label: res.data.active_key_label || null,
          total_requests_today: res.data.total_requests_today || 0,
        });
      }
    } catch (error) {
      console.error("Failed to load usage stats:", error);
    }
  }, []);

  useEffect(() => {
    loadUsageStats();
    // Refresh every 30 seconds
    const interval = setInterval(loadUsageStats, 30000);
    return () => clearInterval(interval);
  }, [loadUsageStats]);

  // Load tasks from backend on mount
  useEffect(() => {
    loadTasksFromBackend();
  }, [loadTasksFromBackend]);

  // Refresh tasks handler with loading state
  const handleRefreshTasks = useCallback(async () => {
    if (isRefreshingTasks) return;
    setIsRefreshingTasks(true);
    try {
      await loadTasksFromBackend();
      toast({
        title: "Tasks refreshed",
        description: "Task list updated from server",
        duration: 2000
      });
    } catch (error) {
      console.error("Failed to refresh tasks:", error);
      toast({
        title: "Refresh failed",
        description: "Could not refresh tasks",
        variant: "destructive"
      });
    } finally {
      setIsRefreshingTasks(false);
    }
  }, [loadTasksFromBackend, isRefreshingTasks, toast]);

  // Auto-refresh tasks every 30 seconds for real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      loadTasksFromBackend();
    }, 30000);
    return () => clearInterval(interval);
  }, [loadTasksFromBackend]);

  // Refresh usage stats when streaming completes (message finalized)
  const prevIsStreaming = useRef(isStreaming);
  useEffect(() => {
    // Detect transition from streaming -> not streaming (message completed)
    if (prevIsStreaming.current && !isStreaming) {
      // Refresh usage stats after a short delay (wait for backend to finalize)
      // Use two-stage refresh: immediate + delayed for accuracy
      setTimeout(loadUsageStats, 300);   // Quick refresh for UI responsiveness
      setTimeout(loadUsageStats, 1500);  // Delayed refresh to ensure backend finished
    }
    prevIsStreaming.current = isStreaming;
  }, [isStreaming, loadUsageStats]);

  // Remove duplicates by ID - MongoDB is source of truth
  const uniqueChats = (chats || []).reduce((acc: Chat[], chat: Chat) => {
    if (!acc.find(c => c.id === chat.id)) {
      acc.push(chat);
    }
    return acc;
  }, []);

  const filteredChats = uniqueChats
    // Show active chat even if it's still empty so users can see/rename it
    .filter((chat) => {
      const hasMessages = (chat.messages?.length || 0) > 0 || (chat.messageCount && chat.messageCount > 0);
      const isActive = chat.id === currentChatId;
      return hasMessages || isActive;
    })
    .filter((chat) => (chat.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
    // Sort by pinned first, then by updatedAt (MongoDB data)
    .sort((a, b) => {
      if (a.isPinned && !b.isPinned) return -1;
      if (!a.isPinned && b.isPinned) return 1;
      // Safe date comparison
      const dateA = a.updatedAt instanceof Date ? a.updatedAt : new Date(a.updatedAt || 0);
      const dateB = b.updatedAt instanceof Date ? b.updatedAt : new Date(b.updatedAt || 0);
      return dateB.getTime() - dateA.getTime();
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



  const handleSelectChat = useDebouncedCallback((id: string) => {
    // Only navigate - Chat.tsx will handle loading via sessionId effect
    navigate(`/chat/${id}`);
  }, 150);

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
            : { width: sidebarExpanded ? 240 : 64 }
        }
        transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        className={cn(
          "h-screen bg-sidebar border-r border-sidebar-border flex flex-col overflow-hidden",
          isMobile
            ? "fixed top-0 left-0 z-50 w-[85vw] max-w-[240px]"
            : "relative shrink-0",
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
                    onClick={() => {
                      // Enter draft mode - NO backend call
                      // Session will be created when user sends first message
                      useChatStore.getState().startDraftSession();
                      navigate('/chat');
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
        <div className="px-3">
          {sidebarExpanded ? (
            <div className="flex items-center w-full border-b border-sidebar-border/50">
              {[
                { id: "history" as const, label: "History", icon: MessageSquare },
                { id: "tasks" as const, label: "Tasks", icon: CheckSquare },
                { id: "media" as const, label: "Media", icon: Music },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-[13px] font-medium transition-all duration-200 relative",
                    "min-w-0 whitespace-nowrap",
                    activeTab === tab.id
                      ? "text-sidebar-foreground"
                      : "text-muted-foreground hover:text-sidebar-foreground"
                  )}
                >
                  <tab.icon className={cn(
                    "w-4 h-4 shrink-0 transition-colors",
                    activeTab === tab.id ? "text-primary" : ""
                  )} />
                  <span className="truncate">{tab.label}</span>
                  {/* Active indicator */}
                  {activeTab === tab.id && (
                    <motion.div
                      layoutId="activeTabIndicator"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full"
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {/* New Chat (collapsed) */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        // Enter draft mode - NO backend call
                        useChatStore.getState().startDraftSession();
                        navigate('/chat');
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
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setActiveTab("media")}
                      className={cn(
                        "text-sidebar-foreground rounded-full",
                        activeTab === "media" && "bg-sidebar-accent"
                      )}
                    >
                      <Music className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8} align="center">
                    <p>Media</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          )}
        </div>

        {/* Search (hidden when collapsed) */}
        {sidebarExpanded && (
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 bg-sidebar-accent/50 rounded-lg px-3 py-2 h-9">
              <Search className="w-4 h-4 text-muted-foreground shrink-0" />
              <Input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-0 h-auto text-sm placeholder:text-muted-foreground/70"
                aria-label="Search chats and tasks"
              />
            </div>
          </div>
        )}

        {/* Filter Tabs - Show for History, Tasks, and Media */}
        {sidebarExpanded && (activeTab === "history" || activeTab === "tasks" || activeTab === "media") && (
          <div className="px-3 pb-2">
            {activeTab === "history" && (
              <div className="flex gap-1">
                <button
                  onClick={() => setHistoryFilter("recent")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    historyFilter === "recent"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <Clock className="w-3.5 h-3.5" />
                  Recent
                </button>
                <button
                  onClick={() => setHistoryFilter("saved")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    historyFilter === "saved"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <Bookmark className="w-3.5 h-3.5" />
                  Saved
                </button>
              </div>
            )}
            {activeTab === "tasks" && (
              <div className="flex gap-1 items-center">
                <button
                  onClick={() => setTasksFilter("pending")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    tasksFilter === "pending"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <CircleDot className="w-3.5 h-3.5" />
                  Pending
                </button>
                <button
                  onClick={() => setTasksFilter("completed")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    tasksFilter === "completed"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Completed
                </button>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={handleRefreshTasks}
                        disabled={isRefreshingTasks}
                        className={cn(
                          "p-2 rounded-md transition-colors",
                          "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                          isRefreshingTasks && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        <RefreshCw className={cn("w-3.5 h-3.5", isRefreshingTasks && "animate-spin")} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>Refresh tasks</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            )}
            {activeTab === "media" && (
              <div className="flex gap-1">
                <button
                  onClick={() => setMediaFilter("all")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    mediaFilter === "all"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                  All Media
                </button>
                <button
                  onClick={() => setMediaFilter("favorite")}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium rounded-md transition-colors",
                    mediaFilter === "favorite"
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <Heart className="w-3.5 h-3.5" />
                  Favorites
                </button>
              </div>
            )}
          </div>
        )}

        {/* Content (hidden when collapsed) */}
        {sidebarExpanded && (
          <ScrollArea className="flex-1 pl-2 pr-3 sm:pl-2 sm:pr-3 md:pl-2 md:pr-4 no-scrollbar overflow-hidden">
            {/* History Tab Content */}
            {activeTab === "history" && (
              <motion.div
                key="history"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="space-y-1 md:space-y-2 pb-4 w-full max-w-full overflow-hidden"
              >
                {/* Draft Session Indicator - Shows when in new chat mode */}
                <AnimatePresence>
                  {(isDraftSession || isCreatingSession) && historyFilter === "recent" && (
                    <DraftSessionItem
                      key="draft-session"
                      isCreating={isCreatingSession}
                      expanded={sidebarExpanded}
                    />
                  )}
                </AnimatePresence>

                {/* Loading skeleton for chat history */}
                {isLoadingChats ? (
                  <ChatListSkeleton />
                ) : (
                  <>
                    {(() => {
                      const chatsToShow = filteredChats.filter((chat: any) =>
                        historyFilter === "recent" ? !chat.isSaved : !!chat.isSaved
                      );

                      // Group chats by date
                      const grouped = chatsToShow.reduce((acc: Record<string, any[]>, chat: any) => {
                        const group = getDateGroup(new Date(chat.updatedAt));
                        if (!acc[group]) acc[group] = [];
                        acc[group].push(chat);
                        return acc;
                      }, {});

                      const groupOrder = ["Today", "Yesterday", "This Week", "Older"];

                      return groupOrder.map(groupName => {
                        const groupChats = grouped[groupName];
                        if (!groupChats || groupChats.length === 0) return null;

                        return (
                          <div key={groupName} className="mb-3">
                            <p className="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wider mb-1.5 px-1">
                              {groupName}
                            </p>
                            <div className="space-y-0.5">
                              {groupChats.map((chat: any, index: number) => (
                                <SidebarChatItem
                                  key={chat.id}
                                  ref={index === groupChats.length - 1 && groupName === groupOrder[groupOrder.length - 1] ? lastChatElementRef : null}
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
                            </div>
                          </div>
                        );
                      });
                    })()}
                    {filteredChats.filter((chat: any) =>
                      historyFilter === "recent" ? !chat.isSaved : !!chat.isSaved
                    ).length === 0 && !isDraftSession && !isCreatingSession && sidebarExpanded && (
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
            )}

            {/* Tasks Tab Content */}
            {activeTab === "tasks" && (
              <motion.div
                key="tasks"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="space-y-3 pb-4 w-full max-w-full overflow-hidden"
              >
                {sidebarExpanded && (
                  <>
                    {tasksFilter === "pending" && pendingTasks.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 mb-3 px-1">
                          <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                          <p className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">
                            Pending
                          </p>
                          <span className="ml-auto text-[10px] font-medium text-muted-foreground bg-sidebar-accent/60 px-2 py-0.5 rounded-full">
                            {pendingTasks.length}
                          </span>
                        </div>
                        <div className="space-y-2">
                          {(showAllTasks ? pendingTasks : pendingTasks.slice(0, 5)).map((task, index) => (
                            <motion.div
                              key={task.id}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ duration: 0.2, delay: index * 0.03 }}
                              className={cn(
                                "group relative rounded-lg overflow-hidden transition-all duration-200",
                                "bg-transparent hover:bg-sidebar-accent/50",
                                "border border-transparent hover:border-sidebar-border/50",
                                "p-2 max-w-full"
                              )
                              }>
                              <div className="flex items-start gap-2.5">
                                {/* Premium Checkbox */}
                                <div className="relative mt-0.5">
                                  <input
                                    type="checkbox"
                                    checked={task.completed}
                                    onChange={() => toggleTask(task.id)}
                                    className="sr-only peer"
                                    id={`task-${task.id}`}
                                  />
                                  <label
                                    htmlFor={`task-${task.id}`}
                                    className={cn(
                                      "w-5 h-5 rounded-md border-2 flex items-center justify-center cursor-pointer transition-all",
                                      "border-muted-foreground/30 hover:border-primary/60",
                                      "peer-checked:bg-primary peer-checked:border-primary"
                                    )}
                                  >
                                    {task.completed && (
                                      <CheckCircle2 className="w-3.5 h-3.5 text-primary-foreground" />
                                    )}
                                  </label>
                                </div>

                                {/* Task Content */}
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-foreground leading-tight line-clamp-2">
                                    {task.title}
                                  </p>
                                  {(task.dueDate || task.timeSeconds || task.imageUrl || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds || taskMeta[task.id]?.imageUrl) && (
                                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                      {(task.dueDate || taskMeta[task.id]?.date) && (
                                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground/80">
                                          {task.dueDate ? format(task.dueDate, "MMM d, h:mm a") : (taskMeta[task.id]?.date ? format(taskMeta[task.id]!.date!, "MMM d") : null)}
                                        </span>
                                      )}
                                      {(task.imageUrl || taskMeta[task.id]?.imageUrl) && (
                                        <span className="inline-flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded-md">
                                          📎 Image
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>

                                {/* Actions */}
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className={cn(
                                        "w-7 h-7 rounded-lg shrink-0 transition-opacity",
                                        isMobile ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                                      )}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreVertical className="w-4 h-4 text-muted-foreground" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" sideOffset={4}>
                                    <DropdownMenuItem
                                      onClick={() => {
                                        setEditTaskId(task.id);
                                        setTaskTitle(task.title);
                                        setTaskDescription(taskMeta[task.id]?.description || "");
                                        setTaskDate(task.dueDate || taskMeta[task.id]?.date);
                                        setTaskTimeSeconds(task.timeSeconds || taskMeta[task.id]?.timeSeconds || 0);
                                        setTaskImageUrl(task.imageUrl || taskMeta[task.id]?.imageUrl);
                                        setTaskDialogOpen(true);
                                      }}
                                      className="gap-2"
                                    >
                                      <Edit className="w-3.5 h-3.5" />
                                      Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => {
                                        setTaskMeta((prev) => ({
                                          ...prev,
                                          [task.id]: { ...prev[task.id], pinned: !prev[task.id]?.pinned },
                                        }));
                                      }}
                                      className="gap-2"
                                    >
                                      <Pin className="w-3.5 h-3.5" />
                                      {taskMeta[task.id]?.pinned ? "Unpin" : "Pin"}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => navigator.clipboard?.writeText(`Task: ${task.title}`)}
                                      className="gap-2"
                                    >
                                      <Share2 className="w-3.5 h-3.5" />
                                      Share
                                    </DropdownMenuItem>
                                    <DropdownMenuItem className="text-destructive gap-2" onClick={() => deleteTask(task.id)}>
                                      <Trash2 className="w-3.5 h-3.5" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            </motion.div>
                          ))}
                          {pendingTasks.length > 5 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="w-full text-xs text-muted-foreground/70 mt-2 h-8 rounded-lg hover:bg-amber-500/5 hover:text-amber-400"
                              onClick={() => setShowAllTasks(!showAllTasks)}
                            >
                              {showAllTasks ? "Show less" : `Show ${pendingTasks.length - 5} more`}
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                    {tasksFilter === "completed" && completedTasks.length > 0 && (
                      <div>
                        {/* Premium Completed Header */}
                        <div className="flex items-center gap-2 mb-3">
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-emerald-500" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-500">
                              Completed
                            </span>
                          </div>
                          <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-500/10 text-emerald-400">
                            {completedTasks.length}
                          </span>
                        </div>
                        <div className="space-y-2">
                          {(showAllTasks ? completedTasks : completedTasks.slice(0, 5)).map((task, index) => (
                            <motion.div
                              key={task.id}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: index * 0.05, duration: 0.2 }}
                              className="group relative p-1.5 rounded-lg bg-transparent hover:bg-emerald-500/5 border border-transparent hover:border-emerald-500/10 transition-all duration-200 w-full max-w-[95%] overflow-hidden"
                            >
                              <div className="flex items-start gap-2.5">
                                {/* Premium Checkbox */}
                                <label className="relative flex items-center justify-center w-5 h-5 mt-0.5 shrink-0 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={task.completed}
                                    onChange={() => toggleTask(task.id)}
                                    className="sr-only peer"
                                  />
                                  <div className="w-5 h-5 rounded-md bg-emerald-500/20 border-2 border-emerald-500/40 peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-all duration-200 flex items-center justify-center">
                                    <Check className="w-3 h-3 text-white" />
                                  </div>
                                </label>
                                <div className="flex-1 min-w-0 overflow-hidden">
                                  <p className="text-sm font-medium text-muted-foreground/60 line-through truncate">{task.title}</p>
                                  {/* Task metadata badges */}
                                  {(task.dueDate || task.timeSeconds || task.imageUrl || taskMeta[task.id]?.date || taskMeta[task.id]?.timeSeconds || taskMeta[task.id]?.imageUrl) && (
                                    <div className="flex flex-wrap gap-1.5 mt-2">
                                      {(task.dueDate || taskMeta[task.id]?.date) && (
                                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground/60">
                                          {task.dueDate ? format(task.dueDate, "MMM d") : format(taskMeta[task.id]!.date!, "dd/MM")}
                                        </span>
                                      )}
                                      {(task.imageUrl || taskMeta[task.id]?.imageUrl) && (
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded-md bg-emerald-500/10 text-emerald-400/60">
                                          <ImageIcon className="w-3 h-3" />
                                          attached
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon-sm"
                                      className={cn(isMobile ? "opacity-100" : "opacity-0 group-hover:opacity-100", "shrink-0 h-7 w-7 rounded-lg hover:bg-emerald-500/10")}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreVertical className="w-3.5 h-3.5 text-muted-foreground" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" sideOffset={4} className="min-w-[140px]">
                                    <DropdownMenuItem onClick={() => toggleTask(task.id)} className="gap-2">
                                      <RotateCcw className="w-3.5 h-3.5" />
                                      Restore
                                    </DropdownMenuItem>
                                    <DropdownMenuItem className="text-destructive gap-2" onClick={() => deleteTask(task.id)}>
                                      <Trash2 className="w-3.5 h-3.5" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            </motion.div>
                          ))}
                          {completedTasks.length > 5 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="w-full text-xs text-muted-foreground/70 mt-2 h-8 rounded-lg hover:bg-emerald-500/5 hover:text-emerald-400"
                              onClick={() => setShowAllTasks(!showAllTasks)}
                            >
                              {showAllTasks ? "Show less" : `Show ${completedTasks.length - 5} more`}
                            </Button>
                          )}
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

            {/* Media Tab Content */}
            {activeTab === "media" && (
              <motion.div
                key="media"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="pb-4 w-full max-w-full overflow-hidden"
              >
                <MediaLibrary searchQuery={searchQuery} filter={mediaFilter} />
              </motion.div>
            )}
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
                  // await new Promise((res) => setTimeout(res, 1000)); // Real API now

                  if (editTaskId) {
                    // Local edit for now (until updateTask is fully implemented in store)
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
                    // Create task in backend (supports all fields now)
                    await createTask(
                      taskTitle,
                      taskDescription,
                      taskDate,
                      taskTimeSeconds,
                      taskImageUrl
                    );
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

        {/* User Profile Modal */}
        <UserProfileModal open={profileModalOpen} onOpenChange={setProfileModalOpen} />

        {/* User Section */}
        {/* Quick Stats & Theme Bar - Above Profile */}
        <div className={cn(
          "px-3 py-2 border-t border-sidebar-border/50",
          !sidebarExpanded && "flex flex-col items-center gap-2"
        )}>
          {sidebarExpanded ? (
            /* Expanded sidebar - horizontal layout */
            <div className="flex items-center justify-between">
              {/* API Source & Usage Indicator */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 cursor-default">
                      {usageStats.current_key_source === "user" ? (
                        <>
                          <Key className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-500 flex-shrink-0" />
                          <span className="text-[10px] sm:text-xs font-medium text-emerald-500 whitespace-nowrap">
                            Your Key{usageStats.active_key_label && <span className="text-muted-foreground/70 ml-0.5">#{usageStats.active_key_label.replace(/[^0-9]/g, '') || '1'}</span>}
                          </span>
                        </>
                      ) : (
                        <>
                          <Zap className={cn(
                            "w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0",
                            usageStats.warning_level === "critical" ? "text-destructive" :
                              usageStats.warning_level === "low" ? "text-yellow-500" : "text-blue-400"
                          )} />
                          <span className={cn(
                            "text-[10px] sm:text-xs font-medium tabular-nums whitespace-nowrap",
                            usageStats.warning_level === "critical" ? "text-destructive" :
                              usageStats.warning_level === "low" ? "text-yellow-500" : "text-blue-400"
                          )}>
                            {usageStats.free_requests_used}<span className="text-muted-foreground/70">/{usageStats.free_limit}</span>
                          </span>
                        </>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="text-xs max-w-[200px]">
                    {usageStats.current_key_source === "user"
                      ? `Using your API key${usageStats.active_key_label ? ` (${usageStats.active_key_label})` : ''} • ${usageStats.total_requests_today} requests today`
                      : `${usageStats.free_requests_remaining} free requests remaining • Resets daily`
                    }
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* Theme Toggle Icons */}
              <div className="flex items-center gap-0.5">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setTheme("light")}
                        className={cn(
                          "p-1.5 rounded-md transition-all",
                          theme === "light"
                            ? "text-primary bg-primary/10"
                            : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent"
                        )}
                      >
                        <Sun className="w-3.5 h-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="text-xs">Light</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setTheme("dark")}
                        className={cn(
                          "p-1.5 rounded-md transition-all",
                          theme === "dark"
                            ? "text-primary bg-primary/10"
                            : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent"
                        )}
                      >
                        <Moon className="w-3.5 h-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="text-xs">Dark</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setTheme("black")}
                        className={cn(
                          "p-1.5 rounded-md transition-all",
                          theme === "black"
                            ? "text-primary bg-primary/10"
                            : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent"
                        )}
                      >
                        <Monitor className="w-3.5 h-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="text-xs">AMOLED</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>
          ) : (
            /* Collapsed sidebar - show icons vertically */
            <>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className={cn(
                      "w-9 h-9 rounded-lg flex flex-col items-center justify-center cursor-default",
                      usageStats.current_key_source === "user"
                        ? "bg-emerald-500/15"
                        : usageStats.warning_level === "critical" ? "bg-destructive/15" :
                          usageStats.warning_level === "low" ? "bg-yellow-500/15" : "bg-emerald-500/15"
                    )}>
                      {usageStats.current_key_source === "user" ? (
                        <Key className="w-4 h-4 text-emerald-500" />
                      ) : (
                        <>
                          <span className={cn(
                            "text-sm font-bold tabular-nums leading-none",
                            usageStats.warning_level === "critical" ? "text-destructive" :
                              usageStats.warning_level === "low" ? "text-yellow-500" : "text-emerald-500"
                          )}>
                            {usageStats.free_requests_used}
                          </span>
                          <span className="text-[8px] text-muted-foreground leading-none">free</span>
                        </>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs p-2">
                    {usageStats.current_key_source === "user" ? (
                      <>
                        <div className="font-medium text-emerald-500">🔑 Using Your API Key</div>
                        {usageStats.active_key_label && (
                          <div className="text-muted-foreground text-[10px] mt-0.5">{usageStats.active_key_label}</div>
                        )}
                        <div className="text-muted-foreground text-[10px] mt-0.5">
                          {usageStats.total_requests_today} requests today
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="font-medium">{usageStats.free_requests_used}/{usageStats.free_limit} free requests</div>
                        <div className="text-muted-foreground text-[10px] mt-0.5">
                          {usageStats.free_requests_remaining} remaining • Resets daily
                        </div>
                      </>
                    )}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => {
                        const themes: Theme[] = ["light", "dark", "black"];
                        const currentIndex = themes.indexOf(theme);
                        const nextTheme = themes[(currentIndex + 1) % themes.length];
                        setTheme(nextTheme);
                      }}
                      className="p-1.5 rounded-md text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent transition-all"
                    >
                      {theme === "light" ? <Sun className="w-4 h-4" /> :
                        theme === "dark" ? <Moon className="w-4 h-4" /> :
                          <Monitor className="w-4 h-4" />}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs">Theme: {theme}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </>
          )}
        </div>

        {/* User Profile Section */}
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
                  <button
                    onClick={() => setProfileModalOpen(true)}
                    className="w-9 h-9 md:w-10 md:h-10 rounded-full overflow-hidden bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center border border-border hover:ring-2 hover:ring-primary/50 transition-all cursor-pointer"
                  >
                    {profileAvatar ? (
                      <img src={profileAvatar} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-4 h-4 md:w-5 md:h-5 text-primary-foreground" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side={sidebarExpanded ? "bottom" : "right"} sideOffset={8} align="center">
                  <p>View Profile</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {sidebarExpanded && (
              <>
                <button
                  onClick={() => setProfileModalOpen(true)}
                  className="flex-1 min-w-0 overflow-hidden text-left hover:opacity-80 transition-opacity cursor-pointer"
                >
                  <p className="text-sm font-medium text-sidebar-foreground truncate max-w-full">
                    {profileName || "User"}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">Free Plan</p>
                </button>
                <div className="flex gap-1">
                  {/* Settings/Profile Button */}
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="text-muted-foreground hover:text-primary hover:bg-primary/10"
                          onClick={() => setProfileModalOpen(true)}
                        >
                          <Settings className="w-4 h-4 md:w-5 md:h-5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Profile Settings</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  {/* Logout Button */}
                  <AlertDialog>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
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
