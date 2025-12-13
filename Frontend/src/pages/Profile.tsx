import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, User, Sparkles, Save, Camera } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

const Profile = () => {
  const { toast } = useToast();
  const [name, setName] = useState("John Doe");
  const [email] = useState("john@example.com");
  const [tone, setTone] = useState("balanced");
  const [language, setLanguage] = useState("en");
  const [model, setModel] = useState("gpt-4o-mini");

  const handleSave = () => {
    toast({
      title: "Profile Updated",
      description: "Your changes have been saved successfully.",
    });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link to="/chat">
                <ArrowLeft className="w-4 h-4" />
              </Link>
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-br from-primary via-blue-500 to-purple-500 flex items-center justify-center">
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-primary-foreground" />
              </div>
              <span className="font-bold text-foreground">PRISM</span>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-xl mx-auto"
        >
          <h1 className="text-2xl font-bold text-foreground mb-8">Profile Settings</h1>

          <div className="bg-card rounded-2xl border border-border shadow-soft p-5 sm:p-8 space-y-6 sm:space-y-8">
            {/* Avatar */}
            <div className="flex items-center gap-4 sm:gap-6">
              <div className="relative">
                <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br from-primary via-blue-500 to-purple-500 flex items-center justify-center">
                  <User className="w-8 h-8 sm:w-10 sm:h-10 text-primary-foreground" />
                </div>
                <button className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-card border border-border shadow-soft flex items-center justify-center hover:bg-secondary transition-colors">
                  <Camera className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
              <div>
                <h2 className="font-semibold text-foreground">{name}</h2>
                <p className="text-sm text-muted-foreground">Free Plan</p>
              </div>
            </div>

            {/* Form */}
            <div className="space-y-6">
              <div className="space-y-2">
                <Label>Display Name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                />
              </div>

              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={email} disabled className="bg-muted" />
                <p className="text-xs text-muted-foreground">
                  Contact support to change your email
                </p>
              </div>

              <div className="space-y-2">
                <Label>AI Tone</Label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="casual">Casual</SelectItem>
                    <SelectItem value="creative">Creative</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Preferred Model</Label>
                <Select value={model} onValueChange={setModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                    <SelectItem value="gpt-4o">GPT-4o (BYOK)</SelectItem>
                    <SelectItem value="claude-3">Claude 3 (BYOK)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Language</Label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                    <SelectItem value="fr">Français</SelectItem>
                    <SelectItem value="de">Deutsch</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="pt-4 border-t border-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Last active</span>
                  <span className="text-foreground">Just now</span>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <Button onClick={handleSave} className="w-full gap-2 btn-responsive">
              <Save className="w-4 h-4" />
              Save Changes
            </Button>
          </div>
        </motion.div>
      </main>
    </div>
  );
};

export default Profile;
