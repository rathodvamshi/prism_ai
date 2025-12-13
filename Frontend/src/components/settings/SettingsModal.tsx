import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useThemeStore } from "@/stores/themeStore";
import { useProfileStore } from "@/stores/profileStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  User,
  Key,
  CreditCard,
  Download,
  Globe,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Camera,
  Save,
  Wand2,
  Keyboard,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";


interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: string;
}

export const SettingsModal = ({ open, onOpenChange, defaultTab = "general" }: SettingsModalProps) => {
  const { toast } = useToast();
  const { theme, setTheme } = useThemeStore();
  const { profile, updateProfile, setAvatarUrl: setProfileAvatar } = useProfileStore();
  
  const [tab, setTab] = useState<string>(defaultTab);
  const tabsRef = useRef<HTMLDivElement>(null);
  const [apiKey, setApiKey] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [name, setName] = useState("User");
  const [tone, setTone] = useState("balanced");
  const [language, setLanguage] = useState("en");
  const [isDark, setIsDark] = useState(false);
  const [email, setEmail] = useState("user@example.com");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setIsDark(theme === "dark");
  }, [theme]);

  useEffect(() => {
    setName(profile.name || "User");
    setEmail(profile.email || "user@example.com");
    setBio(profile.bio);
    setAvatarUrl(profile.avatarUrl || null);
  }, [profile]);

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = reader.result as string;
      setAvatarUrl(url);
      setProfileAvatar(url);
    };
    reader.readAsDataURL(file);
  };

  const handleProfileSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    updateProfile({
      name,
      email,
      bio,
      avatarUrl,
    });
    toast({ title: "Profile Updated", description: "Your changes have been saved." });
  };

  useEffect(() => {
    // preload existing profile from store
    setName(profile.name);
    setEmail(profile.email);
    setBio(profile.bio);
    setAvatarUrl(profile.avatarUrl);
  }, [profile]);

  const handleVerifyApiKey = async () => {
    setIsVerifying(true);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsVerifying(false);
    setIsVerified(true);
    toast({
      title: "API Key Verified!",
      description: "Unlimited mode enabled. Premium models unlocked.",
    });
  };

  const handleExport = () => {
    toast({
      title: "Export Started",
      description: "Your data will be downloaded shortly.",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[92vw] max-w-xl sm:max-w-2xl max-h-[85vh] overflow-y-auto overflow-x-hidden no-scrollbar">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl font-bold">Settings</DialogTitle>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab} className="mt-4">
          <div className="relative sm:static">
            <TabsList
              ref={tabsRef}
              className="w-full flex overflow-x-auto no-scrollbar gap-2 p-1 -mx-1 snap-x snap-mandatory scroll-smooth sm:grid sm:grid-cols-5 sm:gap-1 sm:p-0 sm:mx-0"
            >
            <TabsTrigger value="general" className="text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
              <User className="w-3.5 h-3.5 mr-1" />
              General
            </TabsTrigger>
            <TabsTrigger value="api" className="text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
              <Key className="w-3.5 h-3.5 mr-1" />
              API
            </TabsTrigger>
            <TabsTrigger value="subscription" className="text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
              <CreditCard className="w-3.5 h-3.5 mr-1" />
              Plan
            </TabsTrigger>
            <TabsTrigger value="export" className="text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
              <Download className="w-3.5 h-3.5 mr-1" />
              Export
            </TabsTrigger>
            <TabsTrigger value="language" className="text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
              <Globe className="w-3.5 h-3.5 mr-1" />
              Language
            </TabsTrigger>
            </TabsList>
            {/* Edge fades for mobile */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-6 bg-gradient-to-r from-card to-transparent sm:hidden" />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-card to-transparent sm:hidden" />
            {/* Mobile arrow nudges */}
            <div className="absolute -right-1 -top-3 sm:hidden flex gap-1">
              <button
                type="button"
                aria-label="Previous"
                className="rounded-md bg-secondary text-foreground/70 px-2 py-1 text-xs border border-border"
                onClick={() => { const n = tabsRef.current; if (!n) return; n.scrollBy({ left: -120, behavior: 'smooth' }); }}
              >◀</button>
              <button
                type="button"
                aria-label="Next"
                className="rounded-md bg-secondary text-foreground/70 px-2 py-1 text-xs border border-border"
                onClick={() => { const n = tabsRef.current; if (!n) return; n.scrollBy({ left: 120, behavior: 'smooth' }); }}
              >▶</button>
            </div>
          </div>

          <TabsContent value="general" className="space-y-6 mt-4">
            {/* Profile Section */}
            <div className="p-4 sm:p-5 bg-secondary/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  <h4 className="font-medium text-sm">Profile</h4>
                </div>
                <Button onClick={handleProfileSave} disabled={saving} className="gap-1" size="sm">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-start">
                {/* Avatar uploader */}
                <div className="flex flex-col items-center gap-2">
                  <div className="relative w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden bg-secondary prism-glow animate-scale-in">
                    {avatarUrl ? (
                      <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                        <User className="w-10 h-10" />
                      </div>
                    )}
                    <label className="absolute bottom-1 right-1 inline-flex items-center justify-center bg-background/80 backdrop-blur-md border border-border rounded-full p-1 cursor-pointer shadow-soft hover:shadow-glow transition">
                      <Camera className="w-4 h-4" />
                      <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground">Upload a square image</p>
                </div>
                {/* Editable fields */}
                <div className="sm:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Name</Label>
                    <Input className="input-responsive" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input className="input-responsive" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label>Bio</Label>
                    <Input className="input-responsive" value={bio} onChange={(e) => setBio(e.target.value)} placeholder="Tell us about you" />
                  </div>
                </div>
              </div>
            </div>
            {/* Display Name removed as requested */}
            <div className="space-y-2">
              <Label>AI Tone</Label>
              <Select value={tone} onValueChange={setTone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="balanced">Balanced</SelectItem>
                  <SelectItem value="casual">Casual</SelectItem>
                  <SelectItem value="creative">Creative</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* Quick Commands section removed */}
            {/* Theme toggle: Sun/Moon sliding pill */}
            <div className="space-y-2">
              <Label>Theme</Label>
              <div className="relative rounded-full border border-sidebar-border/60 backdrop-blur-sm bg-background/30 h-10 p-1">
                <div className="grid gap-1 grid-cols-2">
                  <button
                    type="button"
                    aria-label="Light mode"
                    onClick={() => { setIsDark(false); setTheme("light"); }}
                    className={"relative z-10 flex items-center justify-center rounded-full h-8 " + (isDark ? "text-muted-foreground" : "text-sidebar-foreground")}
                  >
                    {/* Sun icon */}
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="4" />
                      <path d="M12 2v2" />
                      <path d="M12 20v2" />
                      <path d="m4.93 4.93 1.41 1.41" />
                      <path d="m17.66 17.66 1.41 1.41" />
                      <path d="M2 12h2" />
                      <path d="M20 12h2" />
                      <path d="m6.34 17.66-1.41 1.41" />
                      <path d="m19.07 4.93-1.41 1.41" />
                    </svg>
                    <span className="ml-2 text-xs font-medium">Light</span>
                  </button>
                  <button
                    type="button"
                    aria-label="Dark mode"
                    onClick={() => { setIsDark(true); setTheme("dark"); }}
                    className={"relative z-10 flex items-center justify-center rounded-full h-8 " + (isDark ? "text-sidebar-foreground" : "text-muted-foreground")}
                  >
                    {/* Moon icon */}
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
                    </svg>
                    <span className="ml-2 text-xs font-medium">Dark</span>
                  </button>
                </div>
                <div
                  className={"absolute top-1 h-8 rounded-full bg-sidebar-accent/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.25)] w-[calc(50%-4px)] " + (isDark ? "left-[calc(50%+3px)]" : "left-1")}
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>Voice Mode</Label>
                <p className="text-xs text-muted-foreground">Enable speech input/output</p>
              </div>
              <Switch />
            </div>
          </TabsContent>

          <TabsContent value="api" className="space-y-4 mt-4">
            <div className="p-4 sm:p-5 bg-secondary/50 rounded-xl border border-border">
              <h4 className="font-medium text-sm mb-2">Bring Your Own Key (BYOK)</h4>
              <p className="text-xs text-muted-foreground mb-4">
                Enter your OpenAI API key to unlock premium models and unlimited usage.
              </p>
              <div className="flex gap-2">
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="flex-1 input-responsive"
                />
                <Button
                  onClick={handleVerifyApiKey}
                  disabled={!apiKey || isVerifying}
                >
                  {isVerifying ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isVerified ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    "Verify"
                  )}
                </Button>
              </div>
              <AnimatePresence>
                {isVerified && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 flex items-center gap-2 text-success text-sm"
                  >
                    <CheckCircle className="w-4 h-4" />
                    API Key verified! Premium features enabled.
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </TabsContent>

          <TabsContent value="subscription" className="space-y-4 mt-4">
            <div className="p-4 sm:p-5 bg-secondary/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="font-medium">Free Plan</h4>
                  <p className="text-xs text-muted-foreground">Limited usage per day</p>
                </div>
                <Button>Upgrade</Button>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Messages today</span>
                  <span>5 / 20</span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full w-1/4 bg-primary rounded-full" />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="export" className="space-y-4 mt-4">
            <div className="p-4 sm:p-5 bg-secondary/50 rounded-xl border border-border">
              <h4 className="font-medium text-sm mb-2">Export Your Data</h4>
              <p className="text-xs text-muted-foreground mb-4">
                Download all your chats, memories, and profile data as a ZIP file.
              </p>
              <Button onClick={handleExport}>
                <Download className="w-4 h-4 mr-2" />
                Download ZIP
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="language" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Interface Language</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                  <SelectItem value="fr">Français</SelectItem>
                  <SelectItem value="de">Deutsch</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>AI Response Language</Label>
              <Select defaultValue="auto">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto-detect</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </TabsContent>
        </Tabs>

        {/* Danger Zone */}
        <div className="mt-6 pt-6 border-t border-border">
          <Button variant="destructive" className="w-full">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Delete Account
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
