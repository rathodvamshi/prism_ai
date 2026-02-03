import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { prism } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Code2, Save } from "lucide-react";

import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface CodeBlockProps {
  children: string;
  language?: string;
  inline?: boolean;
}

// Language detection
const detectLanguage = (code: string): string => {
  const trimmed = code.trim();

  if (trimmed.includes('public class') || trimmed.includes('public static void main')) return 'java';
  if (trimmed.includes('def ') && trimmed.includes(':')) return 'python';
  if (trimmed.includes('#include <') || trimmed.includes('int main()')) return 'cpp';
  if (trimmed.includes('<!DOCTYPE') || trimmed.includes('<html')) return 'html';
  if (trimmed.includes('<?php')) return 'php';
  if (trimmed.includes('SELECT') && trimmed.includes('FROM')) return 'sql';
  if (trimmed.includes('function') || trimmed.includes('const ') || trimmed.includes('let ')) return 'javascript';
  if (trimmed.includes('interface') || trimmed.includes('type ')) return 'typescript';

  return 'javascript';
};

// PRODUCTION-READY Code Formatter - Zero Inline Statements
const formatCode = (code: string, language: string): string => {
  try {
    // Normalize line endings
    let normalized = code
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .trim();

    if (!normalized) return '';

    const indentUnit = '    '; // 4 spaces
    const result: string[] = [];
    let indentLevel = 0;
    let lastWasEmpty = false;
    let inBlockComment = false;

    // Ultra-aggressive statement splitter
    const splitStatements = (text: string): string[] => {
      const lines: string[] = [];
      const rawLines = text.split('\n');

      for (let line of rawLines) {
        const trimmed = line.trim();

        if (!trimmed) {
          lines.push('');
          continue;
        }

        // Never split comments
        if (trimmed.startsWith('//') || trimmed.startsWith('/*') ||
          trimmed.startsWith('*') || trimmed.startsWith('*/')) {
          lines.push(trimmed);
          continue;
        }

        // Split by semicolons intelligently
        let statements: string[] = [];
        let inString = false;
        let stringChar = '';
        let depth = 0;
        let current = '';

        for (let i = 0; i < trimmed.length; i++) {
          const char = trimmed[i];
          const prev = i > 0 ? trimmed[i - 1] : '';

          // Track strings
          if ((char === '"' || char === "'") && prev !== '\\') {
            if (!inString) {
              inString = true;
              stringChar = char;
            } else if (char === stringChar) {
              inString = false;
            }
          }

          // Track brackets/parens
          if (!inString) {
            if (char === '(' || char === '[' || char === '{') depth++;
            if (char === ')' || char === ']' || char === '}') depth--;
          }

          current += char;

          // Split at semicolon only if balanced and not in string
          if (char === ';' && !inString && depth === 0) {
            if (current.trim()) {
              statements.push(current.trim());
            }
            current = '';
          }
        }

        // Add remaining
        if (current.trim()) {
          statements.push(current.trim());
        }

        // Add all statements
        if (statements.length > 0) {
          statements.forEach(stmt => {
            if (stmt.trim()) lines.push(stmt.trim());
          });
        }
      }

      return lines;
    };

    const lines = splitStatements(normalized);

    // Format with perfect indentation and spacing
    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();

      // Handle empty lines
      if (!trimmed) {
        if (!lastWasEmpty) {
          result.push('');
          lastWasEmpty = true;
        }
        continue;
      }

      lastWasEmpty = false;
      const currentIndent = indentUnit.repeat(Math.max(0, indentLevel));

      // Handle single-line comments
      if (trimmed.startsWith('//')) {
        // Add spacing before comment
        if (result.length > 0 && result[result.length - 1] !== '') {
          result.push('');
        }
        result.push(`${currentIndent}// ${trimmed.substring(2).trim()}`);
        continue;
      }

      // Handle block comment start
      if (trimmed.startsWith('/**') || trimmed.startsWith('/*')) {
        if (result.length > 0 && result[result.length - 1] !== '') {
          result.push('');
        }

        result.push(`${currentIndent}/**`);
        inBlockComment = true;

        // Check if it's a single-line block comment
        if (trimmed.includes('*/')) {
          const content = trimmed.substring(trimmed.indexOf('/*') + 2, trimmed.indexOf('*/')).trim();
          if (content) {
            result.push(`${currentIndent} * ${content}`);
          }
          result.push(`${currentIndent} */`);
          result.push('');
          inBlockComment = false;
        }
        continue;
      }

      // Handle block comment content
      if (inBlockComment || trimmed.startsWith('*')) {
        if (trimmed.includes('*/')) {
          const content = trimmed.substring(0, trimmed.indexOf('*/')).replace(/^\*\s*/, '').trim();
          if (content) {
            result.push(`${currentIndent} * ${content}`);
          }
          result.push(`${currentIndent} */`);
          result.push('');
          inBlockComment = false;
        } else {
          const content = trimmed.replace(/^\*\s*/, '').trim();
          if (content) {
            result.push(`${currentIndent} * ${content}`);
          } else {
            result.push(`${currentIndent} *`);
          }
        }
        continue;
      }

      // Handle opening braces
      if (trimmed.includes('{') && !trimmed.includes('}')) {
        const parts = trimmed.split('{');
        const beforeBrace = parts[0].trim();

        if (beforeBrace) {
          result.push(`${currentIndent}${beforeBrace} {`);
        } else {
          result.push(`${currentIndent}{`);
        }

        indentLevel++;

        // Add spacing after method/class declarations
        if (beforeBrace.match(/\b(public|private|protected|class|interface|static|void|int|String)\b/)) {
          result.push('');
        }
        continue;
      }

      // Handle closing braces
      if (trimmed.includes('}')) {
        const parts = trimmed.split('}');
        const beforeBrace = parts[0].trim();

        if (beforeBrace) {
          result.push(`${currentIndent}${beforeBrace}`);
        }

        indentLevel = Math.max(0, indentLevel - 1);
        const braceIndent = indentUnit.repeat(indentLevel);
        result.push(`${braceIndent}}`);

        // Add spacing after closing brace
        if (i + 1 < lines.length && lines[i + 1].trim() && !lines[i + 1].trim().startsWith('}')) {
          result.push('');
        }
        continue;
      }

      // Regular code line
      result.push(`${currentIndent}${trimmed}`);
    }

    return result.join('\n');
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[CodeBlock] Formatting error:', error);
    }
    return code; // Return original on error
  }
};

