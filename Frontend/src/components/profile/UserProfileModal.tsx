/**
 * 👤 PREMIUM USER PROFILE MODAL
 * 
 * Features:
 * - Tab navigation (Profile, API, Settings)
 * - Beautiful card design with profile info layout
 * - Theme switcher (Light, Dark, Black)
 * - Avatar upload with preview
 * - Smooth animations
 */

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useProfileStore } from "@/stores/profileStore";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Mail,
  MapPin,
  Edit3,
  Save,
  X,
  Heart,
  Loader2,
  Plus,
  LogOut,
  Trash2,
  AlertTriangle,
  Camera,
  Sun,
  Moon,
  Monitor,
  Check,
  User,
  Key,
  Settings,
  Copy,
  Eye,
  EyeOff,
  RefreshCw,
  Info,
  ExternalLink,
  Sparkles,
  Zap,
  Clock,
  ChevronUp,
  ChevronDown,
  Activity,
  Shield,
  Bell,
  Volume2,
  Gauge,
} from "lucide-react";
import { userAPI, apiKeysAPI } from "@/lib/api";
import type { Theme } from "@/lib/theme";

// Tab type
type TabType = "profile" | "api" | "settings";

// Theme Button Component
interface ThemeButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

const ThemeButton = ({ active, onClick, icon, label }: ThemeButtonProps) => (
  <button
    onClick={onClick}
    className={cn(
      "flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium transition-all",
      active 
        ? "bg-foreground text-background" 
        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
    )}
  >
    {icon}
    <span>{label}</span>
  </button>
);

// Tab Button Component
interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

const TabButton = ({ active, onClick, icon, label }: TabButtonProps) => (
  <button
    onClick={onClick}
    className={cn(
      "flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-all relative",
      active 
        ? "text-foreground" 
        : "text-muted-foreground hover:text-foreground"
    )}
  >
    <span className={cn(
      "transition-colors",
      active ? "text-primary" : "text-muted-foreground"
    )}>
      {icon}
    </span>
    <span>{label}</span>
    {active && (
      <motion.div
        layoutId="activeTab"
        className="absolute bottom-0 left-3 right-3 h-0.5 bg-primary rounded-full"
        transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
      />
    )}
  </button>
);

