import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { useRef, useState, useEffect } from "react";
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
    <section ref={containerRef} className="relative py-24 overflow-hidden">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16 space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full border border-primary/20 mb-4">
            <Play className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-primary">Live Prototypes</span>
          </div>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground">
            Experience PRISM
            <span className="block bg-gradient-to-r from-primary via-purple-500 to-pink-500 text-transparent bg-clip-text">
              In Action
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Interact with live demonstrations of PRISM's core features. See how AI transforms your workflow.
          </p>
        </motion.div>

        {/* Feature Selection Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap justify-center gap-4 mb-16"
        >
          {features.map((feature) => (
            <motion.button
              key={feature.id}
              onClick={() => setActiveTab(feature.id)}
              whileHover={{ scale: 1.05, y: -3 }}
              whileTap={{ scale: 0.98 }}
              className={`relative px-6 py-4 rounded-2xl border-2 transition-all duration-300 ${
                activeTab === feature.id
                  ? `${feature.bgColor} ${feature.borderColor} shadow-lg shadow-${feature.id}-500/20`
                  : "bg-card/50 border-border hover:border-border/80"
              }`}
            >
              {activeTab === feature.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-gradient-to-br from-background/10 to-background/5 rounded-2xl"
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

        {/* Built By Team Section */}
        <TeamShowcase />
      </div>
    </section>
  );
};

