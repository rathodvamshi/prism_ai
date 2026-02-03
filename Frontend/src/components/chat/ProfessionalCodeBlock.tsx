import { useState, useMemo, useRef } from "react";
import { Highlight } from 'prism-react-renderer';
import { themes } from 'prism-react-renderer';
import { Copy, Check } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { beautifyCode, detectLanguage } from "@/lib/codeBeautifier";

interface CodeBlockProps {
  children: string;
  language?: string;
  inline?: boolean;
}

// 🎨 PROFESSIONAL VS CODE THEME - Perfect Implementation
const professionalTheme = {
  plain: {
    backgroundColor: '#0A0A0A', // Professional dark background
    color: '#d4d4d4', // Default text color
  },
  styles: [] as any, // We handle colors manually for full control
} as any;

// 🌈 PROFESSIONAL COLOR PALETTE - Exact VS Code Colors
const getTokenColor = (token: any) => {
  // 💚 GREEN COMMENTS - Beautiful and readable!
  if (token.types.includes('comment')) {
    return '#4ADE80'; // Professional green
  }

  // 🔵 BLUE KEYWORDS - public, class, return, etc.
  if (token.types.includes('keyword')) {
    return '#569CD6'; // VS Code blue
  }

  // 🟡 GOLD FUNCTIONS - method names, function calls
  if (token.types.includes('function')) {
    return '#DCDCAA'; // VS Code gold
  }

  // 🟠 ORANGE STRINGS - "text", 'text'
  if (token.types.includes('string')) {
    return '#CE9178'; // VS Code orange
  }

  // 🟢 LIGHT GREEN NUMBERS - 123, 42.5
  if (token.types.includes('number')) {
    return '#B5CEA8'; // VS Code light green
  }

  // 🌊 AQUA CLASS NAMES - HelloWorld, MyClass
  if (token.types.includes('class-name')) {
    return '#4EC9B0'; // VS Code aqua
  }

  // ⚪ WHITE OPERATORS & BRACES - =, +, {}, etc.
  if (token.types.includes('operator') ||
    token.types.includes('punctuation') ||
    token.types.includes('delimiter')) {
    return '#FFFFFF'; // Pure white
  }

  // 🔵 LIGHT BLUE VARIABLES
  if (token.types.includes('variable') || token.types.includes('property')) {
    return '#9CDCFE'; // VS Code light blue
  }

  // Default: light gray
  return '#d4d4d4';
};

// 📝 LANGUAGE MAPPING for better support
const languageMap: Record<string, string> = {
  'js': 'javascript',
  'ts': 'typescript',
  'py': 'python',
  'java': 'java',
  'cpp': 'cpp',
  'c++': 'cpp',
  'cs': 'csharp',
  'html': 'markup',
  'xml': 'markup',
  'md': 'markdown',
};

