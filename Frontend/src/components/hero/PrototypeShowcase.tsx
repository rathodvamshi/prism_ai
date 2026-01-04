import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { useRef, useState, useEffect, useMemo, useCallback } from "react";
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
  X,
  Users,
  Linkedin,
  Github,
  Instagram,
  Heart,
  ChevronLeft,
  ChevronRight,
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
        "Custom mini-agents",
        "Parallel task execution",
        "Context sharing",
        "Automated workflows",
      ],
    },
    graph: {
      title: "Knowledge Connections",
      description: "Visualize how all your information, conversations, and insights connect",
      highlights: [
        "Interactive graph",
        "Real-time updates",
        "Drag & rearrange",
        "AI-powered clustering",
      ],
    },
  };

  return (
    <section ref={containerRef} className="relative py-12 sm:py-16 md:py-20 lg:py-24 overflow-hidden">
      <div className="container mx-auto px-3 sm:px-4 md:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 60 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center mb-8 sm:mb-12 md:mb-16 space-y-3 sm:space-y-4 px-2"
        >
          <motion.div 
            initial={{ opacity: 0, scale: 0.5, rotate: -10 }}
            whileInView={{ opacity: 1, scale: 1, rotate: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, type: "spring", stiffness: 200 }}
            className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 bg-primary/10 rounded-full border border-primary/20 mb-2 sm:mb-4"
          >
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            >
              <Play className="w-3 h-3 sm:w-4 sm:h-4 text-primary" />
            </motion.div>
            <span className="text-xs sm:text-sm font-medium text-primary">Live Prototypes</span>
          </motion.div>
          <motion.h2 
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-2xl xs:text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-foreground leading-tight"
          >
            Experience PRISM
            <motion.span 
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="block bg-gradient-to-r from-primary via-purple-500 to-pink-500 text-transparent bg-clip-text"
            >
              In Action
            </motion.span>
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-sm sm:text-base md:text-lg text-muted-foreground max-w-2xl mx-auto px-2"
          >
            Interact with live demonstrations of PRISM's core features. See how AI transforms your workflow.
          </motion.p>
        </motion.div>

        {/* Feature Selection Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.7, delay: 0.5, ease: "easeOut" }}
          className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 md:gap-4 mb-8 sm:mb-12 md:mb-16 px-1"
        >
          {features.map((feature) => (
            <motion.button
              key={feature.id}
              onClick={() => setActiveTab(feature.id)}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              className={`relative px-3 sm:px-4 md:px-6 py-3 sm:py-4 rounded-xl sm:rounded-2xl border-2 transition-all duration-300 ${
                activeTab === feature.id
                  ? `${feature.bgColor} ${feature.borderColor} shadow-lg shadow-${feature.id}-500/20`
                  : "bg-card/50 border-border hover:border-border/80"
              }`}
            >
              {activeTab === feature.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-gradient-to-br from-background/10 to-background/5 rounded-xl sm:rounded-2xl"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}

              <div className="relative flex flex-col sm:flex-row items-center gap-2 sm:gap-3">
                <div
                  className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl flex items-center justify-center transition-colors duration-300 ${
                    activeTab === feature.id
                      ? `bg-gradient-to-br ${feature.color} text-white`
                      : "bg-secondary text-muted-foreground"
                  }`}
                >
                  <feature.icon className="w-4 h-4 sm:w-5 sm:h-5" />
                </div>
                <div className="text-center sm:text-left">
                  <div
                    className={`text-xs sm:text-sm md:text-base font-semibold transition-colors duration-300 ${
                      activeTab === feature.id ? feature.accentColor : "text-foreground"
                    }`}
                  >
                    {feature.title}
                  </div>
                  <div className="text-[10px] sm:text-xs text-muted-foreground hidden sm:block">{feature.description}</div>
                </div>
              </div>
            </motion.button>
          ))}
        </motion.div>

        {/* Prototype Display */}
        <motion.div
          style={{ y, opacity, scale }}
          className="max-w-6xl mx-auto px-1 sm:px-2"
        >
          <div className="relative">
            {/* Main showcase card */}
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="relative bg-gradient-to-br from-card/80 to-card/40 backdrop-blur-xl rounded-2xl sm:rounded-3xl border border-border shadow-xl sm:shadow-2xl overflow-hidden"
            >
              {/* Decorative gradients */}
              <div className={`absolute top-0 right-0 w-48 sm:w-64 md:w-80 lg:w-96 h-48 sm:h-64 md:h-80 lg:h-96 bg-gradient-to-bl ${features.find(f => f.id === activeTab)?.color} opacity-5 rounded-full blur-3xl`} />
              <div className={`absolute bottom-0 left-0 w-48 sm:w-64 md:w-80 lg:w-96 h-48 sm:h-64 md:h-80 lg:h-96 bg-gradient-to-tr ${features.find(f => f.id === activeTab)?.color} opacity-5 rounded-full blur-3xl`} />

              <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 md:gap-8 p-4 sm:p-6 md:p-8 lg:p-12">
                {/* Left side - Description */}
                <div className="flex flex-col justify-center space-y-4 sm:space-y-6">
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <h3 className="text-xl sm:text-2xl md:text-3xl font-bold text-foreground mb-2 sm:mb-3">
                      {mockScreenshots[activeTab].title}
                    </h3>
                    <p className="text-sm sm:text-base text-muted-foreground leading-relaxed mb-4 sm:mb-6">
                      {mockScreenshots[activeTab].description}
                    </p>
                  </motion.div>

                  {/* Feature highlights */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="space-y-2 sm:space-y-3"
                  >
                    {mockScreenshots[activeTab].highlights.map((highlight, index) => (
                      <motion.div
                        key={highlight}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 + index * 0.1 }}
                        className="flex items-center gap-2 sm:gap-3"
                      >
                        <div className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-gradient-to-br ${features.find(f => f.id === activeTab)?.color} flex items-center justify-center flex-shrink-0`}>
                          <Check className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                        </div>
                        <span className="text-xs sm:text-sm text-foreground/80">{highlight}</span>
                      </motion.div>
                    ))}
                  </motion.div>

                  {/* CTA */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="pt-2 sm:pt-4"
                  >
                    <Button
                      variant="hero"
                      size="default"
                      asChild
                      className="group w-full sm:w-auto text-sm sm:text-base"
                    >
                      <Link to="/chat" className="gap-2 justify-center">
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
                  <div className="relative bg-background/60 backdrop-blur-sm rounded-xl sm:rounded-2xl border border-border shadow-lg sm:shadow-xl overflow-hidden">
                    {/* Browser header */}
                    <div className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2 sm:py-3 bg-secondary/30 border-b border-border">
                      <div className="flex items-center gap-1 sm:gap-1.5">
                        <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-500/80" />
                        <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-500/80" />
                        <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-green-500/80" />
                      </div>
                      <div className="flex-1 flex items-center justify-center">
                        <div className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-1 sm:py-1.5 bg-background/50 rounded-md sm:rounded-lg border border-border text-[10px] sm:text-xs text-muted-foreground">
                          <Sparkles className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                          <span className="hidden xs:inline">prism-ai.app/{activeTab}</span>
                          <span className="xs:hidden">prism/{activeTab}</span>
                        </div>
                      </div>
                    </div>

                    {/* Mock content */}
                    <div className="p-3 sm:p-4 md:p-6 min-h-[280px] sm:min-h-[350px] md:min-h-[400px] bg-gradient-to-br from-background/50 to-secondary/20">
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

        {/* Built By Team Section */}
        <TeamShowcase />
      </div>
    </section>
  );
};

// Chat Mockup Component
const ChatMockup = () => {
  return (
    <div className="space-y-3 sm:space-y-4 relative">
      {/* Pin Indicator */}
      <motion.div
        initial={{ scale: 0, rotate: -45 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
        className="absolute -top-2 -right-2 z-10 hidden sm:block"
      >
        <div className="relative group">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-blue-500 via-cyan-500 to-blue-600 flex items-center justify-center shadow-xl border-2 border-white/20">
            <MessageSquare className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="absolute -bottom-14 right-0 whitespace-nowrap"
          >
            <motion.div
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg border border-white/30"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-3 h-3" />
                Try live chat!
              </div>
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
        className="flex items-start gap-2 sm:gap-3"
      >
        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </div>
        <div className="flex-1 bg-secondary/50 rounded-xl sm:rounded-2xl rounded-tl-sm p-3 sm:p-4 border border-border">
          <p className="text-xs sm:text-sm text-foreground">
            Hello! I'm your PRISM AI assistant. I can help you with research, writing, coding, and much more. What would you like to work on today?
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="flex items-start gap-2 sm:gap-3 justify-end"
      >
        <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl sm:rounded-2xl rounded-tr-sm p-3 sm:p-4 max-w-[85%] sm:max-w-[80%]">
          <p className="text-xs sm:text-sm text-white">
            Can you help me understand quantum computing?
          </p>
        </div>
        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 text-white text-[10px] sm:text-xs font-bold">
          You
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5 }}
        className="flex items-start gap-2 sm:gap-3"
      >
        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </div>
        <div className="flex-1 bg-secondary/50 rounded-xl sm:rounded-2xl rounded-tl-sm p-3 sm:p-4 border border-border">
          <div className="flex items-center gap-1.5 sm:gap-2 mb-2">
            <Brain className="w-3 h-3 sm:w-4 sm:h-4 text-primary" />
            <span className="text-[10px] sm:text-xs text-primary font-medium">Thinking...</span>
          </div>
          <div className="space-y-1.5 sm:space-y-2">
            <div className="h-1.5 sm:h-2 bg-foreground/10 rounded-full w-full animate-pulse" />
            <div className="h-1.5 sm:h-2 bg-foreground/10 rounded-full w-4/5 animate-pulse" />
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Highlight Mockup Component
const HighlightMockup = () => {
  const [selectedColor, setSelectedColor] = useState('bg-yellow-400/40');
  const [showPicker, setShowPicker] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });

  const colors = [
    { name: "Yellow", class: "bg-yellow-400/40", border: "border-yellow-400", hex: "rgb(250, 204, 21)" },
    { name: "Blue", class: "bg-blue-400/40", border: "border-blue-400", hex: "rgb(96, 165, 250)" },
    { name: "Pink", class: "bg-pink-400/40", border: "border-pink-400", hex: "rgb(244, 114, 182)" },
    { name: "Green", class: "bg-green-400/40", border: "border-green-400", hex: "rgb(74, 222, 128)" },
    { name: "Purple", class: "bg-purple-400/40", border: "border-purple-400", hex: "rgb(192, 132, 252)" },
  ];

  const handleTextSelect = (e: React.MouseEvent, text: string) => {
    const selection = window.getSelection();
    const selectedStr = selection?.toString();
    
    if (selectedStr && selectedStr.length > 0) {
      setSelectedText(selectedStr);
      const rect = e.currentTarget.getBoundingClientRect();
      setPopupPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top - 50 });
      setShowPicker(true);
    }
  };

  const applyHighlight = (color: typeof colors[0]) => {
    setSelectedColor(color.class);
    setShowPicker(false);
  };

  return (
    <div className="h-full min-h-[300px] sm:min-h-[350px] md:min-h-[400px] space-y-3 sm:space-y-4 relative">
      {/* Document with highlights */}
      <div 
        className="bg-background/50 backdrop-blur-sm rounded-lg sm:rounded-xl border border-border p-3 sm:p-4 md:p-6 space-y-3 sm:space-y-4 relative group"
        onMouseUp={(e) => handleTextSelect(e, '')}
      >
        {/* Pin Indicator */}
        <motion.div
          initial={{ scale: 0, rotate: -45 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
          className="absolute -top-3 -right-3 z-10 hidden sm:block"
        >
          <div className="relative group">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-yellow-500 via-orange-500 to-yellow-600 flex items-center justify-center shadow-xl border-2 border-white/20">
              <Highlighter className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 }}
              className="absolute -bottom-16 right-0 whitespace-nowrap"
            >
              <motion.div
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="px-4 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-xs font-bold rounded-xl shadow-lg border border-white/30"
              >
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3 h-3" />
                    Try it!
                  </div>
                  <div className="text-[10px] font-normal opacity-90">
                    Select text to highlight
                  </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </motion.div>

        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold">Research Document</h3>
          <div className="flex items-center gap-2 text-[10px] sm:text-xs text-muted-foreground hidden xs:flex">
            Select text to highlight
          </div>
        </div>

        <p className="text-xs sm:text-sm text-foreground/80 leading-relaxed select-text">
          Artificial intelligence is transforming how we work and create. With tools like PRISM, anyone can harness AI power for enhanced productivity and creative workflows. The future of work is collaborative intelligence, where humans and AI work together seamlessly.
        </p>

        {/* Color Picker Popup */}
        {showPicker && selectedText && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            style={{
              position: 'absolute',
              left: popupPosition.x,
              top: popupPosition.y,
              zIndex: 50,
            }}
            className="flex gap-1.5 sm:gap-2 p-2 sm:p-3 bg-background/95 backdrop-blur-xl border-2 border-border rounded-lg sm:rounded-xl shadow-2xl"
          >
            {colors.map((color) => (
              <motion.button
                key={color.name}
                whileHover={{ scale: 1.2, y: -3 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => applyHighlight(color)}
                className={`w-7 h-7 sm:w-9 sm:h-9 rounded-full ${color.class} border-2 ${
                  selectedColor === color.class ? `${color.border} ring-2 ring-offset-2 ring-offset-background` : 'border-border/50'
                } transition-all cursor-pointer shadow-lg hover:shadow-xl`}
                title={`Highlight with ${color.name}`}
                style={{ backgroundColor: color.hex }}
              />
            ))}
          </motion.div>
        )}
      </div>

      {/* AI Insight panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="p-3 sm:p-4 md:p-5 bg-gradient-to-br from-primary/10 to-purple-500/10 rounded-lg sm:rounded-xl border border-primary/20 backdrop-blur-sm"
      >
        <div className="flex items-start gap-2 sm:gap-3">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div className="flex-1 space-y-1.5 sm:space-y-2">
            <h4 className="text-xs sm:text-sm font-semibold text-foreground">AI Summary</h4>
            <p className="text-[10px] sm:text-xs text-muted-foreground leading-relaxed">
              This passage discusses AI democratization and its impact on productivity. Current highlight: {selectedColor.includes('yellow') ? 'Yellow' : selectedColor.includes('blue') ? 'Blue' : selectedColor.includes('pink') ? 'Pink' : selectedColor.includes('green') ? 'Green' : 'Purple'}
            </p>
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 pt-1.5 sm:pt-2">
              <div className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded text-[10px] sm:text-xs font-medium">
                Key Concept
              </div>
              <div className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded text-[10px] sm:text-xs font-medium">
                Technology
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Mini Agent Mockup Component
const MiniAgentMockup = () => {
  const [mainMessages, setMainMessages] = useState([
    { id: 1, type: 'ai', text: "Hello! I'm your PRISM assistant. How can I help you today?" },
    { id: 2, type: 'user', text: "Can you help me with my research on quantum computing?" },
    { id: 3, type: 'ai', text: "Absolutely! I'd be happy to help with your quantum computing research. What specific aspect would you like to explore?" },
  ]);
  const [miniMessages, setMiniMessages] = useState<Array<{ id: number; type: string; text: string }>>([]);
  const [mainInput, setMainInput] = useState('');
  const [miniInput, setMiniInput] = useState('');
  const [selectedText, setSelectedText] = useState('');
  const [showPopup, setShowPopup] = useState(false);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });
  const [miniAgentOpen, setMiniAgentOpen] = useState(false);
  const [miniAgentName, setMiniAgentName] = useState('Research Helper');
  const [showNameInput, setShowNameInput] = useState(false);

  const handleTextSelect = (e: React.MouseEvent) => {
    const selection = window.getSelection();
    const selectedStr = selection?.toString();
    
    if (selectedStr && selectedStr.length > 3) {
      setSelectedText(selectedStr);
      const rect = e.currentTarget.getBoundingClientRect();
      setPopupPosition({ 
        x: e.clientX - rect.left, 
        y: e.clientY - rect.top - 60 
      });
      setShowPopup(true);
    }
  };

  const openMiniAgent = () => {
    if (selectedText) {
      setMiniAgentOpen(true);
      setMiniMessages([
        { id: Date.now(), type: 'user', text: selectedText },
        { id: Date.now() + 1, type: 'ai', text: `I can help you explore "${selectedText.substring(0, 30)}..." in more detail. What would you like to know?` }
      ]);
    }
    setShowPopup(false);
  };

  const handleMainSend = () => {
    if (!mainInput.trim()) return;
    
    const userMessage = { id: Date.now(), type: 'user', text: mainInput };
    setMainMessages(prev => [...prev, userMessage]);
    setMainInput('');

    setTimeout(() => {
      const responses = [
        "That's fascinating! Quantum computing has incredible potential.",
        "Let me break that down for you with some key insights.",
        "Great question! Here's what you should know about that.",
      ];
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        text: responses[Math.floor(Math.random() * responses.length)],
      };
      setMainMessages(prev => [...prev, aiMessage]);
    }, 1000);
  };

  const handleMiniSend = () => {
    if (!miniInput.trim()) return;
    
    const userMessage = { id: Date.now(), type: 'user', text: miniInput };
    setMiniMessages(prev => [...prev, userMessage]);
    setMiniInput('');

    setTimeout(() => {
      const responses = [
        "Let me provide more specific details about that aspect.",
        "Based on your main conversation, here's additional context...",
        "I'm analyzing that in relation to your broader research.",
      ];
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        text: responses[Math.floor(Math.random() * responses.length)],
      };
      setMiniMessages(prev => [...prev, aiMessage]);
    }, 1000);
  };

  return (
    <div className="h-full min-h-[300px] sm:min-h-[380px] md:min-h-[450px] p-2 sm:p-3 md:p-4 relative">
      <div className="flex gap-2 sm:gap-3 h-[300px] sm:h-[380px] md:h-[450px] relative">
        {/* Pin Indicator */}
        {!miniAgentOpen && (
          <motion.div
            initial={{ scale: 0, rotate: -45 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
            className="absolute -top-4 left-1/3 z-20 hidden sm:block"
          >
            <div className="relative group">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-green-500 via-emerald-500 to-green-600 flex items-center justify-center shadow-xl border-2 border-white/20">
                <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 }}
                className="absolute -bottom-16 left-1/2 -translate-x-1/2 whitespace-nowrap"
              >
                <motion.div
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg border border-white/30"
                >
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-3 h-3" />
                      Try it!
                    </div>
                    <div className="text-[10px] font-normal opacity-90">
                      Select text to create mini-agent
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            </div>
          </motion.div>
        )}

        {/* Main Chat */}
        <div 
          className={`transition-all duration-300 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 backdrop-blur-sm rounded-xl border border-blue-500/20 flex flex-col ${
            miniAgentOpen ? 'flex-[2]' : 'flex-1'
          }`}
          onMouseUp={handleTextSelect}
        >
          {/* Header */}
          <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-blue-500/20 flex items-center justify-between">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
              </div>
              <div>
                <div className="font-semibold text-xs sm:text-sm">PRISM</div>
                <div className="text-[10px] sm:text-xs text-muted-foreground">Main Chat</div>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-2 sm:p-3 md:p-4 space-y-2 sm:space-y-3">
            {mainMessages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] sm:max-w-[75%] rounded-xl sm:rounded-2xl px-3 sm:px-4 py-1.5 sm:py-2 ${
                    msg.type === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white'
                      : 'bg-secondary/50 text-foreground'
                  }`}
                >
                  <p className="text-[11px] sm:text-sm select-text">{msg.text}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Input */}
          <div className="p-2 sm:p-3 border-t border-blue-500/20">
            <div className="flex gap-1.5 sm:gap-2">
              <input
                type="text"
                value={mainInput}
                onChange={(e) => setMainInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleMainSend()}
                placeholder="Message PRISM..."
                className="flex-1 px-2 sm:px-4 py-1.5 sm:py-2 bg-background/50 border border-border rounded-md sm:rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <button
                onClick={handleMainSend}
                className="p-1.5 sm:p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-md sm:rounded-lg hover:opacity-90 transition-opacity"
              >
                <Send className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
              </button>
            </div>
          </div>
        </div>

        {/* Mini-Agent Panel */}
        <motion.div
          initial={false}
          animate={{
            width: miniAgentOpen ? (window.innerWidth < 640 ? 200 : 320) : 0,
            opacity: miniAgentOpen ? 1 : 0,
            x: miniAgentOpen ? 0 : 20,
          }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="bg-gradient-to-br from-green-500/5 to-emerald-500/5 backdrop-blur-sm rounded-lg sm:rounded-xl border border-green-500/20 flex flex-col overflow-hidden"
        >
          {miniAgentOpen && (
            <>
              {/* Header */}
              <div className="px-4 py-3 border-b border-green-500/20 flex items-center justify-between">
                <div className="flex items-center gap-2 flex-1">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  {showNameInput ? (
                    <input
                      type="text"
                      value={miniAgentName}
                      onChange={(e) => setMiniAgentName(e.target.value)}
                      onBlur={() => setShowNameInput(false)}
                      onKeyPress={(e) => e.key === 'Enter' && setShowNameInput(false)}
                      className="flex-1 text-xs font-semibold bg-transparent border-b border-green-500/30 focus:outline-none"
                      autoFocus
                    />
                  ) : (
                    <div onClick={() => setShowNameInput(true)} className="cursor-pointer">
                      <div className="font-semibold text-xs">{miniAgentName}</div>
                      <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        Active
                      </div>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setMiniAgentOpen(false)}
                  className="p-1 hover:bg-red-500/20 rounded transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Synced indicator */}
              <div className="px-2 sm:px-3 py-1.5 sm:py-2 bg-green-500/10 border-b border-green-500/20">
                <div className="text-[9px] sm:text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1 sm:gap-1.5">
                  <div className="w-1 h-1 rounded-full bg-green-500" />
                  <span className="hidden xs:inline">Context from main chat</span>
                  <span className="xs:hidden">Synced</span>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-2 sm:p-3 space-y-1.5 sm:space-y-2">
                {miniMessages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`text-[10px] sm:text-xs p-2 sm:p-2.5 rounded-md sm:rounded-lg ${
                      msg.type === 'user'
                        ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 ml-auto max-w-[90%] sm:max-w-[85%]'
                        : 'bg-secondary/40 max-w-[90%] sm:max-w-[85%]'
                    }`}
                  >
                    {msg.text}
                  </motion.div>
                ))}
              </div>

              {/* Input */}
              <div className="p-1.5 sm:p-2 border-t border-green-500/20">
                <div className="flex gap-1 sm:gap-1.5">
                  <input
                    type="text"
                    value={miniInput}
                    onChange={(e) => setMiniInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleMiniSend()}
                    placeholder="Ask..."
                    className="flex-1 px-1.5 sm:px-2 py-1 sm:py-1.5 bg-background/50 border border-border rounded text-[10px] sm:text-[11px] focus:outline-none focus:ring-1 focus:ring-green-500/50"
                  />
                  <button
                    onClick={handleMiniSend}
                    className="p-1 sm:p-1.5 bg-gradient-to-r from-green-500 to-emerald-500 rounded hover:opacity-90 transition-opacity"
                  >
                    <Send className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
                  </button>
                </div>
              </div>
            </>
          )}
        </motion.div>
      </div>

      {/* Selection Popup */}
      {showPopup && selectedText && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9 }}
          style={{
            position: 'absolute',
            left: popupPosition.x,
            top: popupPosition.y,
            zIndex: 100,
          }}
          className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-lg shadow-2xl border-2 border-green-400"
        >
          <button
            onClick={openMiniAgent}
            className="flex items-center gap-2 text-sm font-medium hover:scale-105 transition-transform"
          >
            <Bot className="w-4 h-4" />
            Create Mini-Agent
          </button>
        </motion.div>
      )}
    </div>
  );
};