// Chat Mockup Component
const ChatMockup = () => {
  return (
    <div className="space-y-4 relative">
      {/* Pin Indicator */}
      <motion.div
        initial={{ scale: 0, rotate: -45 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
        className="absolute -top-2 -right-2 z-10"
      >
        <div className="relative group">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 via-cyan-500 to-blue-600 flex items-center justify-center shadow-xl border-2 border-white/20">
            <MessageSquare className="w-6 h-6 text-white" />
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
        className="flex items-start gap-3"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 bg-secondary/50 rounded-2xl rounded-tl-sm p-4 border border-border">
          <p className="text-sm text-foreground">
            Hello! I'm your PRISM AI assistant. I can help you with research, writing, coding, and much more. What would you like to work on today?
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="flex items-start gap-3 justify-end"
      >
        <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl rounded-tr-sm p-4 max-w-[80%]">
          <p className="text-sm text-white">
            Can you help me understand quantum computing?
          </p>
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
          You
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
    <div className="h-full min-h-[400px] space-y-4 relative">
      {/* Document with highlights */}
      <div 
        className="bg-background/50 backdrop-blur-sm rounded-xl border border-border p-6 space-y-4 relative group"
        onMouseUp={(e) => handleTextSelect(e, '')}
      >
        {/* Pin Indicator */}
        <motion.div
          initial={{ scale: 0, rotate: -45 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
          className="absolute -top-3 -right-3 z-10"
        >
          <div className="relative group">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-500 via-orange-500 to-yellow-600 flex items-center justify-center shadow-xl border-2 border-white/20">
              <Highlighter className="w-6 h-6 text-white" />
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

        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Research Document</h3>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            Select text to highlight
          </div>
        </div>

        <p className="text-sm text-foreground/80 leading-relaxed select-text">
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
            className="flex gap-2 p-3 bg-background/95 backdrop-blur-xl border-2 border-border rounded-xl shadow-2xl"
          >
            {colors.map((color) => (
              <motion.button
                key={color.name}
                whileHover={{ scale: 1.2, y: -3 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => applyHighlight(color)}
                className={`w-9 h-9 rounded-full ${color.class} border-2 ${
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
        className="p-5 bg-gradient-to-br from-primary/10 to-purple-500/10 rounded-xl border border-primary/20 backdrop-blur-sm"
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 space-y-2">
            <h4 className="text-sm font-semibold text-foreground">AI Summary</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This passage discusses AI democratization and its impact on productivity. Current highlight: {selectedColor.includes('yellow') ? 'Yellow' : selectedColor.includes('blue') ? 'Blue' : selectedColor.includes('pink') ? 'Pink' : selectedColor.includes('green') ? 'Green' : 'Purple'}
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
    <div className="h-full min-h-[450px] p-4 relative">
      <div className="flex gap-3 h-[450px] relative">
        {/* Pin Indicator */}
        {!miniAgentOpen && (
          <motion.div
            initial={{ scale: 0, rotate: -45 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
            className="absolute -top-4 left-1/3 z-20"
          >
            <div className="relative group">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-500 via-emerald-500 to-green-600 flex items-center justify-center shadow-xl border-2 border-white/20">
                <Bot className="w-6 h-6 text-white" />
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
          <div className="px-4 py-3 border-b border-blue-500/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="font-semibold text-sm">PRISM</div>
                <div className="text-xs text-muted-foreground">Main Chat</div>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {mainMessages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2 ${
                    msg.type === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white'
                      : 'bg-secondary/50 text-foreground'
                  }`}
                >
                  <p className="text-sm select-text">{msg.text}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-blue-500/20">
            <div className="flex gap-2">
              <input
                type="text"
                value={mainInput}
                onChange={(e) => setMainInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleMainSend()}
                placeholder="Message PRISM..."
                className="flex-1 px-4 py-2 bg-background/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <button
                onClick={handleMainSend}
                className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg hover:opacity-90 transition-opacity"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </div>

        {/* Mini-Agent Panel */}
        <motion.div
          initial={false}
          animate={{
            width: miniAgentOpen ? 320 : 0,
            opacity: miniAgentOpen ? 1 : 0,
            x: miniAgentOpen ? 0 : 20,
          }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="bg-gradient-to-br from-green-500/5 to-emerald-500/5 backdrop-blur-sm rounded-xl border border-green-500/20 flex flex-col overflow-hidden"
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
              <div className="px-3 py-2 bg-green-500/10 border-b border-green-500/20">
                <div className="text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1.5">
                  <div className="w-1 h-1 rounded-full bg-green-500" />
                  Context from main chat
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {miniMessages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`text-xs p-2.5 rounded-lg ${
                      msg.type === 'user'
                        ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 ml-auto max-w-[85%]'
                        : 'bg-secondary/40 max-w-[85%]'
                    }`}
                  >
                    {msg.text}
                  </motion.div>
                ))}
              </div>

              {/* Input */}
              <div className="p-2 border-t border-green-500/20">
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={miniInput}
                    onChange={(e) => setMiniInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleMiniSend()}
                    placeholder="Ask about selected text..."
                    className="flex-1 px-2 py-1.5 bg-background/50 border border-border rounded text-[11px] focus:outline-none focus:ring-1 focus:ring-green-500/50"
                  />
                  <button
                    onClick={handleMiniSend}
                    className="p-1.5 bg-gradient-to-r from-green-500 to-emerald-500 rounded hover:opacity-90 transition-opacity"
                  >
                    <Send className="w-3 h-3 text-white" />
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
    <div className="space-y-3">
      <div 
        className="relative h-full min-h-[400px] flex items-center justify-center bg-gradient-to-br from-background/50 to-secondary/20 rounded-xl border border-border overflow-hidden select-none"
        onMouseMove={(e) => draggedNode !== null && handleNodeDrag(draggedNode, e)}
        onMouseUp={() => setDraggedNode(null)}
        onMouseLeave={() => setDraggedNode(null)}
      >
        {/* Pin Indicator */}
        <motion.div
          initial={{ scale: 0, rotate: -45 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
          className="absolute -top-3 -right-3 z-50"
        >
          <div className="relative group">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 via-pink-500 to-purple-600 flex items-center justify-center shadow-xl border-2 border-white/20">
              <Network className="w-6 h-6 text-white" />
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
                  className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap pointer-events-none"
                >
                  <div className={`px-3 py-1.5 bg-background/95 backdrop-blur-sm rounded-full border text-xs font-semibold shadow-lg ${
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
                    className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 border-2 border-background flex items-center justify-center shadow-lg pointer-events-none"
                  >
                    <div className="w-2 h-2 rounded-full bg-white" />
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
  const [activeIndex, setActiveIndex] = useState(0);

  const teamMembers = [
    {
      id: 1,
      name: "B. Vamshi",
      role: "Full Stack Developer",
      bio: "Passionate about building scalable AI solutions and creating seamless user experiences.",
      image: "/team/vamshi.jpg",
      gradient: "from-blue-500 via-cyan-500 to-teal-500",
      socials: {
        linkedin: "#",
        github: "#",
        instagram: "#",
      },
    },
    {
      id: 2,
      name: "R. Lakshmi Prasanna",
      role: "AI/ML Engineer",
      bio: "Specializing in machine learning models and natural language processing systems.",
      image: "/api/placeholder/400/400",
      gradient: "from-purple-500 via-pink-500 to-rose-500",
      socials: {
        linkedin: "#",
        github: "#",
        instagram: "#",
      },
    },
    {
      id: 3,
      name: "M. Yashwanth",
      role: "Backend Developer",
      bio: "Expert in building robust APIs and optimizing database performance.",
      image: "/api/placeholder/400/400",
      gradient: "from-green-500 via-emerald-500 to-teal-500",
      socials: {
        linkedin: "#",
        github: "#",
        instagram: "#",
      },
    },
    {
      id: 4,
      name: "M. Shruthi",
      role: "UI/UX Designer",
      bio: "Creating intuitive and beautiful interfaces that users love to interact with.",
      image: "/api/placeholder/400/400",
      gradient: "from-orange-500 via-red-500 to-pink-500",
      socials: {
        linkedin: "#",
        github: "#",
        instagram: "#",
      },
    },
    {
      id: 5,
      name: "SatyaDeva",
      role: "DevOps Engineer",
      bio: "Ensuring smooth deployments and maintaining high-performance infrastructure.",
      image: "/api/placeholder/400/400",
      gradient: "from-indigo-500 via-purple-500 to-pink-500",
      socials: {
        linkedin: "#",
        github: "#",
        instagram: "#",
      },
    },
  ];

  // Auto-rotate through team members
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % teamMembers.length);
    }, 5000); // Change every 5 seconds

    return () => clearInterval(interval);
  }, [teamMembers.length]);

  const activeMember = teamMembers[activeIndex];

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
      className="mt-32 relative"
    >
      {/* Section Header */}
      <div className="text-center mb-20 space-y-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary/10 to-purple-500/10 rounded-full border border-primary/20 mb-4"
        >
          <Users className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-primary">Meet The Team</span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-foreground"
        >
          Built By
          <span className="block bg-gradient-to-r from-primary via-purple-500 to-pink-500 text-transparent bg-clip-text mt-2">
            Passionate Innovators
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto px-4"
        >
          A dedicated team of developers, designers, and engineers working together to build the future of AI.
        </motion.p>
      </div>

      {/* Team Display */}
      <div className="relative max-w-7xl mx-auto px-4">
        <div className="grid lg:grid-cols-[300px,1fr] xl:grid-cols-[320px,1fr] gap-8 lg:gap-12 items-start">
          
          {/* Left side - Vertical Profile Nodes */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative"
          >
            {/* Connecting vertical line */}
            <div className="absolute left-7 top-10 bottom-10 w-0.5 bg-gradient-to-b from-primary/20 via-purple-500/30 to-pink-500/20 hidden sm:block" />
            
            <div className="space-y-4 relative">
              {teamMembers.map((member, index) => (
                <motion.button
                  key={member.id}
                  onClick={() => setActiveIndex(index)}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ x: 8, scale: 1.02 }}
                  className="w-full relative group"
                >
                  {/* Connection line to right */}
                  {activeIndex === index && (
                    <motion.div
                      layoutId="connectionLine"
                      className="absolute left-14 top-1/2 h-0.5 w-8 bg-gradient-to-r from-primary/50 to-transparent hidden lg:block"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ duration: 0.5 }}
                    />
                  )}

                  <div
                    className={`relative flex items-center gap-4 p-3 rounded-2xl border-2 transition-all duration-500 ${
                      activeIndex === index
                        ? `border-transparent shadow-lg bg-gradient-to-r ${member.gradient}`
                        : "border-border/30 bg-card/50 hover:border-border/50 hover:bg-card/70"
                    }`}
                  >
                    {/* Active gradient background */}
                    {activeIndex === index && (
                      <motion.div
                        layoutId="activeNodeBg"
                        className="absolute inset-0 bg-gradient-to-br from-background/95 to-background/90 rounded-2xl m-[2px]"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                      />
                    )}

                    {/* Content */}
                    <div className="relative flex items-center gap-3 flex-1 min-w-0">
                      {/* Avatar */}
                      <div className="relative flex-shrink-0">
                        <div className={`w-14 h-14 rounded-full bg-gradient-to-br ${member.gradient} p-[2px] shadow-md ${
                          activeIndex === index ? 'shadow-lg' : ''
                        }`}>
                          <div className="w-full h-full rounded-full bg-white/90 dark:bg-background/20 backdrop-blur-sm flex items-center justify-center overflow-hidden">
                            {member.image.includes('placeholder') ? (
                              <User className="w-7 h-7 text-white" />
                            ) : (
                              <img 
                                src={member.image} 
                                alt={member.name}
                                className="w-full h-full object-cover"
                              />
                            )}
                          </div>
                        </div>

                        {/* Simple active pulse */}
                        {activeIndex === index && (
                          <div className={`absolute inset-0 rounded-full bg-gradient-to-br ${member.gradient} opacity-30 blur-sm`} />
                        )}
                      </div>

                      {/* Name & Role */}
                      <div className="flex-1 text-left min-w-0">
                        <h4 className={`font-bold text-sm transition-colors truncate ${
                          activeIndex === index ? "text-foreground" : "text-foreground/70"
                        }`}>
                          {member.name}
                        </h4>
                        <p className={`text-xs transition-colors truncate ${
                          activeIndex === index ? "text-muted-foreground" : "text-muted-foreground/60"
                        }`}>
                          {member.role}
                        </p>
                      </div>

                      {/* Active indicator */}
                      {activeIndex === index && (
                        <motion.div
                          layoutId="activeIndicator"
                          className={`w-2 h-2 rounded-full bg-gradient-to-br ${member.gradient} shadow-md`}
                          transition={{ type: "spring", bounce: 0.3 }}
                        />
                      )}
                    </div>

                    {/* Progress bar */}
                    {activeIndex === index && (
                      <motion.div
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 5, ease: "linear" }}
                        className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${member.gradient} origin-left rounded-full`}
                      />
                    )}
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>

          {/* Right side - Detailed Profile Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative min-h-[400px] lg:min-h-[500px]"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={activeMember.id}
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -20 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="relative"
              >
                {/* Main Profile Card */}
                <div className="relative bg-gradient-to-br from-green-50/40 to-green-100/20 dark:from-green-950/15 dark:to-green-900/5 backdrop-blur-xl rounded-3xl border border-border/40 shadow-xl overflow-hidden">
                  {/* Top accent line */}
                  <div className={`absolute top-0 inset-x-0 h-1 bg-gradient-to-r ${activeMember.gradient}`} />

                  <div className="relative p-6 sm:p-8 lg:p-10">
                    <div className="flex flex-col items-center text-center">
                      {/* Profile Image */}
                      <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.2, type: "spring" }}
                        className="relative mb-6"
                      >
                        {/* Avatar */}
                        <div className={`relative w-32 h-32 sm:w-40 sm:h-40 rounded-full bg-gradient-to-br ${activeMember.gradient} p-1 shadow-xl`}>
                          <div className="w-full h-full rounded-full bg-white/90 dark:bg-background/10 backdrop-blur-sm flex items-center justify-center overflow-hidden">
                            {activeMember.image.includes('placeholder') ? (
                              <User className="w-16 h-16 sm:w-20 sm:h-20 text-white" />
                            ) : (
                              <img 
                                src={activeMember.image} 
                                alt={activeMember.name}
                                className="w-full h-full object-cover"
                              />
                            )}
                          </div>
                        </div>

                        {/* Online status */}
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 0.4, type: "spring", bounce: 0.5 }}
                          className="absolute bottom-2 right-2 w-8 h-8 rounded-full bg-green-500 border-4 border-background shadow-lg flex items-center justify-center"
                        >
                          <div className="w-3 h-3 rounded-full bg-white" />
                        </motion.div>
                      </motion.div>

                      {/* Name & Role */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="mb-6 space-y-3"
                      >
                        <h3 className="text-2xl sm:text-3xl font-bold text-foreground">
                          {activeMember.name}
                        </h3>
                        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r ${activeMember.gradient} text-white text-sm font-medium shadow-lg`}>
                          <Sparkles className="w-4 h-4" />
                          {activeMember.role}
                        </div>
                      </motion.div>

                      {/* Bio */}
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="text-muted-foreground leading-relaxed mb-8 max-w-md mx-auto"
                      >
                        {activeMember.bio}
                      </motion.p>

                      {/* Social Links */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="flex items-center justify-center gap-4 flex-wrap"
                      >
                        {Object.entries(activeMember.socials).map(([platform, link], idx) => {
                          const iconConfig = {
                            linkedin: { Icon: Linkedin, color: "bg-[#0077B5] hover:bg-[#0077B5]/80" },
                            github: { Icon: Github, color: "bg-[#181717] dark:bg-[#ffffff] dark:text-[#181717] hover:bg-[#181717]/80 dark:hover:bg-[#ffffff]/80" },
                            instagram: { Icon: Instagram, color: "bg-gradient-to-br from-[#F58529] via-[#DD2A7B] to-[#8134AF] hover:opacity-80" },
                          };
                          const config = iconConfig[platform as keyof typeof iconConfig];
                          const Icon = config.Icon;

                          return (
                            <motion.a
                              key={platform}
                              href={link}
                              initial={{ opacity: 0, scale: 0 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ delay: 0.6 + idx * 0.1, type: "spring", bounce: 0.4 }}
                              whileHover={{ scale: 1.05, y: -2 }}
                              whileTap={{ scale: 0.95 }}
                              className={`w-12 h-12 rounded-xl ${config.color} flex items-center justify-center text-white shadow-md transition-all`}
                            >
                              <Icon className="w-5 h-5" />
                            </motion.a>
                          );
                        })}
                      </motion.div>
                    </div>
                  </div>

                  {/* Bottom decorative element */}
                  <div className={`absolute bottom-0 inset-x-0 h-px bg-gradient-to-r ${activeMember.gradient} opacity-30`} />
                </div>
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Simple decorative elements */}
        <div className="absolute -top-20 left-0 w-32 h-32 bg-gradient-to-br from-blue-500/5 to-purple-500/5 rounded-full blur-2xl pointer-events-none -z-10" />
        <div className="absolute -bottom-20 right-0 w-32 h-32 bg-gradient-to-br from-pink-500/5 to-purple-500/5 rounded-full blur-2xl pointer-events-none -z-10" />
      </div>
    </motion.div>
  );
};
