import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Eye, EyeOff, ArrowLeft, Mail, Lock, User, Github, Info } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useAuthStore } from "@/stores/authStore";
import { AccountCreatedAnimation } from "@/components/animations/AccountCreatedAnimation";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type AuthMode = "login" | "signup" | "forgot" | "otp";

const Auth = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { 
    login, 
    signup, 
    verifyOTP, 
    forgotPassword, 
    isLoading: authLoading, 
    error,
    showAccountCreatedAnimation,
    hideAccountAnimation,
    user
  } = useAuthStore();
  
  const [mode, setMode] = useState<AuthMode>(
    (searchParams.get("mode") as AuthMode) || "login"
  );
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);

  useEffect(() => {
    const modeParam = searchParams.get("mode") as AuthMode;
    if (modeParam && ["login", "signup", "forgot", "otp"].includes(modeParam)) {
      setMode(modeParam);
    }
  }, [searchParams]);

  const handleAnimationComplete = () => {
    hideAccountAnimation();
    navigate("/chat");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (mode === "login") {
        const result = await login(email, password);
        
        if (result.success) {
          toast({ title: "Welcome back!", description: "Redirecting to chat..." });
          navigate("/chat");
        } else {
          toast({
            title: "Login Failed", 
            description: result.error || "Login failed",
            variant: "destructive"
          });
        }
      } else if (mode === "signup") {
        const result = await signup(email, password, name);
        
        if (result.success) {
          if ((result as any).requiresOTP) {
            toast({ 
              title: "OTP Sent! 📧", 
              description: "Check your email and terminal for the 6-digit verification code." 
            });
            setMode("otp");
          } else {
            toast({ title: "Account created!", description: "Welcome to PRISM!" });
            navigate("/chat");
          }
        } else {
          toast({
            title: "Signup Failed",
            description: result.error || "Signup failed",
            variant: "destructive"
          });
        }
      } else if (mode === "forgot") {
        const result = await forgotPassword(email);
        
        if (result.success) {
          toast({ title: "Reset link sent!", description: "Check your email inbox." });
        } else {
          toast({
            title: "Error",
            description: result.error || "Failed to send reset email",
            variant: "destructive"
          });
        }
      } else if (mode === "otp") {
        const otpString = otp.join("");
        const result = await verifyOTP(email, otpString);
        
        if (result.success) {
          if (result.accountCreated) {
            // Don't navigate yet, let the animation play first
            toast({ title: "Email verified!", description: "Account created successfully!" });
          } else {
            // Regular login verification
            toast({ title: "Email verified!", description: "Welcome back to PRISM!" });
            navigate("/chat");
          }
        } else {
          toast({
            title: "Verification Failed",
            description: result.error || "Invalid OTP",
            variant: "destructive"
          });
        }
      }
    } catch (error) {
      toast({
        title: "Network Error",
        description: "Unable to connect to server. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      nextInput?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      prevInput?.focus();
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 overflow-hidden relative">
      {/* Animated background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-purple-500/5 pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent pointer-events-none" />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Back Button & Logo */}
        <div className="flex items-center justify-center mb-6 relative">
          <Link
            to="/"
            className="absolute left-0 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-primary hover:text-primary/80 border border-transparent hover:border-primary/20 transition-all duration-200 group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-200" />
            <span className="text-sm font-medium">Back</span>
          </Link>
          
          <Link to="/" className="flex items-center justify-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary via-blue-500 to-purple-500 flex items-center justify-center shadow-soft">
              <Sparkles className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">PRISM</span>
          </Link>
        </div>

        {/* Card */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="bg-card/80 backdrop-blur-xl rounded-2xl border border-border shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-5 sm:p-6"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {/* Header */}
              <div className="text-center mb-5">
                <motion.h1
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-xl sm:text-2xl font-bold text-foreground mb-1.5"
                >
                  {mode === "login" && "Welcome back"}
                  {mode === "signup" && "Create account"}
                  {mode === "forgot" && "Reset password"}
                  {mode === "otp" && "Verify email"}
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="text-muted-foreground text-xs sm:text-sm"
                >
                  {mode === "login" && "Sign in to continue to PRISM"}
                  {mode === "signup" && "Start your journey with PRISM"}
                  {mode === "forgot" && "We'll send you a reset link"}
                  {mode === "otp" && "Enter the code sent to your email"}
                </motion.p>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-3.5">
                {mode === "signup" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="space-y-1"
                  >
                    <Label htmlFor="name" className="text-foreground text-sm">Full Name</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="name"
                        type="text"
                        placeholder="John Doe"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="pl-10 h-10 bg-background/50 border-border/50 focus:border-primary transition-colors text-sm"
                        required
                      />
                    </div>
                  </motion.div>
                )}

                {mode !== "otp" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: mode === "signup" ? 0.2 : 0.1 }}
                    className="space-y-1"
                  >
                    <Label htmlFor="email" className="text-foreground text-sm">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="pl-10 h-10 bg-background/50 border-border/50 focus:border-primary transition-colors text-sm"
                        required
                      />
                    </div>
                  </motion.div>
                )}

                {(mode === "login" || mode === "signup") && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: mode === "signup" ? 0.3 : 0.2 }}
                    className="space-y-1"
                  >
                    <Label htmlFor="password" className="text-foreground text-sm">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10 pr-20 h-10 bg-background/50 border-border/50 focus:border-primary transition-colors text-sm"
                        required
                      />
                      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                        {mode === "signup" && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button type="button" className="text-muted-foreground hover:text-foreground transition-colors">
                                  <Info className="w-3.5 h-3.5" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="left" className="max-w-xs">
                                <p className="text-xs">Password must be at least 8 characters with uppercase, lowercase, number, and special character.</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {mode === "otp" && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 }}
                    className="flex justify-center gap-2 my-4"
                  >
                    {otp.map((digit, index) => (
                      <Input
                        key={index}
                        id={`otp-${index}`}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
                        className="w-9 h-11 sm:w-10 sm:h-12 text-center text-lg font-semibold bg-background/50 border-border/50 focus:border-primary transition-colors"
                      />
                    ))}
                  </motion.div>
                )}

                {mode === "login" && (
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => setMode("forgot")}
                      className="text-sm text-primary hover:text-primary/80 hover:underline transition-colors"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <Button
                    type="submit"
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-xl transition-all duration-200 h-10"
                    size="default"
                    disabled={isLoading || authLoading}
                  >
                    {isLoading ? (
                      <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    ) : (
                      <>
                        {mode === "login" && "Sign In"}
                        {mode === "signup" && "Create Account"}
                        {mode === "forgot" && "Send Reset Link"}
                        {mode === "otp" && "Verify"}
                      </>
                    )}
                  </Button>
                </motion.div>
              </form>

              {/* Social Auth */}
              {(mode === "login" || mode === "signup") && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="mt-4"
                >
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-border/50" />
                    </div>
                    <div className="relative flex justify-center text-xs">
                      <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-3 mt-3">
                    {/* Google */}
                    <button
                      type="button"
                      className="w-10 h-10 rounded-xl bg-background/50 hover:bg-background border border-border/50 hover:border-primary/20 shadow-soft transition-all duration-200 hover:scale-105 hover:shadow-[0_0_12px_rgba(var(--primary),0.3)] flex items-center justify-center group"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                    </button>

                    {/* GitHub */}
                    <button
                      type="button"
                      className="w-10 h-10 rounded-xl bg-background/50 hover:bg-background border border-border/50 hover:border-primary/20 shadow-soft transition-all duration-200 hover:scale-105 hover:shadow-[0_0_12px_rgba(var(--primary),0.3)] flex items-center justify-center group"
                    >
                      <Github className="w-4 h-4 text-foreground" />
                    </button>

                    {/* Discord */}
                    <button
                      type="button"
                      className="w-10 h-10 rounded-xl bg-background/50 hover:bg-background border border-border/50 hover:border-primary/20 shadow-soft transition-all duration-200 hover:scale-105 hover:shadow-[0_0_12px_rgba(var(--primary),0.3)] flex items-center justify-center group"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                      </svg>
                    </button>
                  </div>
                </motion.div>
              )}

              {/* Footer links */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="mt-4 text-center text-xs sm:text-sm"
              >
                {mode === "login" && (
                  <p className="text-muted-foreground">
                    Don't have an account?{" "}
                    <button
                      onClick={() => setMode("signup")}
                      className="text-primary font-medium hover:text-primary/80 hover:underline transition-colors"
                    >
                      Sign up
                    </button>
                  </p>
                )}
                {mode === "signup" && (
                  <p className="text-muted-foreground">
                    Already have an account?{" "}
                    <button
                      onClick={() => setMode("login")}
                      className="text-primary font-medium hover:text-primary/80 hover:underline transition-colors"
                    >
                      Sign in
                    </button>
                  </p>
                )}
                {(mode === "forgot" || mode === "otp") && (
                  <button
                    onClick={() => setMode("login")}
                    className="inline-flex items-center gap-1 text-primary font-medium hover:text-primary/80 hover:underline transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back to login
                  </button>
                )}
              </motion.div>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Bottom Sign up link for login mode - REMOVED */}
      </motion.div>

      {/* Account Creation Animation */}
      <AccountCreatedAnimation
        isVisible={showAccountCreatedAnimation}
        userEmail={user?.email || email}
        userName={user?.name || name || "User"}
        onComplete={handleAnimationComplete}
      />
    </div>
  );
};

export default Auth;
