import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  MessageCircle,
  Zap,
  Network,
  User,
  Share2,
  Settings,
  Archive,
  Clock,
  LucideIcon,
  Sparkles,
} from "lucide-react";

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
  gradient: string;
  accentColor: string;
}

const features: Feature[] = [
  {
    icon: MessageCircle,
    title: "Intelligent Conversations",
    description: "Engage with an AI that truly understands context, remembers your preferences, and adapts to your communication style for meaningful interactions.",
    gradient: "from-blue-500 via-blue-400 to-cyan-500",
    accentColor: "bg-blue-500/10 border-blue-500/20",
  },
  {
    icon: Zap,
    title: "Highlight Anything Instantly",
    description: "Select any text to create instant highlights with custom colors. Get AI insights, summaries, or create mini-agents from your selections.",
    gradient: "from-yellow-500 via-amber-400 to-orange-500",
    accentColor: "bg-yellow-500/10 border-yellow-500/20",
  },
  {
    icon: Network,
    title: "Visual Knowledge Mapping",
    description: "See your ideas come to life in an interactive knowledge graph. Discover hidden connections and navigate your thoughts visually.",
    gradient: "from-purple-500 via-violet-400 to-pink-500",
    accentColor: "bg-purple-500/10 border-purple-500/20",
  },
  {
    icon: User,
    title: "True Personalization",
    description: "PRISM learns from every interaction, building a unique understanding of your preferences, goals, and working style over time.",
    gradient: "from-green-500 via-emerald-400 to-teal-500",
    accentColor: "bg-green-500/10 border-green-500/20",
  },
  {
    icon: Share2,
    title: "Collaboration With Friends",
    description: "Share highlights, knowledge maps, and conversations. Work together on projects and build collective intelligence with your team.",
    gradient: "from-indigo-500 via-blue-400 to-cyan-500",
    accentColor: "bg-indigo-500/10 border-indigo-500/20",
  },
  {
    icon: Settings,
    title: "Use Your Own APIs + Custom Tools",
    description: "Bring your own API keys and integrate custom tools. Extend PRISM's capabilities to match your unique workflow and requirements.",
    gradient: "from-red-500 via-rose-400 to-pink-500",
    accentColor: "bg-red-500/10 border-red-500/20",
  },
  {
    icon: Archive,
    title: "Second-Brain Memory System",
    description: "Never lose a thought. PRISM's advanced memory system stores, organizes, and retrieves information exactly when you need it.",
    gradient: "from-teal-500 via-cyan-400 to-blue-500",
    accentColor: "bg-teal-500/10 border-teal-500/20",
  },
  {
    icon: Clock,
    title: "Task Tracking & Smart Reminders",
    description: "Extract tasks from conversations automatically. Get intelligent reminders based on context, priority, and your schedule.",
    gradient: "from-amber-500 via-orange-400 to-yellow-500",
    accentColor: "bg-amber-500/10 border-amber-500/20",
  },
];

