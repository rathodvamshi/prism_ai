import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { ParticleCanvas } from "@/components/hero/ParticleCanvas";
import { HorizontalFeatures } from "@/components/hero/HorizontalFeatures";
import { PrototypeShowcase } from "@/components/hero/PrototypeShowcase";
import { ArrowRight, Sparkles } from "lucide-react";

const Hero = () => {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <ParticleCanvas />
        
        <div className="container relative z-10 px-4 sm:px-6 pt-24 pb-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-4xl mx-auto text-center"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium"
            >
              <Sparkles className="w-4 h-4" />
              <span>Your AI-Powered Knowledge Companion</span>
            </motion.div>

            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold text-foreground mb-6 leading-tight">
              Your Personal{" "}
              <span className="bg-gradient-to-r from-primary via-blue-500 to-purple-500 bg-clip-text text-transparent">
                AI Prism
              </span>
            </h1>

            <p className="text-base sm:text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
              Highlight. Understand. Organize your mind. Transform how you interact with AI 
              through intelligent conversations and visual knowledge mapping.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button variant="hero" size="xl" asChild>
                <Link to="/chat" className="gap-2">
                  Start Chatting
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </Button>
              <Button variant="hero-outline" size="xl" asChild>
                <a href="#features-section">Learn More</a>
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Gradient overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
      </section>

      {/* Features Section */}
      <HorizontalFeatures />

      {/* Prototype Showcase */}
      <PrototypeShowcase />

      {/* CTA Section */}
      <section className="py-20 sm:py-24 bg-secondary/50">
        <div className="container px-4 sm:px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="max-w-3xl mx-auto text-center p-8 sm:p-12 bg-card rounded-3xl border border-border shadow-card"
          >
            <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-4">
              Ready to get started?
            </h2>
            <p className="text-muted-foreground mb-8">
              Join thousands of users who have transformed their productivity with PRISM.
            </p>
            <Button variant="hero" size="lg" asChild>
              <Link to="/auth?mode=signup" className="gap-2">
                Create Free Account
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Hero;