// Graph Mockup Component
const GraphMockup = () => {
  // Perfect circular arrangement around center
  const [nodePositions, setNodePositions] = useState([
    { id: 1, x: 50, y: 50, label: "You", color: "from-blue-500 to-cyan-500", size: "large", isUser: true },
    { id: 2, x: 50, y: 15, label: "Likes", color: "from-pink-500 to-rose-500", size: "medium", isUser: false }, // Top
    { id: 3, x: 80, y: 30, label: "Love", color: "from-red-500 to-pink-500", size: "medium", isUser: false }, // Top-right
    { id: 4, x: 80, y: 70, label: "Share", color: "from-green-500 to-emerald-500", size: "medium", isUser: false }, // Bottom-right
    { id: 5, x: 50, y: 85, label: "Comment", color: "from-purple-500 to-indigo-500", size: "medium", isUser: false }, // Bottom
    { id: 6, x: 20, y: 70, label: "Save", color: "from-yellow-500 to-orange-500", size: "medium", isUser: false }, // Bottom-left
    { id: 7, x: 20, y: 30, label: "Follow", color: "from-indigo-500 to-purple-500", size: "medium", isUser: false }, // Top-left
  ]);

  const [draggedNode, setDraggedNode] = useState<number | null>(null);

  // Create web of connections - center hub + hexagonal web
  const connections = [
    // Center to all nodes (hub pattern)
    ...nodePositions.filter(node => !node.isUser).map(node => ({ from: 1, to: node.id, type: 'hub' as const })),
    // Hexagonal web connections between outer nodes
    { from: 2, to: 3, type: 'web' as const }, // Likes to Love
    { from: 3, to: 4, type: 'web' as const }, // Love to Share
    { from: 4, to: 5, type: 'web' as const }, // Share to Comment
    { from: 5, to: 6, type: 'web' as const }, // Comment to Save
    { from: 6, to: 7, type: 'web' as const }, // Save to Follow
    { from: 7, to: 2, type: 'web' as const }, // Follow to Likes (complete circle)
    // Cross connections for stronger web
    { from: 2, to: 5, type: 'cross' as const }, // Top to Bottom
    { from: 3, to: 6, type: 'cross' as const }, // TR to BL
    { from: 4, to: 7, type: 'cross' as const }, // BR to TL
  ];

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
    <div className="space-y-2 sm:space-y-3">
      <div 
        className="relative h-full min-h-[280px] sm:min-h-[340px] md:min-h-[400px] flex items-center justify-center bg-gradient-to-br from-background/50 to-secondary/20 rounded-lg sm:rounded-xl border border-border overflow-hidden select-none"
        onMouseMove={(e) => draggedNode !== null && handleNodeDrag(draggedNode, e)}
        onMouseUp={() => setDraggedNode(null)}
        onMouseLeave={() => setDraggedNode(null)}
      >
        {/* Pin Indicator */}
        <motion.div
          initial={{ scale: 0, rotate: -45 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
          className="absolute -top-3 -right-3 z-50 hidden sm:block"
        >
          <div className="relative group">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-purple-500 via-pink-500 to-purple-600 flex items-center justify-center shadow-xl border-2 border-white/20">
              <Network className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 }}
              className="absolute -bottom-16 right-0 whitespace-nowrap"
            >
              <motion.div
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-bold rounded-xl shadow-lg border border-white/30"
              >
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3 h-3" />
                    Try it!
                  </div>
                  <div className="text-[10px] font-normal opacity-90">
                    Drag nodes to explore
                  </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </motion.div>

        {/* Center container */}
        <div className="relative w-full h-full">
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {/* Animated connections */}
            {connections.map((conn, idx) => {
              const fromNode = nodePositions.find(n => n.id === conn.from);
              const toNode = nodePositions.find(n => n.id === conn.to);
              if (!fromNode || !toNode) return null;
              
              const isHub = conn.type === 'hub';
              const isWeb = conn.type === 'web';
              const isCross = conn.type === 'cross';
              
              return (
                <g key={`${conn.from}-${conn.to}`}>
                  {/* Glow effect */}
                  <motion.line
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: isHub ? 0.3 : isCross ? 0.15 : 0.2 }}
                    transition={{ delay: 0.3 + idx * 0.04, duration: 0.8, ease: "easeOut" }}
                    x1={`${fromNode.x}%`}
                    y1={`${fromNode.y}%`}
                    x2={`${toNode.x}%`}
                    y2={`${toNode.y}%`}
                    stroke={isHub ? "url(#gradient-hub-glow)" : "url(#gradient-web-glow)"}
                    strokeWidth={isHub ? "8" : isCross ? "4" : "5"}
                    strokeLinecap="round"
                  />
                  {/* Main line */}
                  <motion.line
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: isHub ? 0.8 : isCross ? 0.4 : 0.6 }}
                    transition={{ delay: 0.3 + idx * 0.04, duration: 0.8, ease: "easeOut" }}
                    x1={`${fromNode.x}%`}
                    y1={`${fromNode.y}%`}
                    x2={`${toNode.x}%`}
                    y2={`${toNode.y}%`}
                    stroke={isHub ? "url(#gradient-hub)" : isWeb ? "url(#gradient-web)" : "url(#gradient-cross)"}
                    strokeWidth={isHub ? "3" : isCross ? "1.5" : "2"}
                    strokeLinecap="round"
                  />
                </g>
              );
            })}
            
            {/* Gradient definitions */}
            <defs>
              {/* Hub connections (center to nodes) */}
              <linearGradient id="gradient-hub" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgb(59, 130, 246)" stopOpacity="0.95" />
                <stop offset="50%" stopColor="rgb(139, 92, 246)" stopOpacity="0.95" />
                <stop offset="100%" stopColor="rgb(236, 72, 153)" stopOpacity="0.95" />
              </linearGradient>
              <linearGradient id="gradient-hub-glow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgb(59, 130, 246)" stopOpacity="0.5" />
                <stop offset="50%" stopColor="rgb(139, 92, 246)" stopOpacity="0.5" />
                <stop offset="100%" stopColor="rgb(236, 72, 153)" stopOpacity="0.5" />
              </linearGradient>
              {/* Web connections (between outer nodes) */}
              <linearGradient id="gradient-web" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgb(139, 92, 246)" stopOpacity="0.75" />
                <stop offset="100%" stopColor="rgb(236, 72, 153)" stopOpacity="0.75" />
              </linearGradient>
              <linearGradient id="gradient-web-glow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgb(139, 92, 246)" stopOpacity="0.4" />
                <stop offset="100%" stopColor="rgb(236, 72, 153)" stopOpacity="0.4" />
              </linearGradient>
              {/* Cross connections */}
              <linearGradient id="gradient-cross" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgb(168, 85, 247)" stopOpacity="0.5" />
                <stop offset="100%" stopColor="rgb(244, 114, 182)" stopOpacity="0.5" />
              </linearGradient>
            </defs>
          </svg>

          {/* Draggable Nodes */}
          {nodePositions.map((node, index) => {
            const sizeClasses = {
              large: "w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20",
              medium: "w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16",
              small: "w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12",
            };
            return (
              <motion.div
                key={node.id}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + index * 0.1, type: "spring", bounce: 0.5 }}
                whileHover={{ scale: 1.15, zIndex: 10 }}
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
                <div className={`absolute inset-0 bg-gradient-to-br ${node.color} opacity-30 rounded-full blur-lg group-hover:opacity-70 group-hover:blur-2xl transition-all`} />
                
                {/* Node circle */}
                <div className={`relative ${sizeClasses[node.size as keyof typeof sizeClasses]} rounded-full bg-gradient-to-br ${node.color} flex items-center justify-center border-3 border-background shadow-xl group-hover:shadow-2xl transition-all ${
                  node.isUser ? 'ring-4 ring-blue-500/20' : ''
                }`}>
                  {node.isUser ? (
                    <User className="w-1/2 h-1/2 text-white" />
                  ) : (
                    <Network className="w-1/2 h-1/2 text-white" />
                  )}
                  
                  {/* Pulse animation */}
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-current opacity-75"
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [0.6, 0, 0.6],
                    }}
                    transition={{
                      duration: 3,
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
                  className="absolute -bottom-6 sm:-bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap pointer-events-none"
                >
                  <div className={`px-2 sm:px-3 py-1 sm:py-1.5 bg-background/95 backdrop-blur-sm rounded-full border text-[10px] sm:text-xs font-semibold shadow-lg ${
                    node.isUser ? 'border-blue-500/50 bg-blue-500/10' : 'border-border'
                  }`}>
                    {node.label}
                  </div>
                </motion.div>

                {/* Connection indicator for non-user nodes */}
                {!node.isUser && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.6 + index * 0.1, type: "spring" }}
                    className="absolute -top-0.5 sm:-top-1 -right-0.5 sm:-right-1 w-4 h-4 sm:w-6 sm:h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 border-2 border-background flex items-center justify-center shadow-lg pointer-events-none"
                  >
                    <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-white" />
                  </motion.div>
                )}
              </div>
            </motion.div>
          );
        })}
        </div>
      </div>
    </div>
  );
};

