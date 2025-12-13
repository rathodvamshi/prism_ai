import { motion, useScroll, useTransform } from "framer-motion";
import { useRef, useState } from "react";
import {
  MessageSquare,
  Highlighter,
  Network,
  Sparkles,
  Zap,
  ArrowRight,
  Check,
  Play,
  Bot,
  Brain,
  User,
  Send,
  MoreHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

export const PrototypeShowcase = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const y = useTransform(scrollYProgress, [0, 1], [100, -100]);
  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0, 1, 1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0.8, 1, 1, 0.8]);

  const [activeTab, setActiveTab] = useState<"chat" | "highlight" | "graph" | "agent">("chat");

  const features = [
    {
      id: "chat" as const,
      icon: MessageSquare,
      title: "AI Chat",
      description: "Intelligent conversations with context",
      color: "from-blue-500 to-cyan-500",
      accentColor: "text-blue-400",
      bgColor: "bg-blue-500/20",
      borderColor: "border-blue-500/30",
    },
    {
      id: "highlight" as const,
      icon: Highlighter,
      title: "Smart Highlights",
      description: "Instant text analysis and insights",
      color: "from-yellow-500 to-orange-500",
      accentColor: "text-yellow-400",
      bgColor: "bg-yellow-500/20",
      borderColor: "border-yellow-500/30",
    },
    {
      id: "agent" as const,
      icon: Bot,
      title: "Mini Agent",
      description: "AI-powered task automation",
      color: "from-green-500 to-emerald-500",
      accentColor: "text-green-400",
      bgColor: "bg-green-500/20",
      borderColor: "border-green-500/30",
    },
    {
      id: "graph" as const,
      icon: Network,
      title: "Knowledge Graph",
      description: "Visual connection mapping",
      color: "from-purple-500 to-pink-500",
      accentColor: "text-purple-400",
      bgColor: "bg-purple-500/20",
      borderColor: "border-purple-500/30",
    },
  ];

  const mockScreenshots = {
    chat: {
      title: "Intelligent Conversations",
      description: "Experience AI that truly understands context and remembers your preferences",
      highlights: [
        "Context-aware responses",
        "Long-term memory",
        "Multi-turn conversations",
        "Personalized insights",
      ],
    },
    highlight: {
      title: "Instant Text Analysis",
      description: "Select any text to get AI-powered insights, summaries, and custom highlights",
      highlights: [
        "One-click highlighting",
        "AI-powered summaries",
        "Custom color coding",
        "Smart categorization",
      ],
    },
    agent: {
      title: "Mini AI Agents",
      description: "Create specialized mini agents for specific tasks and workflows",
      highlights: [
        "Task automation",
        "Custom workflows",
        "Parallel processing",
        "Quick responses",
      ],
    },
    graph: {
      title: "Visual Knowledge Maps",
      description: "See your ideas and conversations come to life in interactive knowledge graphs",
      highlights: [
        "Interactive visualization",
        "Connection discovery",
        "Topic clustering",
        "Export & share",
      ],
    },
  };

  return (
    <section
      ref={containerRef}
      className="relative py-24 sm:py-32 bg-gradient-to-b from-background via-secondary/5 to-background overflow-hidden"
    >
      {/* Background effects */}
      <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:50px_50px]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-primary/5 via-purple-500/5 to-pink-500/5 rounded-full blur-3xl" />

      <div className="container relative z-10 px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 mb-6 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium shadow-soft"
          >
            <Play className="w-4 h-4" />
            <span>See It In Action</span>
          </motion.div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-4">
            Experience PRISM{" "}
            <span className="bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-clip-text text-transparent">
              In Action
            </span>
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
            Discover how PRISM transforms your workflow with intelligent AI assistance
          </p>
        </motion.div>

        {/* Feature Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 mb-12"
        >
          {features.map((feature, index) => (
            <motion.button
              key={feature.id}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 + index * 0.1 }}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab(feature.id)}
              className={`group relative px-6 py-4 rounded-2xl transition-all duration-300 ${
                activeTab === feature.id
                  ? `border-2 ${feature.borderColor} shadow-xl ${feature.bgColor} backdrop-blur-sm`
                  : "border border-border bg-card/50 hover:border-border/80"
              }`}
            >
              {/* Active indicator glow */}
              {activeTab === feature.id && (
                <motion.div
                  layoutId="activeTab"
                  className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${feature.color} opacity-10`}
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}

              <div className="relative flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-300 ${
                    activeTab === feature.id
                      ? `bg-gradient-to-br ${feature.color} text-white`
                      : "bg-secondary text-muted-foreground"
                  }`}
                >
                  <feature.icon className="w-5 h-5" />
                </div>
                <div className="text-left">
                  <div
                    className={`font-semibold transition-colors duration-300 ${
                      activeTab === feature.id ? feature.accentColor : "text-foreground"
                    }`}
                  >
                    {feature.title}
                  </div>
                  <div className="text-xs text-muted-foreground">{feature.description}</div>
                </div>
              </div>
            </motion.button>
          ))}
        </motion.div>

        {/* Prototype Display */}
        <motion.div
          style={{ y, opacity, scale }}
          className="max-w-6xl mx-auto"
        >
          <div className="relative">
            {/* Main showcase card */}
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="relative bg-gradient-to-br from-card/80 to-card/40 backdrop-blur-xl rounded-3xl border border-border shadow-2xl overflow-hidden"
            >
              {/* Decorative gradients */}
              <div className={`absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl ${features.find(f => f.id === activeTab)?.color} opacity-5 rounded-full blur-3xl`} />
              <div className={`absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr ${features.find(f => f.id === activeTab)?.color} opacity-5 rounded-full blur-3xl`} />

              <div className="relative grid lg:grid-cols-2 gap-8 p-8 lg:p-12">
                {/* Left side - Description */}
                <div className="flex flex-col justify-center space-y-6">
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <h3 className="text-2xl sm:text-3xl font-bold text-foreground mb-3">
                      {mockScreenshots[activeTab].title}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed mb-6">
                      {mockScreenshots[activeTab].description}
                    </p>
                  </motion.div>

                  {/* Feature highlights */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="space-y-3"
                  >
                    {mockScreenshots[activeTab].highlights.map((highlight, index) => (
                      <motion.div
                        key={highlight}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 + index * 0.1 }}
                        className="flex items-center gap-3"
                      >
                        <div className={`w-6 h-6 rounded-full bg-gradient-to-br ${features.find(f => f.id === activeTab)?.color} flex items-center justify-center flex-shrink-0`}>
                          <Check className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-sm text-foreground/80">{highlight}</span>
                      </motion.div>
                    ))}
                  </motion.div>

                  {/* CTA */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="pt-4"
                  >
                    <Button
                      variant="hero"
                      size="lg"
                      asChild
                      className="group"
                    >
                      <Link to="/chat" className="gap-2">
                        Try It Now
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                      </Link>
                    </Button>
                  </motion.div>
                </div>

                {/* Right side - Mock Interface */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 }}
                  className="relative"
                >
                  {/* Browser-like mockup */}
                  <div className="relative bg-background/60 backdrop-blur-sm rounded-2xl border border-border shadow-xl overflow-hidden">
                    {/* Browser header */}
                    <div className="flex items-center gap-2 px-4 py-3 bg-secondary/30 border-b border-border">
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/80" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                        <div className="w-3 h-3 rounded-full bg-green-500/80" />
                      </div>
                      <div className="flex-1 flex items-center justify-center">
                        <div className="flex items-center gap-2 px-4 py-1.5 bg-background/50 rounded-lg border border-border text-xs text-muted-foreground">
                          <Sparkles className="w-3 h-3" />
                          <span>prism-ai.app/{activeTab}</span>
                        </div>
                      </div>
                    </div>

                    {/* Mock content */}
                    <div className="p-6 min-h-[400px] bg-gradient-to-br from-background/50 to-secondary/20">
                      {activeTab === "chat" && <ChatMockup />}
                      {activeTab === "highlight" && <HighlightMockup />}
                      {activeTab === "agent" && <MiniAgentMockup />}
                      {activeTab === "graph" && <GraphMockup />}
                    </div>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

