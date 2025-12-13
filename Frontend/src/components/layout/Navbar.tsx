import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export const Navbar = () => {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed top-0 left-0 right-0 z-50 bg-card/80 backdrop-blur-xl border-b border-border"
    >
      <div className="container mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group min-w-0">
          <div className="relative w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-br from-primary via-blue-500 to-purple-500 flex items-center justify-center shadow-soft group-hover:shadow-glow transition-shadow">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-primary-foreground" />
          </div>
          <span className="text-lg sm:text-xl font-bold text-foreground truncate">PRISM</span>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/auth?mode=login">Login</Link>
          </Button>
          <Button variant="default" size="sm" asChild>
            <Link to="/auth?mode=signup">Sign Up</Link>
          </Button>
        </nav>
      </div>
    </motion.header>
  );
};
