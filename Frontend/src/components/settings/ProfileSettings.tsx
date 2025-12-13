import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProfileStore } from "@/stores/profileStore";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { LoadingSpinner } from "@/components/chat/LoadingSkeletons";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Save, Loader2, User, Trash2, AlertCircle, CheckCircle2 } from "lucide-react";
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

export const ProfileSettings = () => {
  const { profile, stats, isLoading, isSaving, loadProfileFromBackend, saveProfileToBackend, updateProfile, setAvatarUrl } = useProfileStore();
  const { logout } = useAuthStore();
  const { toast } = useToast();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    name: "",
    bio: "",
    location: "",
    website: "",
  });
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Load profile on mount
  useEffect(() => {
    loadProfileFromBackend();
  }, []);

  // Update form data when profile loads
  useEffect(() => {
    setFormData({
      name: profile.name || "",
      bio: profile.bio || "",
      location: profile.location || "",
      website: profile.website || "",
    });
    setAvatarPreview(profile.avatarUrl || null);
  }, [profile]);

  // Check if form has changes
  useEffect(() => {
    const changed = 
      formData.name !== profile.name ||
      formData.bio !== profile.bio ||
      formData.location !== profile.location ||
      formData.website !== profile.website ||
      avatarPreview !== profile.avatarUrl;
    setHasChanges(changed);
  }, [formData, avatarPreview, profile]);

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Please upload an image smaller than 5MB",
        variant: "destructive",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const url = reader.result as string;
      setAvatarPreview(url);
      setHasChanges(true);
    };
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    try {
      const updates = {
        ...formData,
        avatarUrl: avatarPreview || "",
      };
      
      await saveProfileToBackend(updates);
      
      // Show success animation
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 2000);
      
      toast({
        title: "Profile Updated",
        description: "Your changes have been saved successfully",
      });
      
      setHasChanges(false);
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to save profile changes",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== "DELETE_MY_ACCOUNT") {
      toast({
        title: "Confirmation Required",
        description: "Please type 'DELETE_MY_ACCOUNT' to confirm",
        variant: "destructive",
      });
      return;
    }

    setIsDeleting(true);
    try {
      const token = localStorage.getItem('prism_auth_token');
      const response = await fetch('http://127.0.0.1:8000/users/account', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ confirm_delete: "DELETE_MY_ACCOUNT" }),
      });

      if (!response.ok) throw new Error('Failed to delete account');

      toast({
        title: "Account Deleted",
        description: "Your account and all data have been removed",
      });

      // Logout and redirect
      logout();
      navigate("/");
    } catch (error) {
      toast({
        title: "Deletion Failed",
        description: "Failed to delete account. Please try again.",
        variant: "destructive",
      });
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <LoadingSpinner size="lg" />
          <p className="text-sm text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Profile Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold">Profile Settings</h2>
        <p className="text-sm text-muted-foreground">
          Manage your personal information and preferences
        </p>
      </div>

      {/* Avatar Section */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="p-6 bg-card rounded-xl border border-border"
      >
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="w-24 h-24 rounded-full overflow-hidden bg-secondary border-2 border-border">
              {avatarPreview ? (
                <img src={avatarPreview} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                  <User className="w-12 h-12" />
                </div>
              )}
            </div>
            <label className="absolute bottom-0 right-0 p-2 bg-primary text-primary-foreground rounded-full cursor-pointer hover:bg-primary/90 transition-colors shadow-lg">
              <Camera className="w-4 h-4" />
              <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
            </label>
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-lg">{profile.name || "User"}</h3>
            <p className="text-sm text-muted-foreground">{profile.email}</p>
            {stats.member_since && (
              <p className="text-xs text-muted-foreground mt-1">
                Member since {new Date(stats.member_since).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {/* Profile Form */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="p-6 bg-card rounded-xl border border-border space-y-4"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Personal Information</h3>
          <AnimatePresence>
            {showSuccess && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center gap-2 text-green-600"
              >
                <CheckCircle2 className="w-5 h-5" />
                <span className="text-sm font-medium">Saved!</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Your name"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              placeholder="City, Country"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="website">Website</Label>
          <Input
            id="website"
            type="url"
            value={formData.website}
            onChange={(e) => setFormData({ ...formData, website: e.target.value })}
            placeholder="https://yourwebsite.com"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="bio">Bio</Label>
          <Textarea
            id="bio"
            value={formData.bio}
            onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
            placeholder="Tell us about yourself..."
            rows={4}
          />
        </div>

        <Button
          onClick={handleSave}
          disabled={!hasChanges || isSaving}
          className="w-full"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </>
          )}
        </Button>
      </motion.div>

      {/* Stats Section */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="p-6 bg-card rounded-xl border border-border"
        >
          <h3 className="font-semibold mb-4">Account Statistics</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-secondary/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Total Chats</p>
              <p className="text-2xl font-bold">{stats.total_sessions || 0}</p>
            </div>
            <div className="p-3 bg-secondary/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Total Tasks</p>
              <p className="text-2xl font-bold">{stats.total_tasks || 0}</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Danger Zone */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.3 }}
        className="p-6 bg-destructive/10 rounded-xl border border-destructive/30"
      >
        <div className="flex items-start gap-3 mb-4">
          <AlertCircle className="w-5 h-5 text-destructive mt-0.5" />
          <div>
            <h3 className="font-semibold text-destructive">Danger Zone</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Permanently delete your account and all associated data
            </p>
          </div>
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="w-full">
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Account
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete your account and remove all your data from our servers including:
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>All chat conversations and sessions</li>
                  <li>All tasks and memories</li>
                  <li>Vector and graph database entries</li>
                  <li>Mini-agents and highlights</li>
                </ul>
                <div className="mt-4 space-y-2">
                  <Label>Type <strong>DELETE_MY_ACCOUNT</strong> to confirm:</Label>
                  <Input
                    value={deleteConfirmation}
                    onChange={(e) => setDeleteConfirmation(e.target.value)}
                    placeholder="DELETE_MY_ACCOUNT"
                  />
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setDeleteConfirmation("")}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteAccount}
                disabled={isDeleting || deleteConfirmation !== "DELETE_MY_ACCOUNT"}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  "Delete Account"
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </motion.div>
    </div>
  );
};