// Team Showcase Component
const TeamShowcase = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [showImagePopup, setShowImagePopup] = useState(false);

  const teamMembers = useMemo(() => [
    {
      id: 1,
      name: "B. Vamshi",
      role: "AI & Web Developer",
      image: "/team/vamshi.jpg",
      bio: "Building intelligent AI solutions and modern web applications. Specializing in machine learning integration and full-stack development.",
      skills: ["AI/ML", "React", "Python", "Node.js", "TypeScript"],
      socials: { 
        linkedin: "https://www.linkedin.com/in/bukya-vamshi-b27a38348", 
        github: "https://github.com/rathodvamshi", 
        instagram: "https://www.instagram.com/_rathod_369/" 
      },
    },
    {
      id: 2,
      name: "R. Lakshmi Prasanna",
      role: "Web Developer",
      image: "/team/prasanna.jpg",
      bio: "Crafting responsive and visually stunning websites with clean code. Focused on creating seamless user experiences across all devices.",
      skills: ["HTML/CSS", "JavaScript", "React", "Tailwind", "Bootstrap"],
      socials: { 
        github: "https://github.com/LakshmiPrasanna197",
        instagram: "https://www.instagram.com/prasanna__2728/" 
      },
    },
    {
      id: 3,
      name: "M. Yashwanth",
      role: "Web Developer",
      image: "/team/yashwanth.jpg",
      bio: "Developing dynamic and interactive web applications. Passionate about writing efficient code and building user-friendly interfaces.",
      skills: ["JavaScript", "React", "CSS", "Git", "REST APIs"],
      socials: { 
        github: "https://github.com/Malothu-yash", 
        instagram: "https://www.instagram.com/__yashwanth__10" 
      },
    },
    {
      id: 4,
      name: "M. Shruthi",
      role: "UI/UX Designer",
      image: "/team/shruthi.jpg",
      bio: "Designing intuitive user experiences and beautiful interfaces. Transforming complex ideas into elegant, user-centered designs.",
      skills: ["Figma", "UI Design", "Prototyping", "Wireframing", "User Research"],
      socials: { 
        linkedin: "https://www.linkedin.com/in/shruthi-masani-bba518374", 
        github: "https://github.com/Shruthi250705",
        instagram: "https://www.instagram.com/shruthss__" 
      },
    },
    {
      id: 5,
      name: "SatyaDeva",
      role: "Backend Developer",
      image: "/team/satyadeva.jpg",
      bio: "Architecting robust server-side solutions and scalable APIs. Expert in database design and backend system optimization.",
      skills: ["Python", "Django", "PostgreSQL", "REST APIs", "Docker"],
      socials: { 
        linkedin: "https://linkedin.com/in/satya-deva-553401321", 
        github: "https://github.com/satyadeva-0406", 
        instagram: "https://www.instagram.com/satyadeva0406" 
      },
    },
  ], []);

  const iconMap = useMemo(() => ({
    linkedin: Linkedin,
    github: Github,
    instagram: Instagram,
  }), []);

  const platformNames: Record<string, string> = {
    linkedin: "LinkedIn",
    github: "GitHub",
    instagram: "Instagram"
  };

  // Brand colors for social media icons
  const socialColors: Record<string, string> = {
    linkedin: "hover:bg-[#0A66C2] hover:text-white hover:border-[#0A66C2]",
    github: "hover:bg-[#333] hover:text-white hover:border-[#333] dark:hover:bg-white dark:hover:text-[#333] dark:hover:border-white",
    instagram: "hover:bg-gradient-to-br hover:from-[#833AB4] hover:via-[#FD1D1D] hover:to-[#F77737] hover:text-white hover:border-[#E4405F]"
  };

  // Auto-rotate every 3 seconds (pauses on hover or when popup is open)
  useEffect(() => {
    if (isHovered || showImagePopup) return;
    
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % teamMembers.length);
    }, 3000);
    
    return () => clearInterval(interval);
  }, [isHovered, showImagePopup, teamMembers.length]);

  const handlePrev = useCallback(() => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : teamMembers.length - 1));
  }, [teamMembers.length]);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % teamMembers.length);
  }, [teamMembers.length]);

  const currentMember = teamMembers[currentIndex];

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
      className="mt-16 sm:mt-24 md:mt-32 relative px-2"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Image Only Popup */}
      <AnimatePresence>
        {showImagePopup && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowImagePopup(false)}
              className="fixed inset-0 bg-black/80 backdrop-blur-md z-50"
            />
            
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={() => setShowImagePopup(false)}
            >
              <motion.div
                onClick={(e) => e.stopPropagation()}
                className="relative"
              >
                {/* Close button */}
                <button
                  onClick={() => setShowImagePopup(false)}
                  className="absolute -top-2 -right-2 sm:-top-3 sm:-right-3 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-card border border-border hover:border-primary/50 flex items-center justify-center text-muted-foreground hover:text-foreground transition-all z-10 shadow-lg"
                >
                  <X className="w-4 h-4 sm:w-5 sm:h-5" />
                </button>

                {/* Profile Image */}
                <div className="relative">
                  <div className="absolute -inset-1.5 sm:-inset-2 rounded-full bg-gradient-to-br from-primary via-primary/50 to-primary/20 animate-pulse" />
                  {currentMember.image.includes('placeholder') ? (
                    <div className="relative w-48 h-48 xs:w-56 xs:h-56 sm:w-64 sm:h-64 md:w-80 md:h-80 rounded-full bg-card border-2 sm:border-4 border-primary/30 flex items-center justify-center shadow-2xl">
                      <User className="w-16 h-16 xs:w-20 xs:h-20 sm:w-24 sm:h-24 text-muted-foreground" />
                    </div>
                  ) : (
                    <img
                      src={currentMember.image}
                      alt={currentMember.name}
                      className="relative w-48 h-48 xs:w-56 xs:h-56 sm:w-64 sm:h-64 md:w-80 md:h-80 rounded-full object-cover object-top border-2 sm:border-4 border-primary/30 shadow-2xl"
                    />
                  )}
                </div>

                {/* Name below image */}
                <div className="text-center mt-4 sm:mt-6">
                  <h3 className="text-lg xs:text-xl sm:text-2xl font-bold text-white">{currentMember.name}</h3>
                  <p className="text-sm sm:text-base text-primary font-medium mt-1">{currentMember.role}</p>
                </div>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Section Header */}
      <div className="text-center mb-8 sm:mb-10 md:mb-12 space-y-3 sm:space-y-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.5, y: 30 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, type: "spring", stiffness: 200, damping: 15 }}
          className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 bg-primary/5 rounded-full border border-primary/10"
        >
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <Users className="w-3 h-3 sm:w-4 sm:h-4 text-primary" />
          </motion.div>
          <span className="text-xs sm:text-sm font-medium text-primary">Meet The Team</span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
          className="text-2xl xs:text-3xl sm:text-4xl md:text-5xl font-bold text-foreground leading-tight"
        >
          Built By{" "}
          <motion.span 
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-primary inline-block"
          >
            Passionate Innovators
          </motion.span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-sm sm:text-base md:text-lg text-muted-foreground max-w-xl mx-auto px-4"
        >
          A dedicated team building the future of AI.
        </motion.p>
      </div>

      {/* Profile Display */}
      <motion.div 
        initial={{ opacity: 0, y: 60, scale: 0.95 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
        className="relative max-w-4xl mx-auto px-2 sm:px-4"
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
            className="flex flex-col md:flex-row items-center gap-4 sm:gap-6 md:gap-8 p-4 sm:p-6 md:p-8 bg-card/50 backdrop-blur-md border border-border/50 rounded-2xl sm:rounded-3xl"
          >
            {/* Left - Profile Image (Clickable) */}
            <div className="flex flex-col items-center shrink-0">
              <motion.button
                onClick={() => setShowImagePopup(true)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="relative mb-3 sm:mb-4 cursor-pointer group"
              >
                <div className="absolute -inset-1.5 sm:-inset-2 rounded-full bg-primary/20 animate-pulse group-hover:bg-primary/30 transition-colors" />
                {currentMember.image.includes('placeholder') ? (
                  <div className="relative w-24 h-24 xs:w-28 xs:h-28 sm:w-32 sm:h-32 md:w-40 md:h-40 rounded-full bg-card border-3 sm:border-4 border-primary/30 group-hover:border-primary/50 flex items-center justify-center transition-all duration-300">
                    <User className="w-10 h-10 xs:w-12 xs:h-12 sm:w-14 sm:h-14 md:w-16 md:h-16 text-muted-foreground" />
                  </div>
                ) : (
                  <img
                    src={currentMember.image}
                    alt={currentMember.name}
                    className="relative w-24 h-24 xs:w-28 xs:h-28 sm:w-32 sm:h-32 md:w-40 md:h-40 rounded-full object-cover object-top border-3 sm:border-4 border-primary/30 group-hover:border-primary/50 transition-all duration-300"
                  />
                )}
                {/* Hover overlay */}
                <div className="absolute inset-0 rounded-full bg-black/0 group-hover:bg-black/20 transition-all duration-300 flex items-center justify-center">
                  <span className="text-transparent group-hover:text-white text-xs sm:text-sm font-medium transition-all duration-300">View</span>
                </div>
              </motion.button>
              <h3 className="text-base xs:text-lg sm:text-xl font-bold text-foreground text-center">{currentMember.name}</h3>
              <p className="text-xs xs:text-sm sm:text-base text-primary font-medium text-center">{currentMember.role}</p>
            </div>

            {/* Right - Information */}
            <div className="flex-1 min-w-0 w-full md:w-auto">
              <div className="mb-4 sm:mb-5">
                <h4 className="text-xs sm:text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 sm:mb-2">About</h4>
                <p className="text-sm sm:text-base text-foreground leading-relaxed">{currentMember.bio}</p>
              </div>

              <div className="mb-4 sm:mb-5">
                <h4 className="text-xs sm:text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2 sm:mb-3">Skills</h4>
                <div className="flex flex-wrap gap-1.5 sm:gap-2">
                  {currentMember.skills.map((skill) => (
                    <span
                      key={skill}
                      className="px-2 sm:px-3 py-0.5 sm:py-1 text-xs sm:text-sm bg-primary/10 text-primary rounded-full border border-primary/20"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs sm:text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2 sm:mb-3">Connect</h4>
                <div className="flex flex-wrap gap-1.5 sm:gap-2">
                  {Object.entries(currentMember.socials).map(([platform, link]) => {
                    const Icon = iconMap[platform as keyof typeof iconMap];
                    if (!Icon) return null;
                    return (
                      <a
                        key={platform}
                        href={link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-muted/50 rounded-lg text-muted-foreground transition-all duration-300 border border-border ${socialColors[platform]}`}
                      >
                        <Icon className="w-3 h-3 sm:w-4 sm:h-4" />
                        <span className="text-xs sm:text-sm font-medium">{platformNames[platform]}</span>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex items-center justify-center gap-3 sm:gap-4 md:gap-6 mt-4 sm:mt-6"
        >
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={handlePrev}
            className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-card/80 border border-border hover:border-primary/50 flex items-center justify-center text-muted-foreground hover:text-primary transition-all duration-200"
            aria-label="Previous member"
          >
            <ChevronLeft className="w-4 h-4 sm:w-5 sm:h-5" />
          </motion.button>
          
          <div className="flex items-center gap-1.5 sm:gap-2">
            {teamMembers.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentIndex(index)}
                aria-label={`Go to member ${index + 1}`}
                className={`h-1.5 sm:h-2 rounded-full transition-all duration-300 ${
                  index === currentIndex 
                    ? 'w-6 sm:w-8 bg-primary' 
                    : 'w-1.5 sm:w-2 bg-muted-foreground/20 hover:bg-muted-foreground/40'
                }`}
              />
            ))}
          </div>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleNext}
            className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-card/80 border border-border hover:border-primary/50 flex items-center justify-center text-muted-foreground hover:text-primary transition-all duration-200"
            aria-label="Next member"
          >
            <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5" />
          </motion.button>
        </motion.div>
      </motion.div>
    </motion.div>
  );
};