export const CodeBlock = ({ children, language = "javascript", inline = false }: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  const codeBlockRef = useRef<HTMLDivElement>(null);

  // 🌟 STEP 1 — Beautify Code Before Rendering (Safe handling)
  const { beautifiedCode, detectedLanguage, wasBeautified } = useMemo(() => {
    // Safety check
    if (inline || !children || typeof children !== 'string' || children.trim().length === 0) {
      return {
        beautifiedCode: children || '',
        detectedLanguage: language || 'javascript',
        wasBeautified: false
      };
    }

    try {
      const result = beautifyCode(children, language);
      const wasChanged = result.code !== children;

      if (result.success && wasChanged && result.code) {
        return {
          beautifiedCode: result.code,
          detectedLanguage: result.language || 'javascript',
          wasBeautified: true
        };
      } else {
        return {
          beautifiedCode: children,
          detectedLanguage: language || 'javascript',
          wasBeautified: false
        };
      }
    } catch (error) {
      console.warn('🚨 Beautifier error, using original code:', error);
      return {
        beautifiedCode: children,
        detectedLanguage: language || 'javascript',
        wasBeautified: false
      };
    }
  }, [children, language, inline]);

  // Map language to proper prism language
  const safeLang = (detectedLanguage || language || 'javascript').toLowerCase();
  const mappedLanguage = languageMap[safeLang] || safeLang;
  const displayLanguage = mappedLanguage === 'text' ? 'javascript' : mappedLanguage;

  // 🧠 STEP 2 — Split Code Into Lines (Safe handling)
  const codeLines = useMemo(() => {
    const code = beautifiedCode || children || '';
    return code.split("\\n");
  }, [beautifiedCode, children]);

  const lineCount = codeLines.length || 1;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(beautifiedCode || children || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 1000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  // Inline code (single backtick)
  if (inline) {
    return (
      <code className="px-2 py-0.5 rounded-md bg-zinc-900 text-cyan-300 text-sm font-mono border border-zinc-700/40">
        {children}
      </code>
    );
  }

  // 🎨 PROFESSIONAL CODE BLOCK - VS Code Level Quality
  return (
    <motion.div
      ref={codeBlockRef}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="group relative my-6 rounded-xl overflow-hidden border border-zinc-800/50 shadow-2xl w-full max-w-full"
      style={{
        background: '#0A0A0A', // Professional dark background
        borderRadius: '10px', // Rounded corners
        boxShadow: '0 8px 32px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.05)',
        maxWidth: '100%', // Never exceed parent width
      }}
    >
      {/* 🎯 Professional Header Bar */}
      <div
        className="relative flex items-center justify-between px-5 py-3 border-b border-zinc-700/30"
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(6px)'
        }}
      >
        {/* Left: Language and line count */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold text-zinc-200 tracking-wide">
            {displayLanguage && displayLanguage !== "text" ? displayLanguage.toUpperCase() : "CODE"}
          </span>
          <div className="text-xs text-zinc-400 font-mono">
            {lineCount} {lineCount === 1 ? 'line' : 'lines'}
          </div>
        </div>

        {/* Right: Copy button */}
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleCopy}
                className={cn(
                  "relative p-2 rounded-lg transition-all duration-200",
                  "hover:bg-zinc-700/50 hover:scale-105 active:scale-95",
                  copied ? "bg-emerald-500/20 text-emerald-400" : "text-zinc-400 hover:text-zinc-200"
                )}
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span className="absolute inset-0 rounded-lg bg-emerald-400/20 animate-ping" />
                  </>
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs py-1 px-2.5 bg-zinc-900 border-zinc-700 font-medium">
              {copied ? "Copied!" : "Copy code"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* 💎 PROFESSIONAL CODE CONTAINER */}
      <div
        className="relative overflow-hidden w-full"
        style={{
          background: '#0A0A0A',
          maxHeight: '650px',
          maxWidth: '100%',
        }}
      >
        <div className="overflow-x-auto overflow-y-auto h-full w-full" style={{ maxHeight: '650px', maxWidth: '100%' }}>
          <Highlight
            code={beautifiedCode || children || ''}
            language={displayLanguage}
            theme={professionalTheme}
          >
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
              <pre
                className={cn(className, "professional-code-pre")}
                style={{
                  ...style,
                  margin: 0,
                  padding: '20px', // Professional padding
                  background: '#0A0A0A', // Professional dark background
                  fontSize: '14px',
                  lineHeight: '1.6', // Perfect spacing between lines
                  fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", "SF Mono", Consolas, Monaco, monospace',
                  whiteSpace: 'pre',
                  wordWrap: 'normal',
                  overflowWrap: 'normal',
                  tabSize: 4,
                  MozTabSize: 4,
                  fontVariantLigatures: 'common-ligatures',
                  fontFeatureSettings: '"liga", "kern", "calt"',
                  borderRadius: '10px', // Rounded corners
                }}
              >
                <style>{`
                  /* 🎨 PROFESSIONAL VS CODE STYLING */
                  
                  .professional-code-pre {
                    margin: 0 !important;
                    padding: 20px !important;
                    background: #0A0A0A !important;
                    border-radius: 10px !important;
                  }
                  
                  /* 🔥 PERFECT LINE STYLING */
                  .code-line-wrapper {
                    display: flex !important;
                    width: 100% !important;
                    min-height: 1.6em !important;
                    white-space: pre !important;
                    position: relative !important;
                    transition: background-color 0.15s ease;
                    padding: 0 !important;
                  }
                  
                  .code-line-wrapper:hover {
                    background-color: rgba(255, 255, 255, 0.03) !important;
                  }
                  
                  /* Line number styling */
                  .line-number-cell {
                    flex-shrink: 0 !important;
                    min-width: 3.5em !important;
                    text-align: right !important;
                    padding-right: 1em !important;
                    padding-left: 0.5em !important;
                    color: #858585 !important;
                    opacity: 0.7 !important;
                    font-size: 13px !important;
                    line-height: 1.6 !important;
                    user-select: none !important;
                    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
                    margin-right: 1em !important;
                  }
                  
                  /* Code content cell */
                  .code-content-cell {
                    flex: 1 !important;
                    white-space: pre !important;
                    tab-size: 4 !important;
                    min-width: 0 !important;
                  }
                  
                  /* Custom scrollbar */
                  .overflow-x-auto::-webkit-scrollbar,
                  .overflow-y-auto::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                  }
                  
                  .overflow-x-auto::-webkit-scrollbar-track,
                  .overflow-y-auto::-webkit-scrollbar-track {
                    background: rgba(0, 0, 0, 0.2);
                    border-radius: 5px;
                  }
                  
                  .overflow-x-auto::-webkit-scrollbar-thumb,
                  .overflow-y-auto::-webkit-scrollbar-thumb {
                    background-color: rgba(113, 113, 122, 0.5);
                    border-radius: 5px;
                  }
                  
                  .overflow-x-auto::-webkit-scrollbar-thumb:hover,
                  .overflow-y-auto::-webkit-scrollbar-thumb:hover {
                    background-color: rgba(113, 113, 122, 0.8);
                  }
                `}</style>

                {tokens.map((line, i) => {
                  const lineProps = getLineProps({ line, key: i });

                  return (
                    <div
                      key={i}
                      {...lineProps}
                      className="code-line-wrapper"
                      data-line={i + 1}
                    >
                      {/* Line number */}
                      <div className="line-number-cell">
                        {i + 1}
                      </div>

                      {/* Code content with PROFESSIONAL VS CODE COLORS */}
                      <div className="code-content-cell">
                        {line.map((token, key) => {
                          const tokenProps = getTokenProps({ token, key });

                          // 🎨 Apply professional VS Code colors
                          const customColor = getTokenColor(token);

                          return (
                            <span
                              key={key}
                              {...tokenProps}
                              style={{
                                color: customColor, // Professional VS Code color
                                fontStyle: token.types.includes('comment') ? 'italic' : 'normal', // Italic green comments
                                whiteSpace: 'pre',
                              }}
                            />
                          );
                        })}
                        {line.length === 0 && '\\u00A0'} {/* Non-breaking space for empty lines */}
                      </div>
                    </div>
                  );
                })}
              </pre>
            )}
          </Highlight>
        </div>
      </div>
    </motion.div>
  );
};