import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Github,
  Instagram,
  Linkedin,
  Mail,
  Heart,
  Sparkles,
  MessageCircle,
  BookOpen,
  Shield,
  FileText,
  HelpCircle,
  Users,
  Zap,
  ArrowUpRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

export const Footer = () => {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setTimeout(() => {
        setEmail("");
        setSubscribed(false);
      }, 3000);
    }
  };

  const footerLinks = {
    product: [
      { name: "Features", href: "#features-section", icon: Sparkles },
      { name: "Pricing", href: "#", icon: Zap },
      { name: "Updates", href: "#", icon: BookOpen },
      { name: "Roadmap", href: "#", icon: ArrowUpRight },
    ],
    resources: [
      { name: "Documentation", href: "#", icon: FileText },
      { name: "API Reference", href: "#", icon: BookOpen },
      { name: "Community", href: "#", icon: Users },
      { name: "Support", href: "#", icon: HelpCircle },
    ],
    company: [
      { name: "About", href: "#", icon: Users },
      { name: "Blog", href: "#", icon: BookOpen },
      { name: "Privacy", href: "#", icon: Shield },
      { name: "Terms", href: "#", icon: FileText },
    ],
  };

  const socialLinks = [
    { 
      name: "GitHub", 
      icon: Github, 
      href: "https://github.com/rathodvamshi", 
      bgGradient: "from-[#6e5494] to-[#24292e]",
      glowColor: "rgba(110, 84, 148, 0.4)",
      iconColor: "#6e5494"
    },
    { 
      name: "Instagram", 
      icon: Instagram, 
      href: "https://www.instagram.com/_rathod_369/", 
      bgGradient: "from-[#f09433] via-[#e6683c] via-[#dc2743] via-[#cc2366] to-[#bc1888]",
      glowColor: "rgba(225, 48, 108, 0.5)",
      iconColor: "#E1306C"
    },
    { 
      name: "LinkedIn", 
      icon: Linkedin, 
      href: "https://www.linkedin.com/in/bukya-vamshi-b27a38348?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app", 
      bgGradient: "from-[#0077b5] to-[#00a0dc]",
      glowColor: "rgba(0, 119, 181, 0.5)",
      iconColor: "#0077b5"
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
      },
    },
  };

  return (
    <footer className="relative bg-background border-t border-border overflow-hidden">
      {/* Subtle Background gradient effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-secondary/10 via-background to-background pointer-events-none" />
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-gradient-to-br from-primary/3 to-purple-500/3 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-gradient-to-tl from-blue-500/3 to-cyan-500/3 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 pt-16 pb-8">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-12 mb-12"
        >
          {/* Brand Section */}
          <motion.div variants={itemVariants} className="lg:col-span-4">
            <Link to="/" className="inline-flex items-center gap-2 mb-4 group">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-primary to-purple-500 rounded-lg blur-lg opacity-50 group-hover:opacity-75 transition-opacity" />
                <div className="relative w-10 h-10 bg-gradient-to-br from-primary to-purple-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                PRISM
              </span>
            </Link>
            <p className="text-muted-foreground text-sm leading-relaxed mb-6 max-w-sm">
              Transform how you interact with AI through intelligent conversations, 
              visual knowledge mapping, and powerful memory systems.
            </p>
            
            {/* Social Links */}
            <div className="flex items-center gap-4">
              {socialLinks.map((social, index) => {
                const Icon = social.icon;
                return (
                  <motion.a
                    key={social.name}
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    initial={{ opacity: 0, scale: 0 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 + index * 0.1, type: "spring" }}
                    whileHover={{ scale: 1.1, y: -3 }}
                    whileTap={{ scale: 0.95 }}
                    className="group relative"
                    aria-label={social.name}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Glow effect */}
                    <div 
                      className="absolute -inset-1 rounded-xl opacity-0 group-hover:opacity-75 blur-lg transition-all duration-500"
                      style={{
                        background: `linear-gradient(to right, ${social.bgGradient.replace('from-', '').replace('via-', ', ').replace('to-', ', ').split(' ').map(c => c.replace('[', '').replace(']', '')).join(', ')})`
                      }}
                    />
                    
                    {/* Icon container */}
                    <div className="relative w-12 h-12 rounded-xl bg-secondary/50 border border-border flex items-center justify-center text-muted-foreground transition-all duration-300 overflow-hidden group-hover:border-transparent group-hover:shadow-xl">
                      {/* Background gradient on hover */}
                      <div 
                        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                        style={{
                          background: social.name === 'Instagram' 
                            ? 'linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)'
                            : social.name === 'LinkedIn'
                            ? 'linear-gradient(135deg, #0077b5 0%, #00a0dc 100%)'
                            : 'linear-gradient(135deg, #6e5494 0%, #24292e 100%)'
                        }}
                      />
                      
                      {/* Icon */}
                      <Icon className="w-5 h-5 relative z-10 transition-colors duration-300 group-hover:text-white" />
                    </div>
                  </motion.a>
                );
              })}
            </div>
          </motion.div>

          {/* Links Sections */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              Product
            </h3>
            <ul className="space-y-3">
              {footerLinks.product.map((link, index) => (
                <motion.li
                  key={link.name}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.6 + index * 0.05 }}
                >
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 flex items-center gap-2 group"
                  >
                    <link.icon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <span>{link.name}</span>
                  </a>
                </motion.li>
              ))}
            </ul>
          </motion.div>

          <motion.div variants={itemVariants} className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary" />
              Resources
            </h3>
            <ul className="space-y-3">
              {footerLinks.resources.map((link, index) => (
                <motion.li
                  key={link.name}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.7 + index * 0.05 }}
                >
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 flex items-center gap-2 group"
                  >
                    <link.icon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <span>{link.name}</span>
                  </a>
                </motion.li>
              ))}
            </ul>
          </motion.div>

          <motion.div variants={itemVariants} className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-primary" />
              Company
            </h3>
            <ul className="space-y-3">
              {footerLinks.company.map((link, index) => (
                <motion.li
                  key={link.name}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.8 + index * 0.05 }}
                >
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 flex items-center gap-2 group"
                  >
                    <link.icon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <span>{link.name}</span>
                  </a>
                </motion.li>
              ))}
            </ul>
          </motion.div>

          {/* Newsletter Section */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-primary" />
              Stay Updated
            </h3>
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
              Get the latest updates, features, and AI insights.
            </p>
            <form onSubmit={handleSubscribe} className="space-y-3">
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  className="w-full px-4 py-2.5 text-sm bg-secondary/50 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-200 pr-10"
                  disabled={subscribed}
                />
                <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              </div>
              <Button
                type="submit"
                size="sm"
                className="w-full bg-gradient-to-r from-primary to-purple-500 hover:from-primary/90 hover:to-purple-500/90 text-white shadow-lg hover:shadow-xl transition-all duration-300"
                disabled={subscribed}
              >
                {subscribed ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="flex items-center gap-2"
                  >
                    <Heart className="w-4 h-4 fill-current" />
                    Subscribed!
                  </motion.span>
                ) : (
                  "Subscribe"
                )}
              </Button>
            </form>
          </motion.div>
        </motion.div>

        {/* Divider */}
        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="h-px bg-gradient-to-r from-transparent via-border to-transparent mb-8"
        />

        {/* Bottom Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground"
        >
          <div className="flex items-center gap-2">
            <span>© 2024 PRISM. Built by Prism team with</span>
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                repeatDelay: 2,
              }}
            >
              <Heart className="w-4 h-4 text-red-500 fill-current" />
            </motion.div>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-xs hover:text-foreground transition-colors duration-200 flex items-center gap-1"
            >
              <Shield className="w-3.5 h-3.5" />
              Privacy Policy
            </a>
            <a
              href="#"
              className="text-xs hover:text-foreground transition-colors duration-200 flex items-center gap-1"
            >
              <FileText className="w-3.5 h-3.5" />
              Terms of Service
            </a>
            <a
              href="#"
              className="text-xs hover:text-foreground transition-colors duration-200 flex items-center gap-1"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              Help
            </a>
          </div>
        </motion.div>

        {/* Decorative Elements */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 0.1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, delay: 0.6 }}
          className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-primary to-purple-500 rounded-full blur-3xl opacity-0"
        />
      </div>
    </footer>
  );
};
