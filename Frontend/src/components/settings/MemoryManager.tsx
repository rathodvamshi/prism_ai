import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Trash2, Plus, RefreshCw, Network } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const MemoryManager = () => {
    const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] } | null>(null);
    const [loading, setLoading] = useState(false);
    const [newItem, setNewItem] = useState({ relationship: "", target: "", category: "Entity" });
    const { toast } = useToast();

    const fetchGraph = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem("token");
            const res = await fetch("http://127.0.0.1:8000/chat/memory/graph", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.success) {
                setGraphData(data.data);
            }
        } catch (e) {
            console.error(e);
            toast({ title: "Error", description: "Failed to load memory graph", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGraph();
    }, []);

    const handleAdd = async () => {
        if (!newItem.relationship || !newItem.target) return;
        try {
            const token = localStorage.getItem("token");
            const res = await fetch("http://127.0.0.1:8000/chat/memory/relationship", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(newItem)
            });
            if (res.ok) {
                toast({ title: "Success", description: "Memory added successfully" });
                setNewItem({ relationship: "", target: "", category: "Entity" });
                fetchGraph();
            }
        } catch (e) {
            toast({ title: "Error", description: "Failed to add memory", variant: "destructive" });
        }
    };

    const handleDelete = async (target: string, relationship: string) => {
        try {
            const token = localStorage.getItem("token");
            const res = await fetch("http://127.0.0.1:8000/chat/memory/relationship", {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ target, relationship })
            });
            if (res.ok) {
                toast({ title: "Deleted", description: "Memory removed" });
                fetchGraph();
            }
        } catch (e) {
            toast({ title: "Error", description: "Failed to delete memory", variant: "destructive" });
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header Section */}
            <div className="flex items-center justify-between">
                <div className="space-y-1">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                        <Network className="w-4 h-4 text-primary" />
                        Knowledge Graph
                    </h4>
                    <p className="text-xs text-muted-foreground">
                        Manage the relationships and entities the AI remembers about you.
                    </p>
                </div>
                <Button size="sm" variant="outline" onClick={fetchGraph} disabled={loading} className="h-8 gap-2">
                    {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                    Refresh
                </Button>
            </div>

            {/* Add New Memory Section */}
            <div className="p-4 bg-secondary/30 rounded-xl border border-border/50 space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <Plus className="w-4 h-4 text-primary" />
                    <h5 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Add New Memory</h5>
                </div>

                <div className="grid gap-4 sm:grid-cols-12">
                    <div className="sm:col-span-4 space-y-1.5">
                        <Label className="text-xs">Relationship Type</Label>
                        <Select value={newItem.relationship} onValueChange={(v) => setNewItem({ ...newItem, relationship: v })}>
                            <SelectTrigger className="h-9 text-xs"><SelectValue placeholder="Select Type" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="LIKES">LIKES</SelectItem>
                                <SelectItem value="KNOWS">KNOWS</SelectItem>
                                <SelectItem value="LIVES_IN">LIVES_IN</SelectItem>
                                <SelectItem value="WORKS_AT">WORKS_AT</SelectItem>
                                <SelectItem value="HAS_GOAL">HAS_GOAL</SelectItem>
                                <SelectItem value="INTERESTED_IN">INTERESTED_IN</SelectItem>
                                <SelectItem value="PREFERS">PREFERS</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="sm:col-span-3 space-y-1.5">
                        <Label className="text-xs">Category</Label>
                        <Select value={newItem.category} onValueChange={(v) => setNewItem({ ...newItem, category: v })}>
                            <SelectTrigger className="h-9 text-xs"><SelectValue placeholder="Category" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Entity">Entity</SelectItem>
                                <SelectItem value="Interest">Interest</SelectItem>
                                <SelectItem value="Location">Location</SelectItem>
                                <SelectItem value="Person">Person</SelectItem>
                                <SelectItem value="Skill">Skill</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="sm:col-span-5 space-y-1.5">
                        <Label className="text-xs">Target Value</Label>
                        <div className="flex gap-2">
                            <Input
                                className="h-9 text-xs"
                                placeholder="e.g. Quantum Computing"
                                value={newItem.target}
                                onChange={(e) => setNewItem({ ...newItem, target: e.target.value })}
                                onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                            />
                            <Button size="sm" className="h-9 px-3" onClick={handleAdd} disabled={!newItem.target || !newItem.relationship}>
                                Add
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Existing Memories List */}
            <div className="space-y-3">
                <h5 className="text-xs font-medium uppercase tracking-wider text-muted-foreground ml-1">Existing Memories</h5>

                <div className="bg-background rounded-xl border border-border overflow-hidden min-h-[200px] max-h-[400px] overflow-y-auto relative">
                    {loading && !graphData && (
                        <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                            <Loader2 className="w-6 h-6 animate-spin text-primary" />
                        </div>
                    )}

                    <div className="p-1 space-y-1">
                        <AnimatePresence mode="popLayout">
                            {graphData?.links.length === 0 ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex flex-col items-center justify-center py-12 text-muted-foreground"
                                >
                                    <Network className="w-8 h-8 mb-2 opacity-20" />
                                    <p className="text-sm">No memories recorded yet.</p>
                                    <p className="text-xs opacity-60">Chat with the AI to build your graph.</p>
                                </motion.div>
                            ) : (
                                graphData?.links.map((link, i) => {
                                    const targetNode = graphData.nodes.find(n => n.id === link.target);
                                    return (
                                        <motion.div
                                            key={`${link.source}-${link.label}-${link.target}`}
                                            layout
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            className="group flex items-center justify-between p-3 hover:bg-secondary/40 rounded-lg border border-transparent hover:border-border/50 transition-all"
                                        >
                                            <div className="flex items-center gap-3 overflow-hidden">
                                                <div className="flex items-center gap-2 text-xs font-mono shrink-0">
                                                    <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">ME</span>
                                                    <span className="text-muted-foreground/60">──</span>
                                                    <span className="px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground text-[10px] uppercase tracking-wider border border-border/50">
                                                        {link.label}
                                                    </span>
                                                    <span className="text-muted-foreground/60">──▶</span>
                                                </div>
                                                <span className="text-sm font-medium truncate text-foreground">
                                                    {targetNode?.name || "Unknown"}
                                                </span>
                                                {targetNode?.labels && targetNode.labels.length > 0 && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground hidden sm:inline-block">
                                                        {targetNode.labels[0]}
                                                    </span>
                                                )}
                                            </div>

                                            <Button
                                                variant="ghost"
                                                size="icon-sm"
                                                className="h-7 w-7 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                                                onClick={() => handleDelete(targetNode?.name || "", link.label)}
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </Button>
                                        </motion.div>
                                    );
                                })
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
};
