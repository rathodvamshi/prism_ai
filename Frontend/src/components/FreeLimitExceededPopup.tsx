/**
 * 🔒 FREE LIMIT EXCEEDED / ALL KEYS EXHAUSTED POPUP
 * 
 * Shows when:
 * 1. User has used all their free requests (FREE_LIMIT_EXCEEDED)
 * 2. All user's API keys are exhausted for today (ALL_KEYS_EXHAUSTED)
 * 
 * Prompts them to add their own API key or wait until tomorrow
 */

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { apiKeysAPI } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ExternalLink,
  Eye,
  EyeOff,
  Loader2,
  Zap,
  Info,
  X,
  CheckCircle,
  XCircle,
  Check,
  Terminal,
  ShieldCheck,
  CreditCard,
  ArrowRight
} from "lucide-react";
import { cn } from "@/lib/utils";

type ExceededType = "free_limit" | "all_keys_exhausted";

interface FreeLimitExceededPopupProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onKeyAdded?: () => void;
  exceededType?: ExceededType;
}

export const FreeLimitExceededPopup = ({
  open,
  onOpenChange,
  onKeyAdded,
  exceededType = "free_limit"
}: FreeLimitExceededPopupProps) => {
  const { toast } = useToast();
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState<"idle" | "testing" | "valid" | "invalid" | "saving" | "success">("idle");
  const [statusMessage, setStatusMessage] = useState("");

  const [keysCount, setKeysCount] = useState<{ total: number; max: number } | null>(null);
  const [activeTab, setActiveTab] = useState("own_api");
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("yearly");

  // Check how many keys user has
  useEffect(() => {
    if (open) {
      apiKeysAPI.getDashboard().then((res) => {
        if (!res.error && res.data?.usage) {
          setKeysCount({
            total: res.data.usage.total_keys_count || 0,
            max: res.data.usage.max_keys_allowed || 5
          });
        }
      });
    }
  }, [open]);

  // Reset status when key changes
  useEffect(() => {
    if (status !== "saving" && status !== "success") {
      setStatus("idle");
      setStatusMessage("");
    }
  }, [apiKey]);

  const isKeysExhausted = exceededType === "all_keys_exhausted";
  const canAddMoreKeys = keysCount ? keysCount.total < keysCount.max : true;

  // Quick test key without adding
  const handleTestKey = async () => {
    if (!apiKey.trim()) return;

    setStatus("testing");
    try {
      const validateRes = await apiKeysAPI.validateKey(apiKey.trim());

      if (validateRes.data?.valid) {
        setStatus("valid");
        setStatusMessage("Valid API Key");
      } else {
        setStatus("invalid");
        setStatusMessage(validateRes.data?.message || "Invalid API Key");
      }
    } catch (error) {
      setStatus("invalid");
      setStatusMessage("Validation Failed");
    }
  };

  const handleAddKey = async () => {
    if (!apiKey.trim()) return;

    if (!canAddMoreKeys) {
      toast({
        title: "Limit Reached",
        description: "Maximum 5 keys allowed. Please remove one to add more.",
        variant: "destructive",
      });
      return;
    }

    setStatus("saving");
    try {
      // Validate first if not already validated
      if (status !== "valid") {
        const validateRes = await apiKeysAPI.validateKey(apiKey.trim());
        if (validateRes.error || !validateRes.data?.valid) {
          setStatus("invalid");
          setStatusMessage("Invalid Key");
          return;
        }
      }

      const addRes = await apiKeysAPI.addKey(apiKey.trim(), "groq");

      if (addRes.error) {
        setStatus("idle"); // Reset to idle so user can try again
        // Parse specific error types
        const errorMsg = addRes.error.toLowerCase();
        let title = "Failed to Add";
        let description = addRes.error;
        
        if (addRes.status === 409 || errorMsg.includes("duplicate") || errorMsg.includes("already")) {
          title = "Duplicate Key";
          description = "This API key is already saved in your account.";
        } else if (errorMsg.includes("limit") || errorMsg.includes("max")) {
          title = "Limit Reached";
          description = "Maximum 5 keys allowed. Please remove one first.";
        }
        
        toast({
          title,
          description,
          variant: "destructive",
        });
        return;
      }

      setStatus("success");
      setStatusMessage("Saved!");

      // Small delay before closing to show success state
      setTimeout(() => {
        setApiKey("");
        onOpenChange(false);
        onKeyAdded?.();
        setStatus("idle");
      }, 1000);

    } catch (error) {
      setStatus("idle");
      toast({
        title: "Error",
        description: "Something went wrong.",
        variant: "destructive",
      });
    }
  };

  const handleSubscribe = () => {
    toast({
      title: "Coming Soon",
      description: "Subscriptions are coming soon! Stay tuned.",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent hideClose className="w-[95vw] sm:w-[500px] max-w-[500px] max-h-[85vh] sm:max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden bg-background border border-border shadow-2xl sm:rounded-2xl outline-none">
        <DialogTitle className="sr-only">
          {isKeysExhausted ? "All Keys Exhausted" : "Limit Reached"}
        </DialogTitle>


        {/* Close Button */}
        <button
          onClick={() => onOpenChange(false)}
          className="absolute top-4 right-4 z-50 text-muted-foreground/60 hover:text-foreground transition-colors p-2 rounded-full hover:bg-muted/50"
        >
          <X className="w-4 h-4" />
        </button>


        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto">
          <Tabs defaultValue="own_api" value={activeTab} onValueChange={setActiveTab} className="w-full h-full flex flex-col">

            <div className="flex-none px-4 sm:px-6 pt-6">
              <TabsList className="grid w-full grid-cols-2 p-1 bg-muted rounded-xl h-11">
                <TabsTrigger
                  value="own_api"
                  className="rounded-lg text-sm font-medium data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all duration-200"
                >
                  Own API Key
                </TabsTrigger>
                <TabsTrigger
                  value="upgrade"
                  className="rounded-lg text-sm font-medium data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all duration-200"
                >
                  Upgrade Plan
                </TabsTrigger>
              </TabsList>
            </div>

            <div className="flex-1">
              <AnimatePresence mode="wait">
                <TabsContent value="own_api" className="m-0 focus-visible:outline-none">
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    transition={{ duration: 0.2 }}
                    className="p-4 sm:p-6 space-y-6"
                  >

                    <div className="space-y-1 relative">
                      <h2 className="text-lg sm:text-xl font-bold tracking-tight">
                        {isKeysExhausted ? "Daily Limit Exhausted" : "Free Usage Limit Reached"}
                      </h2>
                      <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                        Add your own <span className="font-semibold text-foreground">Groq API key</span> to continue. It's free, secure, and gives you unlimited access.
                      </p>
                    </div>

                    {/* Styled Instructions - Responsive Layout */}
                    <div className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/20 rounded-xl p-3 sm:p-4 space-y-3">
                      <div className="flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 text-xs font-bold shadow-sm mt-0.5">
                          1
                        </div>
                        <div className="text-xs sm:text-sm text-foreground/80">
                          Visit the <a
                            href="https://console.groq.com/keys"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 dark:text-blue-400 font-semibold hover:underline decoration-blue-600/30 underline-offset-4 transition-all ml-0.5 inline-flex items-center gap-0.5"
                          >
                            Groq Console <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 text-xs font-bold shadow-sm mt-0.5">
                          2
                        </div>
                        <div className="text-xs sm:text-sm text-foreground/80">
                          Log in and click <span className="font-semibold text-foreground">"Create API Key"</span>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 text-xs font-bold shadow-sm mt-0.5">
                          3
                        </div>
                        <div className="text-xs sm:text-sm text-foreground/80 break-all sm:break-normal">
                          Copy the key (<code className="bg-background/50 border border-black/5 dark:border-white/10 px-1 py-0.5 rounded text-[10px] font-mono text-muted-foreground whitespace-nowrap">gsk_...</code>) and paste it below
                        </div>
                      </div>
                    </div>

                    {/* Input with embedded functionality */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        {/* Input Container */}
                        <div className="relative group">
                          <div className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-2 text-muted-foreground pointer-events-none transition-colors group-focus-within:text-foreground">
                            <Terminal className="w-4 h-4" />
                          </div>

                          <Input
                            type={showKey ? "text" : "password"}
                            placeholder="gsk_..."
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            disabled={status === "saving" || status === "success"}
                            className={cn(
                              "pl-9 pr-24 font-mono text-xs sm:text-sm bg-background/50 h-10 sm:h-12 transition-all duration-300",
                              "border-input hover:border-primary/40 focus:border-primary focus:ring-4 focus:ring-primary/10",
                              status === "valid" && "border-green-500 hover:border-green-500 focus:border-green-500 focus:ring-green-500/10",
                              status === "invalid" && "border-destructive hover:border-destructive focus:border-destructive focus:ring-destructive/10"
                            )}
                          />

                          {/* Right Side Actions inside Input */}
                          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                            {apiKey && (
                              <button
                                type="button"
                                onClick={() => setShowKey(!showKey)}
                                className="p-1.5 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors mr-1"
                              >
                                {showKey ? <EyeOff className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Eye className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
                              </button>
                            )}

                            <AnimatePresence mode="popLayout">
                              {status === "idle" && apiKey.trim().length > 10 && (
                                <motion.button
                                  initial={{ scale: 0.8, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  exit={{ scale: 0.8, opacity: 0 }}
                                  type="button"
                                  onClick={handleTestKey}
                                  className="bg-primary/10 hover:bg-primary/20 text-primary text-[10px] sm:text-xs font-semibold px-2 sm:px-2.5 py-1 rounded-md transition-colors"
                                >
                                  Verify
                                </motion.button>
                              )}
                              {status === "testing" && (
                                <motion.div
                                  initial={{ scale: 0.8, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  exit={{ scale: 0.8, opacity: 0 }}
                                  className="flex items-center gap-1.5 bg-muted px-2.5 py-1 rounded-md text-[10px] sm:text-xs font-medium text-muted-foreground"
                                >
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                  <span className="hidden sm:inline">Checking...</span>
                                </motion.div>
                              )}
                              {status === "valid" && (
                                <motion.div
                                  initial={{ scale: 0.8, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  exit={{ scale: 0.8, opacity: 0 }}
                                  className="flex items-center gap-1.5 bg-green-500/10 text-green-600 dark:text-green-400 px-2.5 py-1 rounded-md text-[10px] sm:text-xs font-bold"
                                >
                                  <CheckCircle className="w-3.5 h-3.5" />
                                  Valid
                                </motion.div>
                              )}
                              {status === "invalid" && (
                                <motion.div
                                  initial={{ scale: 0.8, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  exit={{ scale: 0.8, opacity: 0 }}
                                  className="flex items-center gap-1.5 bg-destructive/10 text-destructive px-2.5 py-1 rounded-md text-[10px] sm:text-xs font-bold"
                                >
                                  <XCircle className="w-3.5 h-3.5" />
                                  Invalid
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        </div>
                      </div>

                      {/* Main Action Button */}
                      <Button
                        onClick={handleAddKey}
                        disabled={status === "saving" || status === "success" || !apiKey.trim()}
                        className={cn(
                          "w-full h-10 sm:h-11 text-sm sm:text-base font-medium transition-all duration-300 rounded-xl overflow-hidden relative",
                          status === "success" ? "bg-green-600 hover:bg-green-700 text-white" : ""
                        )}
                      >
                        <AnimatePresence mode="wait">
                          {status === "saving" ? (
                            <motion.div
                              key="saving"
                              initial={{ y: 20, opacity: 0 }}
                              animate={{ y: 0, opacity: 1 }}
                              exit={{ y: -20, opacity: 0 }}
                              className="flex items-center gap-2"
                            >
                              <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                              <span>Verifying & Saving...</span>
                            </motion.div>
                          ) : status === "success" ? (
                            <motion.div
                              key="success"
                              initial={{ scale: 0.5, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              className="flex items-center gap-2"
                            >
                              <div className="w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-white/20 flex items-center justify-center">
                                <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-white" />
                              </div>
                              <span>Key Added Successfully!</span>
                            </motion.div>
                          ) : (
                            <motion.div
                              key="idle"
                              initial={{ y: 20, opacity: 0 }}
                              animate={{ y: 0, opacity: 1 }}
                              exit={{ y: -20, opacity: 0 }}
                              className="flex items-center gap-2"
                            >
                              <Zap className="w-4 h-4 fill-current opacity-80" />
                              <span>Save API Key</span>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </Button>

                      <p className="text-center text-[10px] sm:text-xs text-muted-foreground/60">
                        Keys are stored locally and encrypted.
                      </p>
                    </div>

                  </motion.div>
                </TabsContent>

                <TabsContent value="upgrade" className="m-0 focus-visible:outline-none">
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    transition={{ duration: 0.2 }}
                    className="p-4 sm:p-6 space-y-6"
                  >
                    <div className="text-center space-y-4">
                      <div className="space-y-1">
                        <h2 className="text-lg sm:text-xl font-bold">Upgrade to Pro</h2>
                        <p className="text-xs sm:text-sm text-muted-foreground w-[90%] sm:w-4/5 mx-auto">
                          Higher limits, faster responses, and premium models.
                        </p>
                      </div>

                      {/* Custom Toggle */}
                      <div className="inline-flex bg-muted/50 p-1 rounded-full border border-border/50 relative">
                        <div
                          className={cn(
                            "absolute top-1 bottom-1 w-[calc(50%-4px)] rounded-full bg-background shadow-sm transition-all duration-300 ease-spring",
                            billingCycle === "monthly" ? "left-1" : "left-[calc(50%+2px)]"
                          )}
                        />
                        <button
                          onClick={() => setBillingCycle("monthly")}
                          className={cn(
                            "relative z-10 px-4 py-1.5 text-xs font-semibold transition-colors duration-200 w-24 text-center rounded-full",
                            billingCycle === "monthly" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                          )}
                        >
                          Monthly
                        </button>
                        <button
                          onClick={() => setBillingCycle("yearly")}
                          className={cn(
                            "relative z-10 px-4 py-1.5 text-xs font-semibold transition-colors duration-200 w-24 text-center rounded-full flex items-center justify-center gap-1",
                            billingCycle === "yearly" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                          )}
                        >
                          Yearly
                          <span className={cn(
                            "text-[9px] px-1 py-0.5 rounded leading-none transition-colors",
                            billingCycle === "yearly" ? "bg-green-500/10 text-green-600" : "bg-green-500/10 text-green-600/70"
                          )}>-20%</span>
                        </button>
                      </div>
                    </div>

                    {/* Clean Pricing Card */}
                    <div className="border border-border/60 rounded-2xl p-5 sm:p-6 bg-card hover:border-primary/20 transition-all duration-300 shadow-sm relative overflow-hidden group">

                      {/* Card Badge */}
                      <div className="absolute top-4 right-4 animate-in fade-in zoom-in duration-500 delay-100">
                        <div className="bg-primary text-primary-foreground text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-sm">
                          Recommended
                        </div>
                      </div>

                      <div className="mb-6">
                        <h3 className="text-base sm:text-lg font-bold">Pro Plan</h3>
                        <div className="flex items-baseline gap-1 mt-2">
                          <span className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                            {billingCycle === "yearly" ? "$15" : "$19"}
                          </span>
                          <span className="text-xs sm:text-sm font-medium text-muted-foreground">/ month</span>
                        </div>
                        <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
                          {billingCycle === "yearly" ? "Billed $180 yearly" : "Billed monthly"}
                        </p>
                      </div>

                      <ul className="space-y-3 mb-6">
                        {[
                          "Unlimited Messages",
                          "Priority Response Time",
                          "Access to GPT-4 & Opus",
                          "Early Access Features"
                        ].map((item, i) => (
                          <li key={i} className="flex items-center gap-3 text-xs sm:text-sm group/item">
                            <div className="w-5 h-5 rounded-full bg-primary/10 group-hover/item:bg-primary/20 transition-colors flex items-center justify-center shrink-0">
                              <Check className="w-3 h-3 text-primary" />
                            </div>
                            <span className="text-foreground/80 font-medium">{item}</span>
                          </li>
                        ))}
                      </ul>

                      <Button
                        onClick={handleSubscribe}
                        className="w-full h-9 sm:h-10 rounded-lg group-hover:shadow-lg group-hover:shadow-primary/10 transition-all text-sm"
                      >
                        Subscribe Now <ArrowRight className="w-4 h-4 ml-1 opacity-70" />
                      </Button>
                    </div>

                    <div className="flex justify-center pb-2 sm:pb-0">
                      <button className="text-[10px] sm:text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 hover:underline transition-all">
                        <CreditCard className="w-3 h-3" />
                        View Enterprise Plans
                      </button>
                    </div>

                  </motion.div>
                </TabsContent>
              </AnimatePresence>
            </div>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
};