// Chat Mockup Component
const ChatMockup = () => {
  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
        className="flex items-start gap-3"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 bg-secondary/50 rounded-2xl rounded-tl-sm p-4 border border-border">
          <p className="text-sm text-foreground/90">
            Hello! I'm PRISM. I can help you with research, writing, and organizing your thoughts. What would you like to work on today?
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="flex items-start gap-3 justify-end"
      >
        <div className="flex-1 bg-primary/10 rounded-2xl rounded-tr-sm p-4 border border-primary/20 max-w-[80%]">
          <p className="text-sm text-foreground/90">
            Help me understand quantum computing concepts
          </p>
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-semibold">You</span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5 }}
        className="flex items-start gap-3"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 bg-secondary/50 rounded-2xl rounded-tl-sm p-4 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-4 h-4 text-primary" />
            <span className="text-xs text-primary font-medium">Thinking...</span>
          </div>
          <div className="space-y-2">
            <div className="h-2 bg-foreground/10 rounded-full w-full animate-pulse" />
            <div className="h-2 bg-foreground/10 rounded-full w-4/5 animate-pulse" />
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Highlight Mockup Component
const HighlightMockup = () => {
  const [selectedColor, setSelectedColor] = useState<string>('bg-yellow-400/40');
  const [showPicker, setShowPicker] = useState(false);
  
  const colors = [
    { name: 'Yellow', class: 'bg-yellow-400/40', buttonClass: 'bg-yellow-400' },
    { name: 'Blue', class: 'bg-blue-400/40', buttonClass: 'bg-blue-400' },
    { name: 'Pink', class: 'bg-pink-400/40', buttonClass: 'bg-pink-400' },
    { name: 'Green', class: 'bg-green-400/40', buttonClass: 'bg-green-400' },
    { name: 'Purple', class: 'bg-purple-400/40', buttonClass: 'bg-purple-400' },
  ];

  return (
    <div className="space-y-6">
      {/* Document mockup with selection */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative p-6 bg-card/50 backdrop-blur-sm rounded-xl border border-border"
      >
        <p className="text-sm text-foreground/70 leading-relaxed">
          Artificial intelligence is transforming how we{" "}
          <span 
            className="relative inline-block group cursor-pointer"
            onMouseEnter={() => setShowPicker(true)}
          >
            <span className="relative z-10 px-1.5 py-0.5 text-foreground font-medium">work and create</span>
            <motion.span
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className={`absolute inset-0 ${selectedColor} rounded origin-left`}
            />
            {/* Interactive color picker */}
            {showPicker && (
              <motion.div
                initial={{ opacity: 0, y: -5, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                className="absolute -top-14 left-1/2 -translate-x-1/2 whitespace-nowrap z-20"
              >
                <div className="flex items-center gap-1.5 px-3 py-2 bg-background/95 backdrop-blur-xl rounded-lg border border-border shadow-2xl">
                  {colors.map((color) => (
                    <motion.button
                      key={color.name}
                      onClick={() => setSelectedColor(color.class)}
                      whileHover={{ scale: 1.15 }}
                      whileTap={{ scale: 0.9 }}
                      className={`relative p-1.5 rounded transition-all ${
                        selectedColor === color.class ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : 'hover:scale-110'
                      }`}
                      title={color.name}
                    >
                      <div className={`w-4 h-4 ${color.buttonClass} rounded-sm`} />
                    </motion.button>
                  ))}
                  <div className="w-px h-4 bg-border mx-1" />
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="p-1.5 hover:bg-primary/10 rounded transition-colors"
                    title="AI Insights"
                  >
                    <Sparkles className="w-4 h-4 text-primary" />
                  </motion.button>
                </div>
              </motion.div>
            )}
          </span>
          . With tools like PRISM, anyone can{" "}
          <span className="relative inline-block">
            <span className="relative z-10 px-1.5 py-0.5 text-foreground font-medium">harness AI power</span>
            <motion.span
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="absolute inset-0 bg-blue-400/40 rounded origin-left"
            />
          </span>{" "}
          for enhanced productivity and creative workflows.
        </p>
      </motion.div>

      {/* AI Insight panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="p-5 bg-gradient-to-br from-primary/10 to-purple-500/10 rounded-xl border border-primary/20 backdrop-blur-sm"
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 space-y-2">
            <h4 className="text-sm font-semibold text-foreground">AI Summary Generated</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This passage discusses AI democratization and its transformative impact on productivity tools and creative processes.
            </p>
            <div className="flex items-center gap-2 pt-2">
              <div className="px-2 py-1 bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded text-xs font-medium">
                Key Concept
              </div>
              <div className="px-2 py-1 bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded text-xs font-medium">
                Technology
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Graph Mockup Component
const GraphMockup = () => {
  const [nodePositions, setNodePositions] = useState([
    { id: 1, x: 50, y: 50, label: "You", color: "from-blue-500 to-cyan-500", size: "large", isUser: true },
    { id: 2, x: 25, y: 20, label: "Chat", color: "from-purple-500 to-pink-500", size: "medium", isUser: false },
    { id: 3, x: 75, y: 25, label: "Memory", color: "from-green-500 to-emerald-500", size: "medium", isUser: false },
    { id: 4, x: 85, y: 55, label: "Search", color: "from-orange-500 to-yellow-500", size: "medium", isUser: false },
    { id: 5, x: 70, y: 78, label: "Tasks", color: "from-pink-500 to-rose-500", size: "small", isUser: false },
    { id: 6, x: 30, y: 80, label: "Graph", color: "from-indigo-500 to-purple-500", size: "small", isUser: false },
    { id: 7, x: 15, y: 50, label: "Voice", color: "from-teal-500 to-cyan-500", size: "small", isUser: false },
    { id: 8, x: 50, y: 18, label: "Research", color: "from-amber-500 to-orange-500", size: "small", isUser: false },
    { id: 9, x: 35, y: 35, label: "Highlights", color: "from-yellow-500 to-amber-500", size: "small", isUser: false },
    { id: 10, x: 65, y: 40, label: "Analytics", color: "from-violet-500 to-purple-500", size: "small", isUser: false },
  ]);

  const [draggedNode, setDraggedNode] = useState<number | null>(null);

  // All nodes connect to the center user node
  const connections = nodePositions
    .filter(node => !node.isUser)
    .map(node => ({ from: 1, to: node.id }));

  const handleNodeDrag = (nodeId: number, e: React.MouseEvent) => {
    if (draggedNode !== nodeId) return;
    
    const container = e.currentTarget.parentElement?.parentElement;
    if (!container) return;
    
    const rect = container.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    setNodePositions(prev => prev.map(node =>
      node.id === nodeId ? { ...node, x: Math.max(10, Math.min(90, x)), y: Math.max(10, Math.min(90, y)) } : node
    ));
  };

  return (
    <div 
      className="relative h-full min-h-[400px] flex items-center justify-center bg-gradient-to-br from-background/50 to-secondary/20 rounded-xl border border-border/50 overflow-hidden select-none"
      onMouseMove={(e) => draggedNode !== null && handleNodeDrag(draggedNode, e)}
      onMouseUp={() => setDraggedNode(null)}
      onMouseLeave={() => setDraggedNode(null)}
    >
      {/* Info text */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute top-3 left-3 text-xs text-muted-foreground bg-background/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-border"
      >
        <span className="flex items-center gap-2">
          <Network className="w-3 h-3" />
          Drag nodes to reposition
        </span>
      </motion.div>

      {/* Center container */}
      <div className="relative w-full h-full">
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {/* Animated connections */}
          {connections.map((conn, idx) => {
            const fromNode = nodePositions.find(n => n.id === conn.from);
            const toNode = nodePositions.find(n => n.id === conn.to);
            if (!fromNode || !toNode) return null;
            
            return (
              <g key={`${conn.from}-${conn.to}`}>
                <motion.line
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.5 }}
                  transition={{ delay: 0.2 + idx * 0.05, duration: 0.6 }}
                  x1={`${fromNode.x}%`}
                  y1={`${fromNode.y}%`}
                  x2={`${toNode.x}%`}
                  y2={`${toNode.y}%`}
                  stroke="url(#gradient-strong)"
                  strokeWidth="2.5"
                />
              </g>
            );
          })}
          
          {/* Gradient definitions */}
          <defs>
            <linearGradient id="gradient-strong" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgb(59, 130, 246)" stopOpacity="0.7" />
              <stop offset="100%" stopColor="rgb(147, 51, 234)" stopOpacity="0.7" />
            </linearGradient>
          </defs>
        </svg>

        {/* Draggable Nodes */}
        {nodePositions.map((node, index) => {
          const sizeClasses = {
            large: "w-20 h-20",
            medium: "w-16 h-16",
            small: "w-12 h-12",
          };
          
          return (
            <motion.div
              key={node.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 + index * 0.1, type: "spring", bounce: 0.5 }}
              whileHover={{ scale: 1.1, zIndex: 10 }}
              drag
              dragMomentum={false}
              dragElastic={0}
              onDragStart={() => setDraggedNode(node.id)}
              onDragEnd={() => setDraggedNode(null)}
              className="absolute cursor-grab active:cursor-grabbing"
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <div className="relative group">
                {/* Glow effect */}
                <div className={`absolute inset-0 bg-gradient-to-br ${node.color} opacity-30 rounded-full blur-lg group-hover:opacity-60 group-hover:blur-xl transition-all`} />
                
                {/* Node circle */}
                <div className={`relative ${sizeClasses[node.size as keyof typeof sizeClasses]} rounded-full bg-gradient-to-br ${node.color} flex items-center justify-center border-3 border-background shadow-xl group-hover:shadow-2xl transition-shadow`}>
                  {node.isUser ? (
                    <User className="w-1/2 h-1/2 text-white" />
                  ) : (
                    <Network className="w-1/2 h-1/2 text-white" />
                  )}
                  
                  {/* Pulse animation */}
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-current opacity-75"
                    animate={{
                      scale: [1, 1.4, 1],
                      opacity: [0.5, 0, 0.5],
                    }}
                    transition={{
                      duration: 2.5,
                      repeat: Infinity,
                      delay: index * 0.3,
                      ease: "easeInOut",
                    }}
                  />
                </div>
                
                {/* Label */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap pointer-events-none"
                >
                  <div className="px-2.5 py-1 bg-background/95 backdrop-blur-sm rounded-full border border-border text-xs font-semibold shadow-lg">
                    {node.label}
                  </div>
                </motion.div>

                {/* Connection count badge */}
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-gradient-to-br from-primary to-purple-500 border-2 border-background flex items-center justify-center text-[10px] font-bold text-white shadow-lg pointer-events-none">
                  {connections.filter(c => c.from === node.id || c.to === node.id).length}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

// Mini Agent Mockup Component
const MiniAgentMockup = () => {
  const [messages, setMessages] = useState([
    { id: 1, type: 'ai', text: "Hi! I'm your Mini-Agent. How can I assist you today?" },
    { id: 2, type: 'user', text: "Help me with task automation" },
    { id: 3, type: 'ai', text: "I can help you automate repetitive tasks. What specific workflow would you like to optimize?" },
  ]);
  const [input, setInput] = useState('');

  const responses = [
    "That's a great question! Let me help you with that.",
    "I've processed your request and found some relevant information.",
    "Based on the context, here's what I recommend...",
    "I can definitely assist with that task.",
    "Let me analyze that for you.",
  ];

  const handleSend = () => {
    if (!input.trim()) return;
    
    const userMsg = { id: Date.now(), type: 'user' as const, text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    
    setTimeout(() => {
      const aiMsg = {
        id: Date.now() + 1,
        type: 'ai' as const,
        text: responses[Math.floor(Math.random() * responses.length)]
      };
      setMessages(prev => [...prev, aiMsg]);
    }, 1000);
  };

  return (
    <div className="flex gap-3 h-[400px]">
      {/* Main chat area - Left side */}
      <div className="flex-1 flex flex-col bg-secondary/20 rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 pb-3 mb-3 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-white" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-foreground">PRISM</h4>
            <p className="text-xs text-muted-foreground">Main Chat</p>
          </div>
        </div>

        <div className="flex-1 space-y-3 overflow-auto mb-3 scrollbar-hide">
          {messages.slice(0, 3).map((msg, idx) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.2 }}
              className={`flex items-start gap-2 ${msg.type === 'user' ? 'justify-end' : ''}`}
            >
              {msg.type === 'ai' && (
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
              )}
              <div className={`px-3 py-2 rounded-xl text-xs max-w-[75%] ${
                msg.type === 'ai' 
                  ? 'bg-secondary/50 border border-border text-foreground/90' 
                  : 'bg-blue-500/20 border border-blue-500/30 text-foreground/90'
              }`}>
                {msg.text}
              </div>
              {msg.type === 'user' && (
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                  <User className="w-3.5 h-3.5 text-white" />
                </div>
              )}
            </motion.div>
          ))}
        </div>

        <div className="flex items-center gap-2 p-2 bg-background/50 rounded-lg border border-border">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Message PRISM..."
            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none px-1"
          />
          <button 
            onClick={handleSend}
            className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center hover:scale-105 transition-transform"
          >
            <Send className="w-3 h-3 text-white" />
          </button>
        </div>
      </div>

      {/* Mini-Agent sidebar - Right side */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
        className="w-64 flex flex-col bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-xl border border-green-500/20 p-4"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3 pb-3 border-b border-green-500/20">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center relative">
              <Bot className="w-4 h-4 text-white" />
              <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-background animate-pulse" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-foreground">Mini-Agent</h4>
              <p className="text-xs text-green-600 dark:text-green-400">Context-aware chat</p>
            </div>
          </div>
        </div>

        {/* Mini chat */}
        <div className="flex-1 space-y-2 overflow-auto mb-3 scrollbar-hide">
          {messages.map((msg, idx) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + idx * 0.15 }}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`px-2.5 py-1.5 rounded-lg text-xs max-w-[85%] ${
                msg.type === 'ai'
                  ? 'bg-green-500/20 border border-green-500/30 text-foreground/90'
                  : 'bg-secondary/50 border border-border text-foreground/80'
              }`}>
                {msg.text.slice(0, 60)}{msg.text.length > 60 ? '...' : ''}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mini input */}
        <div className="flex items-center gap-2 p-2 bg-background/30 backdrop-blur-sm rounded-lg border border-green-500/20">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask mini-agent..."
            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none"
          />
          <button 
            onClick={handleSend}
            className="w-6 h-6 rounded-md bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center hover:scale-110 transition-transform"
          >
            <Send className="w-3 h-3 text-white" />
          </button>
        </div>

        {/* Connection indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-3 pt-3 border-t border-green-500/20"
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span>Synced with main chat</span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