export const HorizontalFeatures = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);
  const [gsapLoaded, setGsapLoaded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check if mobile
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener("resize", checkMobile);

    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    // Only load GSAP on desktop
    if (isMobile || gsapLoaded) return;

    const loadGSAP = async () => {
      try {
        const { gsap } = await import("gsap");
        const { ScrollTrigger } = await import("gsap/ScrollTrigger");
        gsap.registerPlugin(ScrollTrigger);
        setGsapLoaded(true);

        const section = sectionRef.current;
        const container = containerRef.current;

        if (!section || !container) return;

        // Horizontal scroll animation - scroll until last card reaches 20% from left
        const viewportWidth = window.innerWidth;
        const cardWidth = 320; // w-80 in pixels
        const gap = 32; // gap-8 in pixels
        const targetPosition = viewportWidth * 0.7; // 20% from left
        
        // Calculate scroll distance to position last card at 20% from left
        // Total width of all cards + gaps - viewport width + additional space to reach 20%
        const scrollWidth = container.scrollWidth - viewportWidth + (viewportWidth - cardWidth - targetPosition);
        
        gsap.to(container, {
          x: () => -scrollWidth,
          ease: "none",
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: () => `+=${scrollWidth * 2}`,
            scrub: 1,
            pin: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });

        // Staggered card entrance
        cardsRef.current.forEach((card, index) => {
          if (!card) return;
          
          gsap.fromTo(
            card,
            {
              opacity: 0,
              y: 30,
              scale: 0.95,
            },
            {
              opacity: 1,
              y: 0,
              scale: 1,
              duration: 0.6,
              delay: index * 0.08,
              scrollTrigger: {
                trigger: card,
                containerAnimation: gsap.getById("horizontal-scroll") as any,
                start: "left 80%",
                toggleActions: "play none none reverse",
              },
            }
          );
        });

        return () => {
          ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
        };
      } catch (error) {
        console.warn("Failed to load GSAP:", error);
      }
    };

    loadGSAP();
  }, [isMobile, gsapLoaded]);

  // Desktop view with GSAP horizontal scroll
  if (!isMobile) {
    return (
      <section
        ref={sectionRef}
        id="features-section"
        className="hidden md:block py-24 bg-background overflow-hidden relative"
      >
        {/* Background gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-background via-secondary/20 to-background pointer-events-none" />
        
        <div className="container px-4 sm:px-6 mb-16 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="inline-flex items-center gap-2 px-4 py-2 mb-6 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium shadow-soft"
            >
              <Sparkles className="w-4 h-4" />
              <span>Powerful Features</span>
            </motion.div>
            
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-4 bg-gradient-to-r from-foreground via-foreground to-muted-foreground bg-clip-text">
              Everything you need
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
              Powerful features designed to transform how you work with AI
            </p>
          </motion.div>
        </div>

        <div
          ref={containerRef}
          className="flex gap-8 px-[10vw] relative z-10"
          style={{
            willChange: "transform",
          }}
        >
          {features.map((feature, index) => (
            <div
              key={feature.title}
              ref={(el) => (cardsRef.current[index] = el)}
              className="group relative flex-shrink-0 w-80 h-80 p-6 bg-card rounded-3xl border border-border shadow-soft hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-all duration-500 hover:-translate-y-3 hover:scale-[1.03] overflow-hidden"
              style={{
                willChange: "transform, opacity",
                backfaceVisibility: "hidden",
              }}
            >
              {/* Background gradient glow */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500`} />
              
              {/* Icon container */}
              <div className={`relative w-14 h-14 rounded-2xl ${feature.accentColor} flex items-center justify-center mb-4 transition-all duration-500 group-hover:scale-110 group-hover:rotate-6 shadow-soft`}>
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-20 transition-opacity duration-500`} />
                <feature.icon className="w-7 h-7 text-primary relative z-10 transition-transform duration-500 group-hover:scale-110" />
              </div>

              {/* Content */}
              <div className="relative z-10">
                <h3 className="text-lg font-bold text-foreground mb-2.5 leading-tight group-hover:text-primary transition-colors duration-300">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed group-hover:text-foreground/80 transition-colors duration-300">
                  {feature.description}
                </p>
              </div>

              {/* Decorative gradient line */}
              <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-b-3xl`} />
              
              {/* Shine effect */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  // Mobile view with native horizontal scroll
  return (
    <section
      id="features-section"
      className="block md:hidden py-16 bg-background relative overflow-hidden"
    >
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-secondary/20 to-background pointer-events-none" />
      
      <div className="container px-4 mb-12 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.15, duration: 0.4 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 mb-4 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium shadow-soft"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Powerful Features</span>
          </motion.div>
          
          <h2 className="text-2xl font-bold text-foreground mb-3">
            Everything you need
          </h2>
          <p className="text-muted-foreground text-sm max-w-xl mx-auto leading-relaxed">
            Powerful features designed to transform how you work with AI
          </p>
        </motion.div>
      </div>

      <div
        className="flex gap-4 px-4 pb-4 overflow-x-auto snap-x snap-mandatory scrollbar-hide relative z-10"
        style={{
          WebkitOverflowScrolling: "touch",
          scrollbarWidth: "none",
          msOverflowStyle: "none",
        }}
      >
        {features.map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.5, delay: index * 0.08 }}
            className="relative flex-shrink-0 w-72 h-80 p-5 bg-card rounded-2xl border border-border shadow-soft snap-center overflow-hidden"
          >
            {/* Background gradient glow */}
            <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-5`} />
            
            {/* Icon container */}
            <div className={`relative w-12 h-12 rounded-xl ${feature.accentColor} flex items-center justify-center mb-3 shadow-soft`}>
              <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${feature.gradient} opacity-10`} />
              <feature.icon className="w-6 h-6 text-primary relative z-10" />
            </div>

            {/* Content */}
            <div className="relative z-10">
              <h3 className="text-lg font-bold text-foreground mb-2.5 leading-tight">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </div>

            {/* Decorative gradient line */}
            <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${feature.gradient} opacity-80 rounded-b-2xl`} />
          </motion.div>
        ))}
      </div>

      {/* Scroll indicator */}
      <div className="flex justify-center gap-2 mt-8 relative z-10">
        {features.map((_, index) => (
          <div
            key={index}
            className="w-2 h-2 rounded-full bg-muted-foreground/30 transition-all duration-300"
          />
        ))}
      </div>
      
      {/* Swipe hint */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.5 }}
        className="text-center text-xs text-muted-foreground/60 mt-4 relative z-10"
      >
        Swipe to explore features
      </motion.p>
    </section>
  );
};
