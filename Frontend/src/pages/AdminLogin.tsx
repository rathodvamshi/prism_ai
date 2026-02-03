
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const AdminLogin = () => {
    const navigate = useNavigate();
    const { login, verifyOTP, isLoading } = useAuthStore();

    const [step, setStep] = useState<'login' | 'otp'>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [otp, setOtp] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        const res: any = await login(email, password);

        if (res.success && res.requiresOTP && res.isAdminFlow) {
            setStep('otp');
            toast.info("Admin verification required. Check your email/logs for OTP.");
        } else if (res.success) {
            toast.error("Not an admin account or flow failed.");
        } else {
            toast.error(res.error || "Login failed");
        }
    };

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        const res = await verifyOTP(email, otp);

        if (res.success && res.isAdmin) {
            toast.success("Welcome back, Super Admin.");
            navigate('/admin');
        } else {
            toast.error(res.error || "Verification failed");
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-zinc-950 p-4 relative overflow-hidden">
            {/* Background Effects */}
            <div className="absolute top-0 left-0 w-full h-full opacity-20 pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600 rounded-full blur-[120px]" />
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600 rounded-full blur-[120px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md relative z-10"
            >
                <Card className="border-white/10 bg-black/50 backdrop-blur-xl shadow-2xl">
                    <CardHeader className="text-center space-y-4 pb-2">
                        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                            <ShieldCheck className="w-8 h-8 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                                Admin Portal
                            </CardTitle>
                            <CardDescription className="text-zinc-400 mt-2">
                                Comprehensive System Control
                            </CardDescription>
                        </div>
                    </CardHeader>

                    <CardContent className="pt-6">
                        {step === 'login' ? (
                            <form onSubmit={handleLogin} className="space-y-4">
                                <div className="space-y-2">
                                    <Input
                                        type="email"
                                        placeholder="Admin Email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="bg-black/40 border-white/10 text-white placeholder:text-zinc-600 h-12"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Input
                                        type="password"
                                        placeholder="Secure Password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="bg-black/40 border-white/10 text-white placeholder:text-zinc-600 h-12"
                                    />
                                </div>
                                <Button
                                    type="submit"
                                    disabled={isLoading}
                                    className="w-full h-12 bg-white text-black hover:bg-zinc-200 font-medium text-lg transition-all"
                                >
                                    {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Authenticate"}
                                </Button>
                            </form>
                        ) : (
                            <form onSubmit={handleVerify} className="space-y-6">
                                <div className="text-center space-y-2">
                                    <p className="text-zinc-400 text-sm">
                                        Enter the 6-digit code sent to your secure channel.
                                    </p>
                                </div>
                                <div className="flex justify-center">
                                    <Input
                                        type="text"
                                        maxLength={6}
                                        value={otp}
                                        onChange={(e) => setOtp(e.target.value)}
                                        className="bg-black/40 border-white/10 text-white text-center text-3xl tracking-[1em] h-16 font-mono w-full"
                                        placeholder="••••••"
                                    />
                                </div>
                                <Button
                                    type="submit"
                                    disabled={isLoading}
                                    className="w-full h-12 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-medium text-lg shadow-lg shadow-purple-500/20 transition-all"
                                >
                                    {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Verify & Enter"}
                                </Button>
                                <div className="text-center">
                                    <button
                                        type="button"
                                        onClick={() => setStep('login')}
                                        className="text-xs text-zinc-500 hover:text-white transition-colors"
                                    >
                                        Cancel verification
                                    </button>
                                </div>
                            </form>
                        )}
                    </CardContent>
                </Card>

                <div className="mt-8 text-center">
                    <p className="text-zinc-600 text-xs flex items-center justify-center gap-2">
                        <Lock className="w-3 h-3" />
                        Secured by PRISM Sentinel
                    </p>
                </div>
            </motion.div>
        </div>
    );
};

export default AdminLogin;
