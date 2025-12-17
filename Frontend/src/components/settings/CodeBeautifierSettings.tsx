/**
 * 🎛️ CODE BEAUTIFIER SETTINGS COMPONENT
 * 
 * Control panel for managing code beautification preferences
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCodeBeautifier } from "@/hooks/useCodeBeautifier";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  Sparkles, 
  Settings, 
  BarChart3, 
  Award, 
  RefreshCw, 
  Download,
  Code2,
  Zap,
  Target,
  Globe,
  Trophy
} from "lucide-react";

export const CodeBeautifierSettings = () => {
  const {
    settings,
    updateSettings,
    stats,
    resetStats,
    getAchievements,
    isEnabled,
    toggle,
    toggleAutoDetect,
    toggleIndicator,
  } = useCodeBeautifier();
  
  const [showDemo, setShowDemo] = useState(false);

  const demoCode = `function messyCode(x,y){
if(x>y)return x+y;
else{
let result=x*y;
for(let i=0;i<10;i++){result+=i;}
return result;}}`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <Sparkles className="w-4 h-4" />
          Code Beautifier
          {!isEnabled && <Badge variant="secondary" className="text-xs">OFF</Badge>}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-500" />
            Code Beautifier Settings
          </DialogTitle>
          <DialogDescription>
            Configure automatic code formatting for all AI responses
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Main Toggle */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center justify-between">
                Auto-Beautification
                <Switch
                  checked={isEnabled}
                  onCheckedChange={toggle}
                />
              </CardTitle>
              <CardDescription>
                Automatically format and beautify all code blocks in AI responses
              </CardDescription>
            </CardHeader>
          </Card>

          <AnimatePresence>
            {isEnabled && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-6"
              >
                {/* Format Settings */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Settings className="w-4 h-4" />
                      Formatting Options
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Indent Size */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Indent Size</label>
                        <span className="text-sm text-muted-foreground">
                          {settings.indentSize} spaces
                        </span>
                      </div>
                      <Slider
                        value={[settings.indentSize]}
                        onValueChange={([value]) => updateSettings({ indentSize: value })}
                        max={8}
                        min={2}
                        step={2}
                        className="w-full"
                      />
                    </div>

                    {/* Max Line Length */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Max Line Length</label>
                        <span className="text-sm text-muted-foreground">
                          {settings.maxLineLength} chars
                        </span>
                      </div>
                      <Slider
                        value={[settings.maxLineLength]}
                        onValueChange={([value]) => updateSettings({ maxLineLength: value })}
                        max={120}
                        min={60}
                        step={10}
                        className="w-full"
                      />
                    </div>

                    <Separator />

                    {/* Feature Toggles */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <label className="text-sm font-medium">Auto-detect Language</label>
                          <p className="text-xs text-muted-foreground">
                            Automatically identify programming languages
                          </p>
                        </div>
                        <Switch
                          checked={settings.autoDetectLanguage}
                          onCheckedChange={toggleAutoDetect}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <label className="text-sm font-medium">Show Beautification Indicator</label>
                          <p className="text-xs text-muted-foreground">
                            Display ✨ icon when code is automatically formatted
                          </p>
                        </div>
                        <Switch
                          checked={settings.showBeautificationIndicator}
                          onCheckedChange={toggleIndicator}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Statistics */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="w-4 h-4" />
                      Statistics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Progress */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>Success Rate</span>
                        <span className="font-medium">{Math.round(stats.successRate)}%</span>
                      </div>
                      <Progress value={stats.successRate} className="h-2" />
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
                        <Code2 className="w-4 h-4 text-blue-500" />
                        <div>
                          <div className="font-medium">{stats.totalCodeBlocks}</div>
                          <div className="text-xs text-muted-foreground">Total Blocks</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
                        <Sparkles className="w-4 h-4 text-yellow-500" />
                        <div>
                          <div className="font-medium">{stats.beautifiedBlocks}</div>
                          <div className="text-xs text-muted-foreground">Beautified</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
                        <Globe className="w-4 h-4 text-green-500" />
                        <div>
                          <div className="font-medium">{Object.keys(stats.languages).length}</div>
                          <div className="text-xs text-muted-foreground">Languages</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
                        <Download className="w-4 h-4 text-purple-500" />
                        <div>
                          <div className="font-medium">{stats.timesSaved}</div>
                          <div className="text-xs text-muted-foreground">Downloads</div>
                        </div>
                      </div>
                    </div>

                    {/* Language Breakdown */}
                    {Object.keys(stats.languages).length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Languages</h4>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(stats.languages).map(([lang, count]) => (
                            <Badge key={lang} variant="secondary" className="text-xs">
                              {lang} ({count})
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex justify-end">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={resetStats}
                              className="gap-1"
                            >
                              <RefreshCw className="w-3 h-3" />
                              Reset
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Reset all statistics</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </CardContent>
                </Card>

                {/* Achievements */}
                {getAchievements.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Award className="w-4 h-4" />
                        Achievements
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {getAchievements.map((achievement, index) => (
                          <Badge key={index} className="gap-1 px-2 py-1">
                            <Trophy className="w-3 h-3" />
                            {achievement}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Quick Demo */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      Live Preview
                    </CardTitle>
                    <CardDescription>
                      See the beautifier in action
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button
                      variant="outline"
                      onClick={() => setShowDemo(!showDemo)}
                      className="w-full gap-2"
                    >
                      <Target className="w-4 h-4" />
                      {showDemo ? 'Hide Demo' : 'Show Demo'}
                    </Button>
                    
                    <AnimatePresence>
                      {showDemo && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-4 space-y-3"
                        >
                          <div>
                            <h5 className="text-xs font-medium mb-2 text-muted-foreground">BEFORE</h5>
                            <pre className="bg-muted/50 p-3 rounded text-xs overflow-auto">
                              {demoCode}
                            </pre>
                          </div>
                          
                          <div>
                            <h5 className="text-xs font-medium mb-2 text-muted-foreground">AFTER ✨</h5>
                            <pre className="bg-green-500/10 border border-green-500/20 p-3 rounded text-xs overflow-auto">
                              {`function messyCode(x, y) {
  if (x > y) return x + y;
  else {
    let result = x * y;
    for (let i = 0; i < 10; i++) {
      result += i;
    }
    return result;
  }
}`}
                            </pre>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CodeBeautifierSettings;