interface UserProfileModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const UserProfileModal = ({ open, onOpenChange }: UserProfileModalProps) => {
  const { profile, isLoading, isSaving, loadProfileFromBackend, saveProfileToBackend } = useProfileStore();
  const { logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const { toast } = useToast();
  
  const [activeTab, setActiveTab] = useState<TabType>("profile");
  const [isEditing, setIsEditing] = useState(false);
  const [editedProfile, setEditedProfile] = useState(profile);
  const [newHobby, setNewHobby] = useState("");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deletionStep, setDeletionStep] = useState(0);
  const [deletionComplete, setDeletionComplete] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // API Keys State (Enhanced for BYOK with rotation)
  const [usageData, setUsageData] = useState<{
    free_requests_used: number;
    free_limit: number;
    free_requests_remaining: number;
    has_personal_keys: boolean;
    active_keys_count: number;
    exhausted_keys_count: number;
    total_keys_count: number;
    max_keys_allowed: number;
    can_make_requests: boolean;
    current_key_source: string;
    active_key_label: string | null;
    // Enhanced fields
    warning_level: string | null; // "low", "critical", null
    reset_time_seconds: number | null;
    reset_time_formatted: string | null;
    total_requests_today: number;
  } | null>(null);
  const [apiKeys, setApiKeys] = useState<Array<{
    id: string;
    provider: string;
    model: string;
    label: string;
    masked_key: string;
    is_active: boolean;
    is_exhausted_today: boolean;
    is_valid: boolean;
    last_exhausted_at: string | null;
    created_at: string;
    last_used: string | null;
    priority: number;
    requests_today: number;
  }>>([]);
  const [dashboardMessages, setDashboardMessages] = useState<string[]>([]);
  const [newApiKey, setNewApiKey] = useState("");
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [isValidatingKey, setIsValidatingKey] = useState(false);
  const [isAddingKey, setIsAddingKey] = useState(false);
  const [showAddKeyForm, setShowAddKeyForm] = useState(false);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showNewKey, setShowNewKey] = useState(false);
  const [isHealthChecking, setIsHealthChecking] = useState(false);
  const [healthCheckingKeyId, setHealthCheckingKeyId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [countdownTime, setCountdownTime] = useState<string | null>(null);
  
  // Quick settings toggles
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundsEnabled, setSoundsEnabled] = useState(false);

  // Deletion steps for progress animation
  const deletionSteps = [
    { label: "Removing chat sessions", icon: "💬" },
    { label: "Clearing memories & AI data", icon: "🧠" },
    { label: "Deleting tasks & agents", icon: "🤖" },
    { label: "Wiping vector database", icon: "📊" },
    { label: "Cleaning up account", icon: "✨" },
  ];

  // Load profile when modal opens
  useEffect(() => {
    if (open) {
      loadProfileFromBackend();
      // Also load API data for the stats bar
      loadApiData();
    }
  }, [open, loadProfileFromBackend]);

  // Reload API data when API tab is selected (for fresh data)
  useEffect(() => {
    if (open && activeTab === "api") {
      loadApiData();
    }
  }, [activeTab]);

  // Countdown timer effect
  useEffect(() => {
    if (!usageData?.reset_time_seconds) {
      setCountdownTime(null);
      return;
    }
    
    let remaining = usageData.reset_time_seconds;
    setCountdownTime(usageData.reset_time_formatted || formatCountdown(remaining));
    
    const interval = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(interval);
        // Reload data when timer hits 0
        loadApiData();
      } else {
        setCountdownTime(formatCountdown(remaining));
      }
    }, 1000);
    
    return () => clearInterval(interval);
  }, [usageData?.reset_time_seconds]);

  const formatCountdown = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const loadApiData = async () => {
    setLoadingKeys(true);
    try {
      // Use dashboard endpoint for full data
      const dashboardRes = await apiKeysAPI.getDashboard();
      
      if (!dashboardRes.error && dashboardRes.data) {
        setUsageData(dashboardRes.data.usage);
        setApiKeys(dashboardRes.data.keys || []);
        setDashboardMessages(dashboardRes.data.messages || []);
      } else {
        // Fallback to individual endpoints
        const [usageRes, keysRes] = await Promise.all([
          apiKeysAPI.getUsage(),
          apiKeysAPI.getKeys()
        ]);
        
        if (!usageRes.error && usageRes.data) {
          setUsageData(usageRes.data);
        }
        if (!keysRes.error && keysRes.data) {
          setApiKeys(keysRes.data || []);
        }
      }
    } catch (error) {
      console.error("Failed to load API data:", error);
    } finally {
      setLoadingKeys(false);
    }
  };

  const handleAddKey = async () => {
    if (!newApiKey.trim()) {
      toast({
        title: "❌ Error",
        description: "Please enter an API key",
        variant: "destructive",
      });
      return;
    }

    // Check if max keys reached
    if (usageData && usageData.total_keys_count >= usageData.max_keys_allowed) {
      toast({
        title: "❌ Limit Reached",
        description: `You can store up to ${usageData.max_keys_allowed} API keys. Please delete one to add a new key.`,
        variant: "destructive",
      });
      return;
    }

    setIsValidatingKey(true);
    try {
      // First validate the key
      const validateRes = await apiKeysAPI.validateKey(newApiKey.trim());
      
      if (validateRes.error || !validateRes.data?.valid) {
        toast({
          title: "❌ Invalid Key",
          description: validateRes.data?.message || "The API key is not valid. Please check and try again.",
          variant: "destructive",
        });
        setIsValidatingKey(false);
        return;
      }

      // Show warning if present
      if (validateRes.data?.warning) {
        toast({
          title: "⚠️ Warning",
          description: validateRes.data.warning,
        });
      }

      // Key is valid, now add it
      setIsValidatingKey(false);
      setIsAddingKey(true);
      
      const addRes = await apiKeysAPI.addKey(
        newApiKey.trim(), 
        "groq", 
        newKeyLabel.trim() || undefined
      );
      
      if (addRes.error) {
        // Handle specific error codes
        const errorMsg = addRes.error.toLowerCase();
        if (errorMsg.includes("max") || errorMsg.includes("limit")) {
          toast({
            title: "❌ Maximum Keys Reached",
            description: "You already have 5 API keys. Delete one to add a new key.",
            variant: "destructive",
          });
        } else if (errorMsg.includes("duplicate")) {
          toast({
            title: "❌ Duplicate Key",
            description: "This API key is already saved in your account.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "❌ Failed to Add",
            description: addRes.error,
            variant: "destructive",
          });
        }
        return;
      }

      toast({
        title: "✅ Key Added!",
        description: `API key "${newKeyLabel.trim() || 'Key'}" has been saved and activated.`,
      });

      // Reset form and reload data
      setNewApiKey("");
      setNewKeyLabel("");
      setShowAddKeyForm(false);
      loadApiData();
      
    } catch (error) {
      toast({
        title: "❌ Error",
        description: "Failed to add API key.",
        variant: "destructive",
      });
    } finally {
      setIsValidatingKey(false);
      setIsAddingKey(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      const res = await apiKeysAPI.deleteKey(keyId);
      if (res.error) {
        toast({
          title: "❌ Error",
          description: res.error,
          variant: "destructive",
        });
        return;
      }
      toast({
        title: "🗑️ Key Deleted",
        description: "API key has been removed.",
      });
      loadApiData();
    } catch (error) {
      toast({
        title: "❌ Error", 
        description: "Failed to delete key.",
        variant: "destructive",
      });
    }
  };

  const handleActivateKey = async (keyId: string) => {
    try {
      const res = await apiKeysAPI.activateKey(keyId);
      if (res.error) {
        toast({
          title: "❌ Error",
          description: res.error,
          variant: "destructive",
        });
        return;
      }
      toast({
        title: "✅ Key Activated",
        description: "This key is now active.",
      });
      loadApiData();
    } catch (error) {
      toast({
        title: "❌ Error",
        description: "Failed to activate key.",
        variant: "destructive",
      });
    }
  };

  // Health check a single key
  const handleHealthCheck = async (keyId: string) => {
    setHealthCheckingKeyId(keyId);
    try {
      const res = await apiKeysAPI.healthCheckKey(keyId);
      if (res.error) {
        toast({
          title: "❌ Health Check Failed",
          description: res.error,
          variant: "destructive",
        });
        return;
      }
      
      if (res.data?.valid) {
        toast({
          title: "✅ Key is Healthy",
          description: `"${res.data.label}" is working properly.`,
        });
      } else {
        toast({
          title: "⚠️ Key Issue Detected",
          description: res.data?.message || "Key may not be working properly.",
          variant: "destructive",
        });
      }
      loadApiData();
    } catch (error) {
      toast({
        title: "❌ Error",
        description: "Failed to check key health.",
        variant: "destructive",
      });
    } finally {
      setHealthCheckingKeyId(null);
    }
  };

  // Health check all keys
  const handleHealthCheckAll = async () => {
    setIsHealthChecking(true);
    try {
      const res = await apiKeysAPI.healthCheckAll();
      if (res.error) {
        toast({
          title: "❌ Health Check Failed",
          description: res.error,
          variant: "destructive",
        });
        return;
      }
      
      toast({
        title: "🔍 Health Check Complete",
        description: res.data?.summary || "All keys checked.",
      });
      loadApiData();
    } catch (error) {
      toast({
        title: "❌ Error",
        description: "Failed to check keys.",
        variant: "destructive",
      });
    } finally {
      setIsHealthChecking(false);
    }
  };

  // Copy masked key to clipboard
  const handleCopyKey = (maskedKey: string) => {
    navigator.clipboard.writeText(maskedKey);
    toast({
      title: "📋 Copied!",
      description: "Masked key copied to clipboard.",
    });
  };

  // Move key up in priority
  const handleMoveKeyUp = async (index: number) => {
    if (index === 0) return;
    const newOrder = [...apiKeys];
    [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
    
    try {
      const res = await apiKeysAPI.reorderKeys(newOrder.map(k => k.id));
      if (!res.error) {
        loadApiData();
      }
    } catch (error) {
      console.error("Failed to reorder keys:", error);
    }
  };

  // Move key down in priority
  const handleMoveKeyDown = async (index: number) => {
    if (index === apiKeys.length - 1) return;
    const newOrder = [...apiKeys];
    [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    
    try {
      const res = await apiKeysAPI.reorderKeys(newOrder.map(k => k.id));
      if (!res.error) {
        loadApiData();
      }
    } catch (error) {
      console.error("Failed to reorder keys:", error);
    }
  };

  // Sync edited profile when profile changes
  useEffect(() => {
    setEditedProfile(profile);
  }, [profile]);

  const handleSave = async () => {
    try {
      await saveProfileToBackend(editedProfile);
      setIsEditing(false);
      toast({
        title: "✅ Profile Updated!",
        description: "Your changes have been saved.",
      });
    } catch (error) {
      toast({
        title: "❌ Save Failed",
        description: "Could not save your profile.",
        variant: "destructive",
      });
    }
  };

  const handleCancel = () => {
    setEditedProfile(profile);
    setIsEditing(false);
  };

  const handleAvatarClick = () => {
    if (isEditing && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast({
        title: "Invalid file",
        description: "Please select an image file.",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Please select an image under 5MB.",
        variant: "destructive",
      });
      return;
    }

    setIsUploadingAvatar(true);
    
    try {
      // Convert to base64 for storage
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setEditedProfile({ ...editedProfile, avatarUrl: base64String });
        setIsUploadingAvatar(false);
        toast({
          title: "📷 Image Ready",
          description: "Click Save to update your avatar.",
        });
      };
      reader.onerror = () => {
        setIsUploadingAvatar(false);
        toast({
          title: "Upload failed",
          description: "Could not read the image file.",
          variant: "destructive",
        });
      };
      reader.readAsDataURL(file);
    } catch (error) {
      setIsUploadingAvatar(false);
      toast({
        title: "Upload failed",
        description: "Could not process the image.",
        variant: "destructive",
      });
    }
  };

  const addHobby = () => {
    if (newHobby.trim() && !editedProfile.hobbies.includes(newHobby.trim())) {
      setEditedProfile({
        ...editedProfile,
        hobbies: [...editedProfile.hobbies, newHobby.trim()],
      });
      setNewHobby("");
    }
  };

  const removeHobby = (hobby: string) => {
    setEditedProfile({
      ...editedProfile,
      hobbies: editedProfile.hobbies.filter((h) => h !== hobby),
    });
  };

  const handleLogout = () => {
    logout();
    onOpenChange(false);
    toast({
      title: "👋 Logged Out",
      description: "See you next time!",
    });
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "DELETE_MY_ACCOUNT") {
      toast({
        title: "❌ Confirmation Failed",
        description: "Please type DELETE_MY_ACCOUNT to confirm.",
        variant: "destructive",
      });
      return;
    }

    // Close the confirmation dialog and show full-screen deleting animation
    setShowDeleteDialog(false);
    setIsDeleting(true);
    setDeletionStep(0);
    setDeletionComplete(false);
    
    // Animate through deletion steps
    const stepInterval = setInterval(() => {
      setDeletionStep(prev => {
        if (prev < deletionSteps.length - 1) return prev + 1;
        clearInterval(stepInterval);
        return prev;
      });
    }, 600);
    
    try {
      const result = await userAPI.deleteAccount("DELETE_MY_ACCOUNT");
      
      if (result.error) {
        clearInterval(stepInterval);
        throw new Error(result.error);
      }
      
      // Ensure all steps complete
      clearInterval(stepInterval);
      setDeletionStep(deletionSteps.length - 1);
      
      // Show completion state
      await new Promise(resolve => setTimeout(resolve, 500));
      setDeletionComplete(true);
      
      // Logout and clear all local data
      logout();
      localStorage.clear();
      sessionStorage.clear();
      
      // Wait to show success, then redirect
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Redirect to login page
      window.location.href = "/auth";
      
    } catch (error) {
      setIsDeleting(false);
      setDeletionStep(0);
      setDeletionComplete(false);
      onOpenChange(false);
      toast({
        title: "❌ Delete Failed",
        description: "Could not delete your account. Please try again.",
        variant: "destructive",
      });
      setDeleteConfirmText("");
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "U";
  };

  return (
    <>
      {/* Full-screen Deleting Animation Overlay */}
      <AnimatePresence>
        {isDeleting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center"
          >
            {/* Blur background with theme-aware gradient */}
            <div className="absolute inset-0 bg-background/90 backdrop-blur-xl" />
            <div className="absolute inset-0 bg-gradient-to-br from-destructive/5 via-transparent to-primary/5" />
            
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="relative flex flex-col items-center gap-8 p-8 max-w-sm mx-4"
            >
              {/* Success or Deleting State */}
              <AnimatePresence mode="wait">
                {deletionComplete ? (
                  <motion.div
                    key="success"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                    className="relative"
                  >
                    <motion.div 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2, type: "spring" }}
                      className="w-28 h-28 rounded-full bg-green-500/20 flex items-center justify-center"
                    >
                      <motion.div
                        initial={{ scale: 0, rotate: -180 }}
                        animate={{ scale: 1, rotate: 0 }}
                        transition={{ delay: 0.4, type: "spring", stiffness: 200 }}
                      >
                        <Check className="w-14 h-14 text-green-500" />
                      </motion.div>
                    </motion.div>
                    {/* Success ring burst */}
                    <motion.div
                      initial={{ scale: 0.8, opacity: 1 }}
                      animate={{ scale: 2, opacity: 0 }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className="absolute inset-0 rounded-full border-4 border-green-500/50"
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="deleting"
                    exit={{ scale: 0.8, opacity: 0 }}
                    className="relative"
                  >
                    {/* Animated icon container */}
                    <motion.div
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      className="w-28 h-28 rounded-full bg-destructive/10 flex items-center justify-center relative"
                    >
                      <Trash2 className="w-12 h-12 text-destructive" />
                    </motion.div>
                    {/* Spinning ring */}
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 rounded-full"
                      style={{
                        background: `conic-gradient(from 0deg, transparent 0%, hsl(var(--destructive)) 30%, transparent 60%)`
                      }}
                    />
                    {/* Inner white ring to create arc effect */}
                    <div className="absolute inset-1 rounded-full bg-background" />
                    <div className="absolute inset-1 rounded-full bg-destructive/10 flex items-center justify-center">
                      <Trash2 className="w-12 h-12 text-destructive" />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              
              {/* Text */}
              <div className="text-center space-y-2">
                <AnimatePresence mode="wait">
                  {deletionComplete ? (
                    <motion.div
                      key="complete-text"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-2"
                    >
                      <h2 className="text-2xl font-bold text-green-500">Account Deleted</h2>
                      <p className="text-sm text-muted-foreground">Redirecting to login...</p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="progress-text"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="space-y-1"
                    >
                      <h2 className="text-xl font-semibold text-foreground">Deleting Account</h2>
                      <motion.p
                        key={deletionStep}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-sm text-muted-foreground flex items-center justify-center gap-2"
                      >
                        <span>{deletionSteps[deletionStep]?.icon}</span>
                        <span>{deletionSteps[deletionStep]?.label}</span>
                      </motion.p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              
              {/* Progress Steps */}
              {!deletionComplete && (
                <div className="w-full space-y-3">
                  {deletionSteps.map((step, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ 
                        opacity: index <= deletionStep ? 1 : 0.4,
                        x: 0
                      }}
                      transition={{ delay: index * 0.1 }}
                      className="flex items-center gap-3"
                    >
                      <motion.div
                        animate={{
                          backgroundColor: index < deletionStep 
                            ? "hsl(var(--primary))" 
                            : index === deletionStep 
                              ? "hsl(var(--destructive))" 
                              : "hsl(var(--muted))"
                        }}
                        className="w-6 h-6 rounded-full flex items-center justify-center text-xs"
                      >
                        {index < deletionStep ? (
                          <Check className="w-3.5 h-3.5 text-primary-foreground" />
                        ) : index === deletionStep ? (
                          <Loader2 className="w-3.5 h-3.5 text-destructive-foreground animate-spin" />
                        ) : (
                          <span className="text-muted-foreground">{index + 1}</span>
                        )}
                      </motion.div>
                      <span className={cn(
                        "text-sm transition-colors",
                        index < deletionStep ? "text-primary" : 
                        index === deletionStep ? "text-foreground font-medium" : 
                        "text-muted-foreground"
                      )}>
                        {step.label}
                      </span>
                    </motion.div>
                  ))}
                </div>
              )}
              
              {/* Progress bar */}
              {!deletionComplete && (
                <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: "0%" }}
                    animate={{ width: `${((deletionStep + 1) / deletionSteps.length) * 100}%` }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className="h-full bg-gradient-to-r from-destructive to-primary rounded-full"
                  />
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <Dialog open={open && !isDeleting} onOpenChange={onOpenChange}>
        <DialogContent hideClose className="w-[95vw] sm:w-[90vw] md:w-full max-w-[480px] p-0 overflow-hidden bg-background border border-border/50 shadow-xl rounded-2xl">
          {/* Visually hidden title for screen readers */}
          <DialogTitle className="sr-only">User Profile</DialogTitle>
          
          {/* Close Button - Always visible at top corner */}
          <button
            onClick={() => onOpenChange(false)}
            className="absolute -top-1 -right-1 z-20 p-1.5 rounded-full text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>

          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-20"
              >
                <div className="relative">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 animate-pulse" />
                  <Loader2 className="w-8 h-8 animate-spin text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                </div>
                <p className="text-muted-foreground text-sm mt-4">Loading...</p>
              </motion.div>
            ) : (
              <motion.div
                key="content"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col"
              >
                {/* Tab Navigation */}
                <div className="flex border-b border-border">
                  <TabButton 
                    active={activeTab === "profile"} 
                    onClick={() => setActiveTab("profile")}
                    icon={<User className="w-4 h-4" />}
                    label="Profile"
                  />
                  <TabButton 
                    active={activeTab === "api"} 
                    onClick={() => setActiveTab("api")}
                    icon={<Key className="w-4 h-4" />}
                    label="API"
                  />
                  <TabButton 
                    active={activeTab === "settings"} 
                    onClick={() => setActiveTab("settings")}
                    icon={<Settings className="w-4 h-4" />}
                    label="Settings"
                  />
                </div>

                {/* Hidden file input for avatar upload */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarChange}
                  className="hidden"
                />

                {/* Tab Content */}
                <div className="max-h-[60vh] overflow-y-auto scrollbar-none [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                  <AnimatePresence mode="wait">
                    {/* Profile Tab */}
                    {activeTab === "profile" && (
                      <motion.div
                        key="profile"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.2 }}
                        className="p-5 space-y-5 relative"
                      >
                        {/* Edit Icons - Absolute Top Right */}
                        <div className="absolute top-4 right-4 z-10">
                          {isEditing ? (
                            <div className="flex items-center gap-0.5">
                              <button
                                onClick={handleCancel}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                              >
                                <X className="w-4 h-4" />
                              </button>
                              <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="p-1.5 rounded-md text-primary hover:bg-primary/10 transition-colors disabled:opacity-50"
                              >
                                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setIsEditing(true)}
                              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                          )}
                        </div>

                        {/* Profile Header */}
                        <div className="flex items-center gap-4">
                          {/* Round Avatar */}
                          <div 
                            className={cn(
                              "relative group flex-shrink-0",
                              isEditing && "cursor-pointer"
                            )}
                            onClick={handleAvatarClick}
                          >
                            <div className="w-20 h-20 rounded-full bg-muted overflow-hidden ring-2 ring-border">
                              {isUploadingAvatar ? (
                                <div className="w-full h-full flex items-center justify-center">
                                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                </div>
                              ) : editedProfile.avatarUrl ? (
                                <img
                                  src={editedProfile.avatarUrl}
                                  alt="Avatar"
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full bg-primary/10 flex items-center justify-center">
                                  <span className="text-xl font-semibold text-primary">
                                    {getInitials(editedProfile.name || "")}
                                  </span>
                                </div>
                              )}
                            </div>
                            {isEditing && (
                              <div className="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <Camera className="w-5 h-5 text-white" />
                              </div>
                            )}
                          </div>

                          {/* Name & Email */}
                          <div className="flex-1 min-w-0">
                            {isEditing ? (
                              <Input
                                value={editedProfile.name}
                                onChange={(e) => setEditedProfile({ ...editedProfile, name: e.target.value })}
                                placeholder="Your name"
                                className="text-lg font-semibold h-10 mb-1"
                              />
                            ) : (
                              <h3 className="text-lg font-semibold truncate">{profile.name || "No name"}</h3>
                            )}
                            
                            <p className="text-sm text-muted-foreground truncate">{profile.email || "No email"}</p>
                            
                            {isEditing ? (
                              <div className="flex items-center gap-1.5 mt-1">
                                <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
                                <Input
                                  value={editedProfile.location}
                                  onChange={(e) => setEditedProfile({ ...editedProfile, location: e.target.value })}
                                  placeholder="Location"
                                  className="text-sm h-8 flex-1"
                                />
                              </div>
                            ) : profile.location ? (
                              <p className="text-sm text-muted-foreground flex items-center gap-1.5 mt-0.5">
                                <MapPin className="w-3.5 h-3.5" />
                                {profile.location}
                              </p>
                            ) : null}
                          </div>
                        </div>

                        {/* Divider */}
                        <div className="border-t border-border" />

                        {/* Bio Section */}
                        <div className="space-y-2">
                          <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            About
                          </label>
                          {isEditing ? (
                            <Textarea
                              value={editedProfile.bio}
                              onChange={(e) => setEditedProfile({ ...editedProfile, bio: e.target.value })}
                              placeholder="Tell us about yourself..."
                              className="resize-none text-sm min-h-[80px]"
                              rows={3}
                            />
                          ) : (
                            <p className="text-sm text-foreground/80 leading-relaxed">
                              {profile.bio || <span className="text-muted-foreground">No bio yet</span>}
                            </p>
                          )}
                        </div>

                        {/* Interests Section */}
                        <div className="space-y-2">
                          <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Interests
                          </label>
                          <div className="flex flex-wrap gap-1.5">
                            {editedProfile.hobbies.length > 0 ? (
                              editedProfile.hobbies.map((hobby, idx) => (
                                <Badge
                                  key={idx}
                                  variant="secondary"
                                  className={cn(
                                    "text-xs px-2.5 py-1 rounded-md font-normal",
                                    isEditing && "pr-1.5"
                                  )}
                                >
                                  {hobby}
                                  {isEditing && (
                                    <button onClick={() => removeHobby(hobby)} className="ml-1.5 hover:text-destructive">
                                      <X className="w-3 h-3" />
                                    </button>
                                  )}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-sm text-muted-foreground">No interests yet</span>
                            )}
                          </div>
                          {isEditing && (
                            <div className="flex gap-2 mt-2">
                              <Input
                                value={newHobby}
                                onChange={(e) => setNewHobby(e.target.value)}
                                placeholder="Add interest..."
                                className="flex-1 text-sm h-9"
                                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addHobby())}
                              />
                              <Button size="sm" variant="outline" onClick={addHobby} className="h-9 px-3">
                                <Plus className="w-4 h-4" />
                              </Button>
                            </div>
                          )}
                        </div>

                        {/* Theme Section */}
                        <div className="space-y-2">
                          <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Theme
                          </label>
                          <div className="flex gap-1 p-1 bg-muted/50 rounded-lg">
                            <ThemeButton 
                              active={theme === "light"} 
                              onClick={() => setTheme("light")}
                              icon={<Sun className="w-4 h-4" />}
                              label="Light"
                            />
                            <ThemeButton 
                              active={theme === "dark"} 
                              onClick={() => setTheme("dark")}
                              icon={<Moon className="w-4 h-4" />}
                              label="Dark"
                            />
                            <ThemeButton 
                              active={theme === "black"} 
                              onClick={() => setTheme("black")}
                              icon={<Monitor className="w-4 h-4" />}
                              label="Black"
                            />
                          </div>
                        </div>

                        {/* Sign Out */}
                        <div className="pt-3 border-t border-border">
                          <Button
                            variant="ghost"
                            className="w-full h-10 text-muted-foreground hover:text-foreground"
                            onClick={handleLogout}
                          >
                            <LogOut className="w-4 h-4 mr-2" />
                            Sign Out
                          </Button>
                        </div>
                      </motion.div>
                    )}

                    {/* API Tab */}
                    {activeTab === "api" && (
                      <motion.div
                        key="api"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="p-5 space-y-5 max-h-[500px] overflow-y-auto"
                      >
                        {loadingKeys ? (
                          <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                          </div>
                        ) : (
                          <>
                            {/* Warning Banner for Low/Critical Usage */}
                            {usageData?.warning_level && (
                              <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={cn(
                                  "flex items-center gap-2 p-3 rounded-lg text-xs",
                                  usageData.warning_level === "critical"
                                    ? "bg-destructive/10 border border-destructive/20 text-destructive"
                                    : "bg-yellow-500/10 border border-yellow-500/20 text-yellow-600 dark:text-yellow-400"
                                )}
                              >
                                <AlertTriangle className="w-4 h-4 shrink-0" />
                                <div className="flex-1">
                                  <span className="font-medium">
                                    {usageData.warning_level === "critical" 
                                      ? "⚠️ Only 2 free requests left!" 
                                      : "📊 Running low on free requests"}
                                  </span>
                                  <span className="ml-1 opacity-80">
                                    Add an API key to avoid interruptions.
                                  </span>
                                </div>
                              </motion.div>
                            )}

                            {/* Usage Stats Card */}
                            <div className="rounded-xl bg-gradient-to-br from-primary/5 via-primary/3 to-transparent border border-primary/10 p-4">
                              <div className="flex items-center gap-3 mb-3">
                                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                                  <Sparkles className="w-5 h-5 text-primary" />
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center justify-between">
                                    <h3 className="font-semibold text-sm">
                                      {usageData?.current_key_source === "user" 
                                        ? "Using Personal Key" 
                                        : "Free Usage"}
                                    </h3>
                                    <div className="flex items-center gap-2">
                                      {usageData?.total_requests_today !== undefined && usageData.total_requests_today > 0 && (
                                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                                          <Activity className="w-3 h-3" />
                                          {usageData.total_requests_today} today
                                        </span>
                                      )}
                                      {usageData?.total_keys_count !== undefined && (
                                        <span className="text-xs text-muted-foreground">
                                          {usageData.total_keys_count}/{usageData.max_keys_allowed || 5} keys
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    {usageData?.current_key_source === "user" 
                                      ? usageData?.active_key_label 
                                        ? `Active: ${usageData.active_key_label}` 
                                        : "Using your own API key"
                                      : `${usageData?.free_requests_used || 0}/${usageData?.free_limit || 10} requests used`
                                    }
                                  </p>
                                </div>
                              </div>
                              
                              {/* Show progress bar only when using free tier */}
                              {usageData?.current_key_source !== "user" && (
                                <>
                                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden mb-2">
                                    <motion.div
                                      initial={{ width: 0 }}
                                      animate={{ 
                                        width: `${((usageData?.free_requests_used || 0) / (usageData?.free_limit || 10)) * 100}%` 
                                      }}
                                      transition={{ duration: 0.5, ease: "easeOut" }}
                                      className={cn(
                                        "h-full rounded-full transition-colors",
                                        (usageData?.free_requests_used || 0) >= (usageData?.free_limit || 10) 
                                          ? "bg-destructive" 
                                          : (usageData?.free_requests_used || 0) >= ((usageData?.free_limit || 10) * 0.8)
                                            ? "bg-yellow-500"
                                            : "bg-primary"
                                      )}
                                    />
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    {(usageData?.free_requests_used || 0) >= (usageData?.free_limit || 20) 
                                      ? "Add your own API key to continue using AI features"
                                      : `${usageData?.free_requests_remaining ?? ((usageData?.free_limit || 10) - (usageData?.free_requests_used || 0))} requests remaining`
                                    }
                                  </p>
                                </>
                              )}

                              {/* Key Status Summary + Countdown Timer */}
                              {usageData && (usageData.total_keys_count > 0 || countdownTime) && (
                                <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
                                  <div className="flex items-center gap-3">
                                    {usageData.total_keys_count > 0 && (
                                      <>
                                        <div className="flex items-center gap-1.5">
                                          <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                          <span className="text-xs text-muted-foreground">
                                            {usageData.active_keys_count || 0} active
                                          </span>
                                        </div>
                                        {usageData.exhausted_keys_count > 0 && (
                                          <div className="flex items-center gap-1.5">
                                            <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                                            <span className="text-xs text-muted-foreground">
                                              {usageData.exhausted_keys_count} exhausted
                                            </span>
                                          </div>
                                        )}
                                      </>
                                    )}
                                  </div>
                                  {/* Countdown Timer */}
                                  {countdownTime && (usageData.exhausted_keys_count > 0 || usageData.warning_level) && (
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                      <Clock className="w-3 h-3" />
                                      <span>Resets in {countdownTime}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Dashboard Messages */}
                            {dashboardMessages.length > 0 && (
                              <div className="space-y-2">
                                {dashboardMessages.map((msg, idx) => (
                                  <div 
                                    key={idx}
                                    className={cn(
                                      "flex items-start gap-2 p-3 rounded-lg text-xs",
                                      msg.includes("exhausted") || msg.includes("limited")
                                        ? "bg-yellow-500/10 border border-yellow-500/20 text-yellow-600 dark:text-yellow-400"
                                        : msg.includes("error") || msg.includes("invalid")
                                        ? "bg-destructive/10 border border-destructive/20 text-destructive"
                                        : "bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400"
                                    )}
                                  >
                                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                    <span>{msg}</span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* API Keys Section */}
                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                  Your API Keys ({usageData?.total_keys_count || apiKeys.length}/{usageData?.max_keys_allowed || 5})
                                </label>
                                <div className="flex items-center gap-1">
                                  {apiKeys.length > 0 && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 text-xs"
                                      onClick={handleHealthCheckAll}
                                      disabled={isHealthChecking}
                                      title="Check all keys are valid"
                                    >
                                      {isHealthChecking ? (
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                      ) : (
                                        <Shield className="w-3 h-3" />
                                      )}
                                    </Button>
                                  )}
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-7 text-xs"
                                    onClick={() => setShowAddKeyForm(!showAddKeyForm)}
                                    disabled={(usageData?.total_keys_count || apiKeys.length) >= (usageData?.max_keys_allowed || 5)}
                                    title={(usageData?.total_keys_count || apiKeys.length) >= (usageData?.max_keys_allowed || 5) 
                                      ? "Maximum keys reached. Delete a key to add more." 
                                      : "Add a new API key"}
                                  >
                                    <Plus className="w-3 h-3 mr-1" />
                                    Add Key
                                  </Button>
                                </div>
                              </div>

                              {/* Add Key Form */}
                              <AnimatePresence>
                                {showAddKeyForm && (
                                  <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="overflow-hidden"
                                  >
                                    <div className="space-y-3 p-4 rounded-xl bg-muted/30 border border-border">
                                      {/* Instructions */}
                                      <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                        <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                                        <div className="text-xs text-muted-foreground">
                                          <p className="font-medium text-blue-500 mb-1">How to get a Groq API key:</p>
                                          <ol className="list-decimal list-inside space-y-0.5">
                                            <li>Visit <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-0.5">console.groq.com <ExternalLink className="w-3 h-3" /></a></li>
                                            <li>Sign up or log in to your account</li>
                                            <li>Create a new API key</li>
                                            <li>Copy and paste it below</li>
                                          </ol>
                                        </div>
                                      </div>

                                      <div className="space-y-2">
                                        <Input
                                          placeholder="Label (optional, e.g., 'Work Key')"
                                          value={newKeyLabel}
                                          onChange={(e) => setNewKeyLabel(e.target.value)}
                                          className="h-9 text-sm"
                                        />
                                        <div className="relative">
                                          <Input
                                            type={showNewKey ? "text" : "password"}
                                            placeholder="gsk_xxxxxxxxxxxx"
                                            value={newApiKey}
                                            onChange={(e) => setNewApiKey(e.target.value)}
                                            className="h-9 text-sm font-mono pr-10"
                                          />
                                          <button
                                            type="button"
                                            onClick={() => setShowNewKey(!showNewKey)}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                          >
                                            {showNewKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                          </button>
                                        </div>
                                      </div>

                                      <div className="flex gap-2">
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          className="flex-1"
                                          onClick={() => {
                                            setShowAddKeyForm(false);
                                            setNewApiKey("");
                                            setNewKeyLabel("");
                                          }}
                                        >
                                          Cancel
                                        </Button>
                                        <Button
                                          size="sm"
                                          className="flex-1"
                                          onClick={handleAddKey}
                                          disabled={isValidatingKey || isAddingKey || !newApiKey.trim()}
                                        >
                                          {isValidatingKey ? (
                                            <>
                                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                              Validating...
                                            </>
                                          ) : isAddingKey ? (
                                            <>
                                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                              Adding...
                                            </>
                                          ) : (
                                            <>
                                              <Zap className="w-3 h-3 mr-1" />
                                              Add Key
                                            </>
                                          )}
                                        </Button>
                                      </div>
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>

                              {/* Keys List */}
                              {apiKeys.length === 0 ? (
                                <div className="text-center py-6 px-4 rounded-xl bg-muted/30 border border-dashed border-border">
                                  <Key className="w-8 h-8 mx-auto mb-2 text-muted-foreground/50" />
                                  <p className="text-sm text-muted-foreground">No API keys added yet</p>
                                  <p className="text-xs text-muted-foreground/70 mt-1">
                                    Add your own Groq API key for unlimited usage
                                  </p>
                                </div>
                              ) : (
                                <div className="space-y-2">
                                  {apiKeys.map((key, index) => (
                                    <motion.div
                                      key={key.id}
                                      initial={{ opacity: 0, y: 5 }}
                                      animate={{ opacity: 1, y: 0 }}
                                      layout
                                      className={cn(
                                        "flex items-center gap-2 p-3 rounded-lg border transition-colors",
                                        !key.is_valid
                                          ? "bg-destructive/5 border-destructive/20"
                                          : key.is_exhausted_today
                                            ? "bg-yellow-500/5 border-yellow-500/20"
                                            : key.is_active 
                                              ? "bg-primary/5 border-primary/20" 
                                              : "bg-muted/30 border-border"
                                      )}
                                    >
                                      {/* Priority Controls */}
                                      {apiKeys.length > 1 && (
                                        <div className="flex flex-col gap-0.5">
                                          <button
                                            onClick={() => handleMoveKeyUp(index)}
                                            disabled={index === 0}
                                            className={cn(
                                              "p-0.5 rounded hover:bg-muted transition-colors",
                                              index === 0 ? "opacity-30 cursor-not-allowed" : "cursor-pointer"
                                            )}
                                            title="Move up (higher priority)"
                                          >
                                            <ChevronUp className="w-3 h-3" />
                                          </button>
                                          <span className="text-[10px] text-center text-muted-foreground">{index + 1}</span>
                                          <button
                                            onClick={() => handleMoveKeyDown(index)}
                                            disabled={index === apiKeys.length - 1}
                                            className={cn(
                                              "p-0.5 rounded hover:bg-muted transition-colors",
                                              index === apiKeys.length - 1 ? "opacity-30 cursor-not-allowed" : "cursor-pointer"
                                            )}
                                            title="Move down (lower priority)"
                                          >
                                            <ChevronDown className="w-3 h-3" />
                                          </button>
                                        </div>
                                      )}

                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span className="text-sm font-medium truncate">
                                            {key.label || "Groq API Key"}
                                          </span>
                                          {key.is_active && !key.is_exhausted_today && key.is_valid && (
                                            <Badge variant="default" className="text-[10px] h-4 px-1.5 bg-primary/20 text-primary hover:bg-primary/20">
                                              Active
                                            </Badge>
                                          )}
                                          {!key.is_valid && (
                                            <Badge variant="destructive" className="text-[10px] h-4 px-1.5">
                                              Invalid
                                            </Badge>
                                          )}
                                          {key.is_exhausted_today && key.is_valid && (
                                            <Badge variant="outline" className="text-[10px] h-4 px-1.5 border-yellow-500/30 text-yellow-600 dark:text-yellow-400">
                                              Exhausted
                                            </Badge>
                                          )}
                                        </div>
                                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                                          <p className="text-xs text-muted-foreground font-mono">
                                            {key.masked_key}
                                          </p>
                                          {key.requests_today > 0 && (
                                            <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                                              <Activity className="w-2.5 h-2.5" />
                                              {key.requests_today} today
                                            </span>
                                          )}
                                          {key.is_exhausted_today && countdownTime && (
                                            <span className="text-[10px] text-yellow-600 dark:text-yellow-400 flex items-center gap-0.5">
                                              <Clock className="w-2.5 h-2.5" />
                                              {countdownTime}
                                            </span>
                                          )}
                                        </div>
                                      </div>

                                      {/* Action Buttons */}
                                      <div className="flex items-center gap-0.5">
                                        {/* Copy masked key */}
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                          onClick={() => handleCopyKey(key.masked_key)}
                                          title="Copy masked key"
                                        >
                                          <Copy className="w-3.5 h-3.5" />
                                        </Button>

                                        {/* Health check single key */}
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                          onClick={() => handleHealthCheck(key.id)}
                                          disabled={healthCheckingKeyId === key.id}
                                          title="Check if key is valid"
                                        >
                                          {healthCheckingKeyId === key.id ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                          ) : (
                                            <RefreshCw className="w-3.5 h-3.5" />
                                          )}
                                        </Button>

                                        {/* Activate key */}
                                        {!key.is_active && !key.is_exhausted_today && key.is_valid && (
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-muted-foreground hover:text-primary"
                                            onClick={() => handleActivateKey(key.id)}
                                            title="Activate this key"
                                          >
                                            <Check className="w-3.5 h-3.5" />
                                          </Button>
                                        )}

                                        {/* Delete key */}
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                          onClick={() => handleDeleteKey(key.id)}
                                          title="Delete this key"
                                        >
                                          <Trash2 className="w-3.5 h-3.5" />
                                        </Button>
                                      </div>
                                    </motion.div>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Info Note */}
                            <div className="text-xs text-center text-muted-foreground pt-2">
                              Your API keys are encrypted and stored securely 🔐
                            </div>
                          </>
                        )}
                      </motion.div>
                    )}

                    {/* Settings Tab */}
                    {activeTab === "settings" && (
                      <motion.div
                        key="settings"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="p-5 space-y-5"
                      >
                        {/* Preferences */}
                        <div className="space-y-3">
                          <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Preferences
                          </label>
                          
                          <div className="space-y-2">
                            <div className="flex items-center justify-between py-2">
                              <div>
                                <p className="text-sm font-medium">Notifications</p>
                                <p className="text-xs text-muted-foreground">Email updates</p>
                              </div>
                              <div className="w-9 h-5 bg-primary rounded-full relative cursor-pointer">
                                <div className="w-4 h-4 bg-white rounded-full absolute right-0.5 top-0.5" />
                              </div>
                            </div>
                            
                            <div className="flex items-center justify-between py-2">
                              <div>
                                <p className="text-sm font-medium">Sounds</p>
                                <p className="text-xs text-muted-foreground">Play effects</p>
                              </div>
                              <div className="w-9 h-5 bg-muted rounded-full relative cursor-pointer">
                                <div className="w-4 h-4 bg-white rounded-full absolute left-0.5 top-0.5 shadow-sm" />
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Danger Zone */}
                        <div className="space-y-3 pt-4 border-t border-border">
                          <label className="text-xs font-medium uppercase tracking-wide text-destructive">
                            Danger Zone
                          </label>
                          
                          <Button
                            variant="outline"
                            className="w-full justify-start text-destructive border-destructive/30 hover:bg-destructive/10"
                            onClick={() => setShowDeleteDialog(true)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete Account
                          </Button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={(open) => {
        if (!isDeleting) {
          setShowDeleteDialog(open);
          if (!open) setDeleteConfirmText("");
        }
      }}>
        <AlertDialogContent className="w-[95vw] sm:w-full max-w-[440px] rounded-2xl border-destructive/30">
          <AlertDialogHeader>
            <div className="flex items-center justify-center mb-2">
              <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-destructive" />
              </div>
            </div>
            <AlertDialogTitle className="text-center text-lg">
              Delete Your Account?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p className="text-sm text-center text-muted-foreground">
                  This action is <span className="text-foreground font-medium">permanent</span> and <span className="text-foreground font-medium">cannot be undone</span>.
                </p>
                
                <div className="bg-destructive/5 border border-destructive/20 rounded-xl p-4 space-y-2">
                  <p className="text-xs font-semibold text-destructive flex items-center gap-1.5">
                    <Trash2 className="w-3.5 h-3.5" />
                    Everything will be permanently deleted:
                  </p>
                  <ul className="text-xs text-muted-foreground space-y-1 pl-5">
                    <li className="flex items-center gap-2">• Your profile, settings & preferences</li>
                    <li className="flex items-center gap-2">• All chat sessions & conversations</li>
                    <li className="flex items-center gap-2">• All AI memories & learnings about you</li>
                    <li className="flex items-center gap-2">• Tasks, mini agents & workflows</li>
                    <li className="flex items-center gap-2">• Highlights, mood history & shared links</li>
                    <li className="flex items-center gap-2">• All data from MongoDB, Pinecone & Neo4j</li>
                  </ul>
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs font-medium text-foreground block">
                    Type <code className="bg-destructive/10 text-destructive px-1.5 py-0.5 rounded font-mono text-[11px]">DELETE_MY_ACCOUNT</code> to confirm:
                  </label>
                  <Input
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value.toUpperCase())}
                    placeholder="Type here..."
                    className="font-mono text-sm text-center border-destructive/30 focus:border-destructive focus:ring-destructive/20"
                    disabled={isDeleting}
                    autoComplete="off"
                    spellCheck={false}
                  />
                  {deleteConfirmText && deleteConfirmText !== "DELETE_MY_ACCOUNT" && (
                    <p className="text-[10px] text-destructive text-center">Keep typing: DELETE_MY_ACCOUNT</p>
                  )}
                  {deleteConfirmText === "DELETE_MY_ACCOUNT" && (
                    <p className="text-[10px] text-green-500 text-center flex items-center justify-center gap-1">
                      <Check className="w-3 h-3" /> Confirmed - Click delete to proceed
                    </p>
                  )}
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2 sm:gap-2">
            <AlertDialogCancel 
              onClick={() => setDeleteConfirmText("")} 
              className="rounded-xl flex-1"
              disabled={isDeleting}
            >
              Keep My Account
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteAccount}
              disabled={deleteConfirmText !== "DELETE_MY_ACCOUNT" || isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-xl flex-1 disabled:opacity-50"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Forever
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default UserProfileModal;
