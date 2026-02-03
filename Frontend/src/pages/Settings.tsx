import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useIsMobile } from "@/hooks/use-mobile";
import { useThemeStore } from "@/stores/themeStore";
import { useProfileStore } from "@/stores/profileStore";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Bell, Brain, Camera, CheckCircle, CreditCard, Download, Globe, Key, Loader2, Lock, Save, Sparkles, User } from "lucide-react";
import { MemoryManager } from "@/components/settings/MemoryManager";

const MobileSettings = () => {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { toast } = useToast();

  // Redirect desktop/tablet to chat (modal remains desktop behavior)
  useEffect(() => {
    if (!isMobile) navigate("/chat", { replace: true });
  }, [isMobile, navigate]);

  // State reused from modal for parity
  const [tab, setTab] = useState<string>("general");
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

  // Initialize tab from query param if present
  useEffect(() => {
    const usp = new URLSearchParams(window.location.search);
    const t = usp.get("tab");
    if (t) setTab(t);
  }, []);

  const { theme, setTheme } = useThemeStore();
  const { profile, updateProfile, setAvatarUrl: setProfileAvatar } = useProfileStore();

  useEffect(() => {
    setIsDark(theme === "dark");
  }, [theme]);

  useEffect(() => {
    setName(profile.name);
    setEmail(profile.email);
    setBio(profile.bio);
    setAvatarUrl(profile.avatarUrl);
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

  const handleVerifyApiKey = async () => {
    setIsVerifying(true);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsVerifying(false);
    setIsVerified(true);
    toast({ title: "API Key Verified!", description: "Unlimited mode enabled. Premium models unlocked." });
  };

  const handleExport = () => {
    toast({ title: "Export Started", description: "Your data will be downloaded shortly." });
  };

  const tabsRef = useRef<HTMLDivElement>(null);

  return (
    <div className="md:hidden flex flex-col min-h-dvh bg-background overflow-x-hidden">
      {/* Header */}
      <div className="relative h-12 px-2 flex items-center border-b border-border bg-card">
        <Button variant="ghost" size="icon-sm" className="absolute left-1" onClick={() => navigate("/chat")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h1 className="w-full text-center text-lg font-bold">Settings</h1>
      </div>

      {/* Options bar */}
      <div className="px-2 py-2 border-b border-border bg-card/80">
        <Tabs value={tab} onValueChange={setTab}>
          <div ref={tabsRef} className="w-full overflow-x-auto no-scrollbar scroll-smooth">
            <TabsList className="h-10 items-center justify-center rounded-md bg-muted text-muted-foreground w-full flex overflow-x-auto no-scrollbar gap-2 p-1 -mx-1 snap-x snap-mandatory scroll-smooth sm:grid sm:grid-cols-8 sm:gap-1 sm:p-0 sm:mx-0">
              <TabsTrigger value="general" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <User className="w-3.5 h-3.5 mr-1" />
                General
              </TabsTrigger>
              <TabsTrigger value="api" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Key className="w-3.5 h-3.5 mr-1" />
                API
              </TabsTrigger>
              <TabsTrigger value="subscription" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <CreditCard className="w-3.5 h-3.5 mr-1" />
                Plan
              </TabsTrigger>
              <TabsTrigger value="memory" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Brain className="w-3.5 h-3.5 mr-1" />
                Memory
              </TabsTrigger>
              <TabsTrigger value="notifications" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Bell className="w-3.5 h-3.5 mr-1" />
                Notifs
              </TabsTrigger>
              <TabsTrigger value="export" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Download className="w-3.5 h-3.5 mr-1" />
                Export
              </TabsTrigger>
              <TabsTrigger value="language" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Globe className="w-3.5 h-3.5 mr-1" />
                Lang
              </TabsTrigger>
              <TabsTrigger value="privacy" className="inline-flex items-center justify-center rounded-sm px-3 py-1.5 font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-xs whitespace-nowrap snap-start data-[state=active]:bg-secondary data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground">
                <Lock className="w-3.5 h-3.5 mr-1" />
                Privacy
              </TabsTrigger>
            </TabsList>
          </div>
        </Tabs>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto">
        <div className="min-h-full grid place-items-center p-4">
          <div className="w-full max-w-md mx-auto">
            <Tabs value={tab} onValueChange={setTab}>
              <TabsContent value="general" className="space-y-6">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
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
                  <div className="grid grid-cols-1 gap-4 items-start">
                    <div className="flex flex-col items-center gap-2">
                      <div className="relative w-24 h-24 rounded-full overflow-hidden bg-secondary">
                        {avatarUrl ? (
                          <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                            <User className="w-10 h-10" />
                          </div>
                        )}
                        <label className="absolute bottom-1 right-1 inline-flex items-center justify-center bg-background/80 backdrop-blur-md border border-border rounded-full p-1 cursor-pointer shadow-soft">
                          <Camera className="w-4 h-4" />
                          <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
                        </label>
                      </div>
                      <p className="text-xs text-muted-foreground">Upload a square image</p>
                    </div>
                    <div className="grid grid-cols-1 gap-3">
                      <div className="space-y-2">
                        <Label>Name</Label>
                        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
                      </div>
                      <div className="space-y-2">
                        <Label>Email</Label>
                        <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
                      </div>
                      <div className="space-y-2">
                        <Label>Bio</Label>
                        <Input value={bio} onChange={(e) => setBio(e.target.value)} placeholder="Tell us about you" />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Theme</Label>
                  <div className="relative rounded-full border border-sidebar-border/60 backdrop-blur-sm bg-background/30 h-10 p-1">
                    <div className="grid gap-1 grid-cols-2">
                      <button type="button" onClick={() => { setIsDark(false); setTheme("light"); }} className={"relative z-10 flex items-center justify-center rounded-full h-8 " + (isDark ? "text-muted-foreground" : "text-sidebar-foreground")}>Light</button>
                      <button type="button" onClick={() => { setIsDark(true); setTheme("dark"); }} className={"relative z-10 flex items-center justify-center rounded-full h-8 " + (isDark ? "text-sidebar-foreground" : "text-muted-foreground")}>Dark</button>
                    </div>
                    <div className={"absolute top-1 h-8 rounded-full bg-sidebar-accent/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.25)] w-[calc(50%-4px)] " + (isDark ? "left-[calc(50%+3px)]" : "left-1")} />
                  </div>
                </div>

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

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Voice Mode</Label>
                    <p className="text-xs text-muted-foreground">Enable speech input/output</p>
                  </div>
                  <Switch />
                </div>
              </TabsContent>

              <TabsContent value="api" className="space-y-4">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
                  <h4 className="font-medium text-sm mb-2">Bring Your Own Key (BYOK)</h4>
                  <p className="text-xs text-muted-foreground mb-4">Enter your Groq API key to unlock unlimited usage. Get your free key at console.groq.com</p>
                  <div className="flex gap-2">
                    <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="gsk_..." className="flex-1" />
                    <Button onClick={handleVerifyApiKey} disabled={!apiKey || isVerifying}>
                      {isVerifying ? <Loader2 className="w-4 h-4 animate-spin" /> : isVerified ? <CheckCircle className="w-4 h-4" /> : "Verify"}
                    </Button>
                  </div>
                  <AnimatePresence>
                    {isVerified && (
                      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mt-3 flex items-center gap-2 text-success text-sm">
                        <CheckCircle className="w-4 h-4" /> API Key verified! Unlimited usage enabled.
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </TabsContent>

              <TabsContent value="subscription" className="space-y-4">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
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

              <TabsContent value="memory" className="space-y-4">
                <MemoryManager />
              </TabsContent>

              <TabsContent value="notifications" className="space-y-4">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
                  <h4 className="font-medium text-sm mb-2">Notifications</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Message notifications</span>
                      <Switch />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Weekly summary</span>
                      <Switch />
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="export" className="space-y-4">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
                  <h4 className="font-medium text-sm mb-2">Export Your Data</h4>
                  <p className="text-xs text-muted-foreground mb-4">Download all your chats, memories, and profile data as a ZIP file.</p>
                  <Button onClick={handleExport}><Download className="w-4 h-4 mr-2" /> Download ZIP</Button>
                </div>
              </TabsContent>

              <TabsContent value="language" className="space-y-4">
                <div className="space-y-2">
                  <Label>Interface Language</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
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
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto-detect</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Español</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </TabsContent>

              <TabsContent value="privacy" className="space-y-4">
                <div className="p-4 bg-secondary/50 rounded-xl border border-border">
                  <h4 className="font-medium text-sm mb-2">Privacy</h4>
                  <p className="text-xs text-muted-foreground mb-4">Control what data is stored and how it is used.</p>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Store chat history</span>
                      <Switch />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Personalization</span>
                      <Switch />
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <div className="mt-6">
              <Button variant="destructive" className="w-full">Delete Account</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MobileSettings;
