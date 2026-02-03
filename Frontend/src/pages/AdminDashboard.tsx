
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import {
    Users, Activity, Server, Shield, LogOut,
    Search, Wifi, Cpu, Database, AlertTriangle,
    CheckCircle, Ban, Eye, Key, MessageSquare
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { adminAPI } from '@/lib/api';
import { toast } from 'sonner';

// --- SUB-COMPONENTS ---

const StatCard = ({ title, value, icon: Icon, color, index }: any) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.1 }}
    >
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-zinc-400">
                    {title}
                </CardTitle>
                <Icon className={`h-4 w-4 ${color}`} />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
            </CardContent>
        </Card>
    </motion.div>
);

// --- MAIN DASHBOARD ---

const AdminDashboard = () => {
    const navigate = useNavigate();
    const { user, logout, isAdmin } = useAuthStore();
    const [activeTab, setActiveTab] = useState("overview");

    // Data State
    const [stats, setStats] = useState<any>(null);
    const [systemHealth, setSystemHealth] = useState<any>(null);
    const [users, setUsers] = useState<any[]>([]);
    const [userSearch, setUserSearch] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    // UI State
    const [selectedUser, setSelectedUser] = useState<any>(null);
    const [isUserModalOpen, setIsUserModalOpen] = useState(false);

    // Initial Check
    useEffect(() => {
        if (!user || !isAdmin) {
            navigate('/admin/login');
        }
    }, [user, isAdmin, navigate]);

    // Fetch Data Loop
    useEffect(() => {
        const fetchData = async () => {
            try {
                if (activeTab === 'overview') {
                    const statsRes = await adminAPI.getStats();
                    const healthRes = await adminAPI.getSystemHealth();
                    if (statsRes.data) setStats(statsRes.data);
                    if (healthRes.data) setSystemHealth(healthRes.data);
                } else if (activeTab === 'users') {
                    const usersRes = await adminAPI.getUsers({ search: userSearch });
                    if (usersRes.data) setUsers(usersRes.data.users);
                }
            } catch (e) {
                console.error("Fetch error", e);
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, [activeTab, userSearch]);

    // Actions
    const handleUserAction = async (userId: string, action: string) => {
        const res = await adminAPI.performUserAction(userId, action);
        if (res.error) {
            toast.error(res.error);
        } else {
            toast.success(res.data.message);
            // Refresh list
            const usersRes = await adminAPI.getUsers({ search: userSearch });
            if (usersRes.data) setUsers(usersRes.data.users);
            setIsUserModalOpen(false);
        }
    };

    const handleImpersonate = async (userId: string) => {
        // Security Notice
        const confirmed = window.confirm("⚠️ GOD MODE ACTIVATION\n\nYou are about to impersonate this user. EVERYTHING you see and do will be as them.\nThis action is logged.\n\nProceed?");
        if (!confirmed) return;

        const res = await adminAPI.impersonateUser(userId);
        if (res.error) {
            toast.error(res.error);
        } else {
            toast.success("Impersonation active. Redirecting...");
            setTimeout(() => window.location.href = "/", 1000);
        }
    };

    // --- RENDER ---

    if (isLoading && !stats && !users.length) {
        return (
            <div className="h-screen w-full flex items-center justify-center bg-zinc-950 text-white">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
                    <p className="font-mono text-zinc-400">Loading Admin Core...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-zinc-950 text-white flex overflow-hidden">
            {/* SIDEBAR */}
            <motion.div
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="w-64 border-r border-white/10 bg-zinc-900/50 backdrop-blur-xl p-4 flex flex-col gap-2 z-20 shadow-2xl"
            >
                <div className="flex items-center gap-3 px-2 py-4 mb-4">
                    <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center">
                        <Shield className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="font-bold text-lg">Prism Admin</h1>
                        <p className="text-xs text-zinc-500">God Mode Active</p>
                    </div>
                </div>

                <nav className="space-y-1 flex-1">
                    {[
                        { id: 'overview', icon: Activity, label: 'Overview' },
                        { id: 'users', icon: Users, label: 'User Management' },
                        { id: 'sessions', icon: MessageSquare, label: 'Session Intel' },
                        { id: 'system', icon: Server, label: 'System Health' },
                    ].map((item) => (
                        <Button
                            key={item.id}
                            variant={activeTab === item.id ? "secondary" : "ghost"}
                            className="w-full justify-start gap-3"
                            onClick={() => setActiveTab(item.id)}
                        >
                            <item.icon className="w-4 h-4" />
                            {item.label}
                        </Button>
                    ))}
                </nav>

                <div className="mt-auto border-t border-white/10 pt-4">
                    <div className="flex items-center gap-3 px-2 mb-3">
                        <Avatar className="w-8 h-8 rounded-lg">
                            <AvatarFallback className="bg-purple-900 text-purple-200">A</AvatarFallback>
                        </Avatar>
                        <div className="overflow-hidden">
                            <p className="text-sm font-medium truncate">{user?.email}</p>
                            <p className="text-xs text-zinc-500">Super Admin</p>
                        </div>
                    </div>
                    <Button variant="ghost" className="w-full justify-start gap-3 text-red-400 hover:text-red-300 hover:bg-red-950/30" onClick={() => logout()}>
                        <LogOut className="w-4 h-4" />
                        Log Out
                    </Button>
                </div>
            </motion.div>

            {/* MAIN CONTENT */}
            <div className="flex-1 overflow-auto">
                <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-black/20 backdrop-blur-md sticky top-0 z-50">
                    <h2 className="text-xl font-semibold capitalize">{activeTab.replace('-', ' ')}</h2>
                    <div className="flex items-center gap-4">
                        {systemHealth && (
                            <div className="flex items-center gap-2 text-xs bg-zinc-900/80 px-3 py-1.5 rounded-full border border-zinc-800">
                                <Cpu className="w-3 h-3 text-blue-400" />
                                <span>{systemHealth.cpu_usage}%</span>
                                <div className="h-3 w-px bg-zinc-700 mx-1" />
                                <Database className="w-3 h-3 text-green-400" />
                                <span>{systemHealth.memory_usage}%</span>
                                <div className="h-3 w-px bg-zinc-700 mx-1" />
                                <Wifi className="w-3 h-3 text-yellow-400" />
                                <span>{systemHealth.db_latency_ms}ms</span>
                            </div>
                        )}
                    </div>
                </header>

                <main className="p-8">
                    {activeTab === 'overview' && (
                        <div className="space-y-8">
                            {/* Stats Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                <StatCard index={0} title="Total Users" value={stats?.total_users || 0} icon={Users} color="text-blue-500" />
                                <StatCard index={1} title="Active Sessions" value={stats?.total_sessions || 0} icon={MessageSquare} color="text-green-500" />
                                <StatCard index={2} title="System Load" value={`${systemHealth?.cpu_usage || 0}%`} icon={Cpu} color="text-yellow-500" />
                                <StatCard index={3} title="Growth Rate" value={`+${stats?.growth_rate || 0}%`} icon={Activity} color="text-purple-500" />
                            </div>

                            {/* Charts */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                <Card className="bg-black/40 border-white/10 col-span-1">
                                    <CardHeader>
                                        <CardTitle>Activity Trend</CardTitle>
                                    </CardHeader>
                                    <CardContent className="h-[300px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={[
                                                { name: 'Mon', value: 40 }, { name: 'Tue', value: 30 }, { name: 'Wed', value: 20 },
                                                { name: 'Thu', value: 27 }, { name: 'Fri', value: 18 }, { name: 'Sat', value: 23 }, { name: 'Sun', value: 34 }
                                            ]}>
                                                <defs>
                                                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <XAxis dataKey="name" stroke="#555" iconType="circle" />
                                                <YAxis stroke="#555" />
                                                <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333' }} />
                                                <Area type="monotone" dataKey="value" stroke="#8884d8" fillOpacity={1} fill="url(#colorValue)" />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </CardContent>
                                </Card>
                                <Card className="bg-black/40 border-white/10 col-span-1">
                                    <CardHeader>
                                        <CardTitle>User Growth</CardTitle>
                                    </CardHeader>
                                    <CardContent className="h-[300px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={[
                                                { name: 'Jan', value: 10 }, { name: 'Feb', value: 25 }, { name: 'Mar', value: 40 },
                                                { name: 'Apr', value: 55 }, { name: 'May', value: 80 }, { name: 'Jun', value: 110 }
                                            ]}>
                                                <XAxis dataKey="name" stroke="#555" />
                                                <YAxis stroke="#555" />
                                                <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333' }} />
                                                <Line type="monotone" dataKey="value" stroke="#82ca9d" strokeWidth={3} dot={{ r: 4 }} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    )}

                    {activeTab === 'users' && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="relative w-64">
                                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-zinc-500" />
                                    <Input
                                        placeholder="Search users..."
                                        className="pl-8 bg-black/40 border-white/10"
                                        value={userSearch}
                                        onChange={(e) => setUserSearch(e.target.value)}
                                    />
                                </div>
                                <Button variant="outline" onClick={() => setUserSearch("")}>Refresh</Button>
                            </div>

                            <Card className="bg-black/40 border-white/10">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-white/5 hover:bg-transparent">
                                            <TableHead>User</TableHead>
                                            <TableHead>Role</TableHead>
                                            <TableHead>Status</TableHead>
                                            <TableHead>Joined</TableHead>
                                            <TableHead className="text-right">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {users.map((u) => (
                                            <TableRow key={u.id} className="border-white/5 hover:bg-white/5">
                                                <TableCell className="font-medium">
                                                    <div className="flex items-center gap-3">
                                                        <Avatar className="w-8 h-8 rounded-md bg-zinc-800">
                                                            <AvatarFallback>{u.name?.[0] || u.email[0]}</AvatarFallback>
                                                        </Avatar>
                                                        <div className="flex flex-col">
                                                            <span>{u.name || "N/A"}</span>
                                                            <span className="text-xs text-zinc-500">{u.email}</span>
                                                        </div>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="outline" className={u.role === 'admin' ? "border-purple-500 text-purple-400" : "border-zinc-700 text-zinc-400"}>
                                                        {u.role}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    {u.is_banned ? (
                                                        <Badge variant="destructive">Banned</Badge>
                                                    ) : (
                                                        <Badge className="bg-green-500/10 text-green-400 hover:bg-green-500/20">Active</Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-zinc-500 text-sm">
                                                    {new Date(u.created_at).toLocaleDateString()}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                                <span className="sr-only">Open menu</span>
                                                                <Eye className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end" className="bg-zinc-900 border-zinc-800 text-white">
                                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                            <DropdownMenuSeparator className="bg-zinc-800" />
                                                            <DropdownMenuItem onClick={() => { setSelectedUser(u); setIsUserModalOpen(true); }}>
                                                                View Details
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem className="text-red-400 focus:text-red-400" onClick={() => handleImpersonate(u.id)}>
                                                                <Key className="mr-2 h-4 w-4" /> Impersonate
                                                            </DropdownMenuItem>
                                                            <DropdownMenuSeparator className="bg-zinc-800" />
                                                            {u.is_banned ? (
                                                                <DropdownMenuItem onClick={() => handleUserAction(u.id, "unban")}>
                                                                    <CheckCircle className="mr-2 h-4 w-4" /> Unban User
                                                                </DropdownMenuItem>
                                                            ) : (
                                                                <DropdownMenuItem className="text-red-500 focus:text-red-500" onClick={() => handleUserAction(u.id, "ban")}>
                                                                    <Ban className="mr-2 h-4 w-4" /> Ban User
                                                                </DropdownMenuItem>
                                                            )}
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </Card>
                        </div>
                    )}

                    {activeTab === 'sessions' && (
                        <div className="flex items-center justify-center h-96 text-zinc-500">
                            <div className="text-center space-y-2">
                                <Database className="w-12 h-12 mx-auto opacity-50" />
                                <p>Session Intelligence Module Loading...</p>
                                <p className="text-xs">Feature available in next update.</p>
                            </div>
                        </div>
                    )}

                    {/* User Detail Modal */}
                    <Dialog open={isUserModalOpen} onOpenChange={setIsUserModalOpen}>
                        <DialogContent className="bg-zinc-900 border-zinc-800 text-white sm:max-w-xl">
                            <DialogHeader>
                                <DialogTitle>User Profile Analysis</DialogTitle>
                                <DialogDescription>Deep dive into user metrics</DialogDescription>
                            </DialogHeader>
                            {selectedUser && (
                                <div className="space-y-6 pt-4">
                                    <div className="flex items-start gap-4">
                                        <Avatar className="w-20 h-20 rounded-xl bg-zinc-800">
                                            <AvatarFallback className="text-2xl">{selectedUser.email[0].toUpperCase()}</AvatarFallback>
                                        </Avatar>
                                        <div className="space-y-1">
                                            <h3 className="text-xl font-bold">{selectedUser.name || "Unknown"}</h3>
                                            <p className="text-zinc-400">{selectedUser.email}</p>
                                            <div className="flex gap-2 pt-2">
                                                <Badge variant="outline">{selectedUser.role}</Badge>
                                                <Badge variant="outline">{selectedUser.is_banned ? 'Banned' : 'Active'}</Badge>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 bg-black/40 rounded-lg border border-white/5">
                                            <p className="text-xs text-zinc-500">User ID</p>
                                            <p className="font-mono text-sm truncate">{selectedUser.id}</p>
                                        </div>
                                        <div className="p-4 bg-black/40 rounded-lg border border-white/5">
                                            <p className="text-xs text-zinc-500">Joined On</p>
                                            <p className="text-sm">{new Date(selectedUser.created_at).toLocaleDateString()}</p>
                                        </div>
                                    </div>

                                    <Button className="w-full bg-red-600/10 text-red-500 hover:bg-red-600/20 border border-red-600/20" variant="outline" onClick={() => handleImpersonate(selectedUser.id)}>
                                        <Key className="mr-2 h-4 w-4" />
                                        Login as {selectedUser.name || "User"}
                                    </Button>
                                </div>
                            )}
                        </DialogContent>
                    </Dialog>

                </main>
            </div>
        </div>
    );
};

export default AdminDashboard;