export const CodeBlock = React.memo(({ children, language = "javascript", inline = false }: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  const [highlightedLine, setHighlightedLine] = useState<number | null>(null);
  const [highlights, setHighlights] = useState<Array<{
    id: string;
    text: string;
    color: string;
    timestamp: number;
  }>>([]);
  const [showSidebar, setShowSidebar] = useState(false);

  // Theme detection
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    // Check if dark theme is active
    const checkTheme = () => {
      const isDark = document.documentElement.classList.contains('dark') ||
        document.documentElement.getAttribute('data-theme') === 'dark';
      setIsDarkTheme(isDark);
    };

    checkTheme();

    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-theme']
    });

    return () => observer.disconnect();
  }, []);

  const containerRef = useRef<HTMLDivElement>(null);
  const formattedCodeCache = useRef<Map<string, string>>(new Map());

  // Load highlights from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('code-highlights');
    if (stored) {
      try {
        setHighlights(JSON.parse(stored));
      } catch (e) {
        if (process.env.NODE_ENV === 'development') {
          console.error('[CodeBlock] Failed to load highlights:', e);
        }
      }
    }
  }, []);

  // Auto-detect language if not specified
  const detectedLanguage = useMemo(() => {
    if (language && language !== 'text') return language;
    return detectLanguage(children);
  }, [children, language]);

  // Cached formatting - prevents re-formatting on parent re-renders
  const formattedCode = useMemo(() => {
    const cacheKey = `${detectedLanguage}:${children}`;

    // Return cached version if available
    if (formattedCodeCache.current.has(cacheKey)) {
      return formattedCodeCache.current.get(cacheKey)!;
    }

    // Format and cache
    try {
      const formatted = formatCode(children, detectedLanguage);
      formattedCodeCache.current.set(cacheKey, formatted);

      // Limit cache size to prevent memory issues
      if (formattedCodeCache.current.size > 50) {
        const firstKey = formattedCodeCache.current.keys().next().value;
        formattedCodeCache.current.delete(firstKey);
      }

      return formatted;
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[CodeBlock] Formatting failed:', error);
      }
      return children;
    }
  }, [children, detectedLanguage]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[CodeBlock] Copy failed:', error);
      }
    }
  }, [children]);

  const handleDownload = useCallback(() => {
    try {
      const blob = new Blob([children], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `code.${detectedLanguage}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[CodeBlock] Download failed:', error);
      }
    }
  }, [children, detectedLanguage]);

  // Line highlight handler
  const handleLineClick = useCallback((lineNumber: number) => {
    setHighlightedLine(lineNumber);
    setTimeout(() => setHighlightedLine(null), 2000);
  }, []);

  // Clear selection
  // Remove highlight
  const removeHighlight = useCallback((id: string) => {
    // Remove from DOM
    const span = document.querySelector(`[data-highlight-id="${id}"]`);
    if (span && span.parentNode) {
      const text = span.textContent || '';
      span.parentNode.replaceChild(document.createTextNode(text), span);
    }

    // Update state and save
    setHighlights(prev => {
      const updated = prev.filter(h => h.id !== id);
      requestIdleCallback(() => {
        localStorage.setItem('code-highlights', JSON.stringify(updated));
      });
      return updated;
    });
  }, []);



  if (inline) {
    return (
      <code
        data-code-block="true"
        className="px-1 py-0.5 rounded bg-zinc-800/80 text-cyan-400 text-[12px] sm:text-[13px] font-mono border border-zinc-700/50"
        onMouseUp={(e) => e.stopPropagation()}
      >
        {children}
      </code>
    );
  }

  return (
    <div
      ref={containerRef}
      data-code-block="true"
      className="gpt-code-block w-full max-w-full min-w-0 my-4 rounded-xl overflow-hidden border"
      style={{
        background: 'var(--gpt-code-bg, #f7f7f8)',
        borderColor: 'var(--gpt-code-border, #e5e7eb)',
        userSelect: 'text',
        WebkitUserSelect: 'text',
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {/* Premium Glassmorphism Header */}
      <div
        className="relative flex items-center justify-between px-4 py-3 backdrop-blur-xl border-b border-zinc-800/40"
        style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01))',
        }}
      >
        {/* Gradient Accent Line */}
        <div
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899, #3b82f6)',
            backgroundSize: '200% 100%',
            animation: 'gradient-shift 8s ease infinite',
          }}
        />

        {/* Language Badge with Icon */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20">
            <Code2 className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <span className="text-sm font-semibold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent uppercase tracking-wide">
            {detectedLanguage}
          </span>
        </div>

        {/* Action Buttons with Premium Style */}
        <TooltipProvider delayDuration={200}>
          <div className="flex items-center gap-1.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleCopy}
                  className={cn(
                    "group/btn p-2 rounded-lg transition-all duration-200",
                    "hover:bg-white/5 active:scale-95",
                    "border border-transparent hover:border-white/10",
                    copied ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "text-zinc-400 hover:text-white"
                  )}
                >
                  {copied ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4 group-hover/btn:scale-110 transition-transform" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent
                side="bottom"
                className="bg-zinc-900/95 backdrop-blur-xl border-zinc-700/50 text-xs font-medium"
              >
                {copied ? "✓ Copied!" : "Copy code"}
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleDownload}
                  className={cn(
                    "group/btn p-2 rounded-lg transition-all duration-200",
                    "hover:bg-white/5 active:scale-95",
                    "border border-transparent hover:border-white/10",
                    saved ? "bg-blue-500/10 border-blue-500/30 text-blue-400" : "text-zinc-400 hover:text-white"
                  )}
                >
                  {saved ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Save className="w-4 h-4 group-hover/btn:scale-110 transition-transform" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent
                side="bottom"
                className="bg-zinc-900/95 backdrop-blur-xl border-zinc-700/50 text-xs font-medium"
              >
                {saved ? "✓ Saved!" : "Download"}
              </TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>

      {/* Gradient Animation Keyframes */}
      <style>{`
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
      `}</style>

      {/* GPT-Style Code Container */}
      <div className="gpt-code-content overflow-x-auto">
        <SyntaxHighlighter
          key={`code-${children.length}-${detectedLanguage}`}
          language={detectedLanguage}
          style={vscDarkPlus}
          showLineNumbers={true}
          wrapLines={true}
          wrapLongLines={false}
          useInlineStyles={true}
          PreTag="div"
          data-code-block="true"
          className="syntax-highlighter-code text-xs sm:text-sm"
          lineProps={(lineNumber) => ({
            style: {
              display: 'block',
              minHeight: '1.5em',
              backgroundColor: highlightedLine === lineNumber ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
              borderLeft: highlightedLine === lineNumber ? '3px solid #3b82f6' : '3px solid transparent',
              paddingLeft: highlightedLine === lineNumber ? '8px' : '0px',
            }
          })}
          customStyle={{
            margin: 0,
            padding: '14px',
            background: 'var(--gpt-code-bg, #f7f7f8)',
            fontSize: '14px',
            lineHeight: '1.6',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            color: 'var(--gpt-code-text, #111827)',
            borderRadius: 0,
            whiteSpace: 'pre',
            overflowX: 'auto',
          }}
          lineNumberStyle={{
            minWidth: '2.5em',
            paddingRight: '0.75em',
            color: 'var(--gpt-line-num, #9ca3af)',
            userSelect: 'none',
            borderRight: '1px solid rgba(59, 130, 246, 0.1)',
            marginRight: '1.25em',
            textAlign: 'right',
            fontSize: '12px',
            display: 'inline-block',
            opacity: 0.6,
          }}
          codeTagProps={{
            style: {
              whiteSpace: 'pre',
              wordBreak: 'keep-all',
              overflowWrap: 'normal',
              fontVariantLigatures: 'common-ligatures',
              maxWidth: '100%',
            }
          }}
        >
          {formattedCode}
        </SyntaxHighlighter>

        {/* GPT-Style Code Block Styling */}
        <style>{`
            /* ===== GPT-STYLE CSS VARIABLES ===== */
            :root {
              --gpt-code-bg: #1f1f1f;
              --gpt-code-border: #404040;
              --gpt-header-bg: #2d2d2d;
              --gpt-code-text: #e5e7eb;
              --gpt-lang-color: #9ca3af;
              --gpt-line-num: #6b7280;
            }
            
            /* Dark Mode - GPT Accurate */
            .dark, [data-theme="dark"] {
              --gpt-code-bg: #0f0f0f;
              --gpt-code-border: #262626;
              --gpt-header-bg: #171717;
              --gpt-code-text: #e5e7eb;
              --gpt-lang-color: #9ca3af;
              --gpt-line-num: #6b7280;
            }
            
            /* ===== MOBILE OPTIMIZATION ===== */
            @media (max-width: 768px) {
              .gpt-code-block pre {
                font-size: 12px !important;
                padding: 10px !important;
                max-height: 50vh;
              }
              
              .gpt-code-header {
                padding: 8px 10px !important;
              }
            }
            
            /* ===== CLEAN SELECTION (NO GRADIENTS) ===== */
            .gpt-code-block *::selection {
              background: rgba(59, 130, 246, 0.2) !important;
              color: inherit !important;
            }
            
            /* ===== TEXT SELECTION ENABLED ===== */
            .gpt-code-block,
            .gpt-code-block *,
            .gpt-code-block pre,
            .gpt-code-block code {
              -webkit-user-select: text !important;
              user-select: text !important;
            }
            
            /* ===== HORIZONTAL SCROLL ONLY ===== */
            .gpt-code-content {
              overflow-x: auto;
              overflow-y: hidden;
            }
            
            /* ===== CLEAN SCROLLBAR ===== */
            .gpt-code-content::-webkit-scrollbar {
              height: 8px;
            }
            
            .gpt-code-content::-webkit-scrollbar-track {
              background: transparent;
            }
            
            .gpt-code-content::-webkit-scrollbar-thumb {
              background: rgba(0, 0, 0, 0.2);
              border-radius: 4px;
            }
            
            .dark .gpt-code-content::-webkit-scrollbar-thumb {
              background: rgba(255, 255, 255, 0.2);
            }
            
            /* ===== REMOVE OLD STYLES ===== */
            .code-block-container *::selection,
            .code-block-container::selection,
            .code-block-container *::-webkit-selection,
            .code-block-container::-webkit-selection {
              background: rgba(59, 130, 246, 0.2) !important;
              color: inherit !important;
            }
            
            /* Enable text selection everywhere */
            .code-block-container,
            .code-block-container *,
            .code-block-container pre,
            .code-block-container code,
            .code-block-container span {
              -webkit-user-select: text !important;
              -moz-user-select: text !important;
              -ms-user-select: text !important;
              user-select: text !important;
            }
            
            /* Prevent pointer-events from blocking selection */
            .code-block-container * {
              pointer-events: auto !important;
            }
            
            /* Smooth scroll with padding */
            .code-block-container > div {
              scroll-padding-left: 1rem;
              scroll-padding-right: 1rem;
            }
            
            /* Maximum stability - prevent any repaints */
            .code-block-container {
              contain: strict;
              content-visibility: auto;
            }
            
            .code-block-container * {
              backface-visibility: hidden;
              perspective: 1000px;
            }
            
            /* Comments - Clean green, no background */
            .code-block-container .token.comment,
            .code-block-container .token.prolog,
            .code-block-container .token.doctype,
            .code-block-container .token.cdata {
              color: #6A9955 !important;
              font-style: italic;
            }
            
            /* Block comments - no background */
            .code-block-container .token.block-comment {
              color: #6A9955 !important;
              font-style: italic;
            }
            
            /* Keywords - Blue */
            .code-block-container .token.keyword {
              color: #569CD6 !important;
              font-weight: 600;
            }
            
            /* Strings - Bright Orange */
            .code-block-container .token.string {
              color: #FFB86C !important;
            }
            
            /* Functions - Aqua */
            .code-block-container .token.function,
            .code-block-container .token.method {
              color: #4EC9B0 !important;
              font-weight: 500;
            }
            
            /* Numbers */
            .code-block-container .token.number {
              color: #B5CEA8 !important;
            }
            
            /* Class names - Aqua */
            .code-block-container .token.class-name {
              color: #4EC9B0 !important;
              font-weight: 600;
            }
            
            /* Operators and punctuation */
            .code-block-container .token.operator,
            .code-block-container .token.punctuation {
              color: #D4D4D4 !important;
            }
            
            /* Booleans and constants */
            .code-block-container .token.boolean,
            .code-block-container .token.constant {
              color: #569CD6 !important;
            }
            
            /* Variables */
            .code-block-container .token.variable {
              color: #9CDCFE !important;
            }
            
            /* Parameters */
            .code-block-container .token.parameter {
              color: #9CDCFE !important;
            }
            
            /* Annotations */
            .code-block-container .token.annotation,
            .code-block-container .token.decorator {
              color: #DCDCAA !important;
            }
            
            /* Code structure */
            .code-block-container code {
              display: block;
              white-space: pre;
              font-feature-settings: "liga" 1, "calt" 1;
              -webkit-font-smoothing: antialiased;
              -moz-osx-font-smoothing: grayscale;
              text-rendering: optimizeLegibility;
            }
            
            /* Line numbers */
            .code-block-container .linenumber {
              min-width: 3.5em;
              text-align: right;
            }
            
            /* Premium line hover effect */
            .code-block-container .token-line {
              transition: all 0.2s ease;
              border-left: 2px solid transparent;
              padding-left: 0.5rem;
              margin-left: -0.5rem;
            }
            
            .code-block-container .token-line:hover {
              background: linear-gradient(90deg, rgba(59, 130, 246, 0.05), transparent) !important;
              border-left-color: rgba(59, 130, 246, 0.3);
            }
            
            /* Golden bracket highlighting */
            .code-block-container .token.punctuation.brace,
            .code-block-container .token.punctuation.bracket {
              color: #FFD700 !important;
              font-weight: 700;
            }
            
            /* Tags for HTML/XML */
            .code-block-container .token.tag {
              color: #569CD6 !important;
            }
            
            /* Attributes */
            .code-block-container .token.attr-name {
              color: #9CDCFE !important;
            }
            
            /* Properties */
            .code-block-container .token.property {
              color: #9CDCFE !important;
            }
            
            /* Regex */
            .code-block-container .token.regex {
              color: #D16969 !important;
            }
            
            /* Horizontal scrollbar styling - Always visible when needed */
            .code-block-container {
              scrollbar-width: thin;
              scrollbar-color: rgba(120, 120, 120, 0.6) transparent;
              overflow-x: auto;
              overflow-y: hidden;
              scroll-behavior: smooth;
              max-width: 100%;
              width: 100%;
            }
            
            .code-block-container > div {
              scrollbar-width: thin;
              scrollbar-color: rgba(120, 120, 120, 0.6) transparent;
              overflow-x: auto;
              overflow-y: hidden;
              scroll-behavior: smooth;
              max-width: 100%;
              width: 100%;
            }
            
            /* Visible horizontal scrollbar - 6px height for better visibility */
            .code-block-container::-webkit-scrollbar,
            .code-block-container > div::-webkit-scrollbar {
              height: 6px !important;
              width: 0px !important;
              background: rgba(0, 0, 0, 0.2);
            }
            
            .code-block-container::-webkit-scrollbar-track,
            .code-block-container > div::-webkit-scrollbar-track {
              background: rgba(0, 0, 0, 0.2);
              border-radius: 3px;
              margin: 0 8px;
            }
            
            .code-block-container::-webkit-scrollbar-thumb,
            .code-block-container > div::-webkit-scrollbar-thumb {
              background: rgba(120, 120, 120, 0.6);
              border-radius: 3px;
              transition: background 0.2s ease;
            }
            
            .code-block-container::-webkit-scrollbar-thumb:hover,
            .code-block-container > div::-webkit-scrollbar-thumb:hover {
              background: rgba(150, 150, 150, 0.8);
            }
            
            /* Always show scrollbar thumb when content overflows */
            .code-block-container::-webkit-scrollbar-thumb,
            .code-block-container > div::-webkit-scrollbar-thumb {
              background: rgba(120, 120, 120, 0.6);
            }
            
            /* Pre element - ensure dark background */
            .code-block-container pre {
              margin: 0;
              padding: 0;
              background: #1e1e1e !important;
            }
          `}</style>
      </div>

      {/* Highlights Sidebar Toggle */}
      {highlights.length > 0 && (
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="absolute top-3 right-3 z-10 px-3 py-1.5 rounded-md bg-zinc-800/90 hover:bg-zinc-700/90 border border-zinc-700/50 transition-colors flex items-center gap-2 text-xs text-zinc-400 hover:text-white backdrop-blur-sm"
          title="View Highlights"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <span className="font-medium">{highlights.length}</span>
        </button>
      )}

      {/* Highlights Sidebar */}
      {showSidebar && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
            onClick={() => setShowSidebar(false)}
          />

          {/* Sidebar Panel */}
          <div className="fixed right-0 top-0 h-full w-80 bg-zinc-900 border-l border-zinc-800 shadow-2xl z-50 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <h3 className="text-sm font-semibold text-white">Highlights</h3>
                <span className="text-xs text-zinc-500">({highlights.length})</span>
              </div>
              <button
                onClick={() => setShowSidebar(false)}
                className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Highlights List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {highlights.length === 0 ? (
                <div className="text-center text-zinc-500 text-sm py-8">
                  No highlights yet
                </div>
              ) : (
                highlights.map((highlight, index) => (
                  <div
                    key={highlight.id}
                    className="group relative p-3 rounded-lg bg-zinc-800/50 border border-zinc-700/50 hover:border-zinc-600 transition-all"
                  >
                    {/* Color indicator */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                      style={{ backgroundColor: highlight.color }}
                    />

                    {/* Text with exact highlight color */}
                    <div className="pl-3">
                      <p
                        className="text-sm font-mono leading-relaxed line-clamp-3"
                        style={{
                          backgroundColor: highlight.color,
                          color: '#ffffff',
                          padding: '4px 8px',
                          borderRadius: '4px'
                        }}
                      >
                        {highlight.text}
                      </p>

                      {/* Metadata */}
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-zinc-500">
                          {new Date(highlight.timestamp).toLocaleTimeString()}
                        </span>

                        {/* Remove button */}
                        <button
                          onClick={() => removeHighlight(highlight.id)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-all text-xs"
                          title="Remove"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer Actions */}
            {highlights.length > 0 && (
              <div className="px-4 py-3 border-t border-zinc-800">
                <button
                  onClick={() => {
                    if (confirm('Clear all highlights?')) {
                      setHighlights([]);
                      localStorage.removeItem('code-highlights');
                      // Remove all highlight spans from DOM
                      document.querySelectorAll('[data-highlight-id]').forEach(span => {
                        const text = span.textContent || '';
                        span.parentNode?.replaceChild(document.createTextNode(text), span);
                      });
                    }
                  }}
                  className="w-full px-3 py-2 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 hover:text-red-300 text-xs font-medium transition-colors"
                >
                  Clear All Highlights
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if children or language actually changed
  return prevProps.children === nextProps.children &&
    prevProps.language === nextProps.language &&
    prevProps.inline === nextProps.inline;
});
