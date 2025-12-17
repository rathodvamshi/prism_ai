import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
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
  const [selection, setSelection] = useState<{
    text: string;
    range: Range | null;
    rect: DOMRect | null;
  } | null>(null);
  const [showColorPopup, setShowColorPopup] = useState(false);
  const [highlights, setHighlights] = useState<Array<{
    id: string;
    text: string;
    color: string;
    timestamp: number;
  }>>([])
  const [showSidebar, setShowSidebar] = useState(false);
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
  
  // Capture selection and show popup (GPT-like behavior)
  const handleTextSelection = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
      setSelection(null);
      setShowColorPopup(false);
      return;
    }
    
    const range = sel.getRangeAt(0);
    const selectedText = sel.toString().trim();
    
    if (!selectedText || selectedText.length === 0) {
      setSelection(null);
      setShowColorPopup(false);
      return;
    }
    
    // Get selection bounding rectangle
    const rect = range.getBoundingClientRect();
    
    // Save selection data
    setSelection({
      text: selectedText,
      range: range.cloneRange(),
      rect: rect
    });
    
    setShowColorPopup(true);
  }, []);
  
  // Clear selection
  const clearSelection = useCallback(() => {
    setSelection(null);
    setShowColorPopup(false);
    window.getSelection()?.removeAllRanges();
  }, []);
  
  // Apply color to selected text with instant save
  const applyColor = useCallback((color: string) => {
    if (!selection?.range || !selection?.text) return;
    
    // Create highlight object
    const highlight = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      text: selection.text,
      color: color,
      timestamp: Date.now()
    };
    
    // Wrap selection in colored span with data-highlight-id
    const span = document.createElement('span');
    span.setAttribute('data-highlight-id', highlight.id);
    span.style.backgroundColor = color;
    span.style.color = '#ffffff';
    span.style.padding = '2px 4px';
    span.style.borderRadius = '3px';
    span.style.display = 'inline';
    span.style.transition = 'all 0.15s ease';
    
    try {
      selection.range.surroundContents(span);
    } catch (e) {
      // Fallback for complex selections
      const contents = selection.range.extractContents();
      span.appendChild(contents);
      selection.range.insertNode(span);
    }
    
    // Update state and save instantly (batched with requestIdleCallback for performance)
    setHighlights(prev => {
      const updated = [...prev, highlight];
      // Save to localStorage instantly
      requestIdleCallback(() => {
        localStorage.setItem('code-highlights', JSON.stringify(updated));
      });
      return updated;
    });
    
    clearSelection();
  }, [selection, clearSelection]);
  
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
      <code className="px-1 sm:px-1.5 py-0.5 rounded bg-zinc-800/80 text-cyan-400 text-[12px] sm:text-[13px] font-mono border border-zinc-700/50">
        {children}
      </code>
    );
  }

  return (
    <div
        ref={containerRef}
        className={cn(
          "group relative my-2 sm:my-4 rounded-md sm:rounded-lg overflow-hidden border",
          "border-zinc-800/50 bg-[#1e1e1e]",
          "shadow-lg"
        )}
        style={{
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
          userSelect: 'text',
          WebkitUserSelect: 'text'
        }}
        onMouseUp={(e) => {
          e.stopPropagation();
          setTimeout(handleTextSelection, 10);
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Premium Header with macOS style */}
        <div className="flex items-center justify-between px-2 sm:px-4 py-1.5 sm:py-2 bg-gradient-to-r from-[#2d2d30] to-[#252526] border-b border-zinc-800/50">
          <div className="flex items-center gap-2 sm:gap-3">
            {/* macOS traffic lights */}
            <div className="hidden sm:flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57] hover:bg-[#ff6e65] transition-all cursor-pointer hover:scale-110" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e] hover:bg-[#ffc93d] transition-all cursor-pointer hover:scale-110" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#28c840] hover:bg-[#37d74f] transition-all cursor-pointer hover:scale-110" />
            </div>
            
            {/* Language badge */}
            <div className="flex items-center gap-1.5 sm:gap-2 px-1.5 sm:px-2 py-0.5 rounded-md bg-zinc-800/40">
              <Code2 className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-zinc-500" />
              <span className="text-[10px] sm:text-[11px] font-semibold text-zinc-400 uppercase tracking-wide">
                {detectedLanguage}
              </span>
            </div>
          </div>
          
          {/* Compact Toolkit */}
          <TooltipProvider delayDuration={200}>
            <div className="flex items-center gap-0.5 sm:gap-1 bg-zinc-800/30 rounded-md p-0.5">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleCopy}
                    className={cn(
                      "p-1 sm:p-1.5 rounded transition-all duration-200",
                      "hover:bg-zinc-700/60 active:scale-95",
                      copied ? "text-emerald-400 bg-emerald-500/10" : "text-zinc-400 hover:text-zinc-200"
                    )}
                  >
                    {copied ? <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> : <Copy className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs py-1 px-2">
                  {copied ? "Copied!" : "Copy"}
                </TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleDownload}
                    className={cn(
                      "p-1 sm:p-1.5 rounded transition-all duration-200",
                      "hover:bg-zinc-700/60 active:scale-95",
                      saved ? "text-blue-400 bg-blue-500/10" : "text-zinc-400 hover:text-zinc-200"
                    )}
                  >
                    {saved ? <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> : <Save className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs py-1 px-2">
                  {saved ? "Saved!" : "Save"}
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </div>

        {/* Code Container */}
        <div className="relative code-block-container" style={{ contain: 'layout style paint', isolation: 'isolate' }}>
          <SyntaxHighlighter
            key={`code-${children.length}-${detectedLanguage}`}
            language={detectedLanguage}
            style={vscDarkPlus}
            showLineNumbers={true}
            wrapLines={true}
            wrapLongLines={false}
            useInlineStyles={true}
            PreTag="div"
            lineProps={(lineNumber) => ({
              style: {
                display: 'block',
                width: '100%',
                minHeight: '1.7em',
                backgroundColor: highlightedLine === lineNumber ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                borderLeft: highlightedLine === lineNumber ? '3px solid #3b82f6' : '3px solid transparent',
                paddingLeft: highlightedLine === lineNumber ? '8px' : '0px',
              }
            })}
            customStyle={{
              margin: 0,
              padding: '1.5rem 1.5rem',
              paddingRight: '1.5rem',
              background: '#1e1e1e',
              fontSize: '14px',
              lineHeight: '1.85',
              letterSpacing: '0.02em',
              fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", "SF Mono", Consolas, Monaco, "Courier New", monospace',
              borderRadius: 0,
              whiteSpace: 'pre',
              overflowX: 'auto',
              overflowY: 'hidden',
              height: 'auto',
              scrollPaddingLeft: '1rem',
              scrollPaddingRight: '1rem',
            }}
            lineNumberStyle={{
              minWidth: '3.5em',
              paddingRight: '1.5em',
              paddingLeft: '0.75em',
              color: '#858585',
              userSelect: 'none',
              borderRight: '1px solid #3e3e42',
              marginRight: '1.5em',
              textAlign: 'right',
              fontSize: '13px',
              display: 'inline-block',
            }}
            codeTagProps={{
              style: {
                whiteSpace: 'pre',
                wordBreak: 'keep-all',
                overflowWrap: 'normal',
                fontVariantLigatures: 'common-ligatures',
              }
            }}
          >
            {formattedCode}
          </SyntaxHighlighter>

          {/* Stable VS Code styling - No hover effects */}
          <style>{`
            /* ULTRA-STRONG Selection - Never disappears */
            .code-block-container *::selection,
            .code-block-container::selection,
            .code-block-container *::-webkit-selection,
            .code-block-container::-webkit-selection {
              background-color: #8b5cf6 !important;
              background: #8b5cf6 !important;
              color: #ffffff !important;
            }
            
            .code-block-container *::-moz-selection,
            .code-block-container::-moz-selection {
              background-color: #8b5cf6 !important;
              background: #8b5cf6 !important;
              color: #ffffff !important;
            }
            
            /* Force selection even when window loses focus */
            .code-block-container *::selection,
            .code-block-container *::-moz-selection {
              background-color: #8b5cf6 !important;
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
            
            /* Comments - Brighter Green with subtle background */
            .code-block-container .token.comment,
            .code-block-container .token.prolog,
            .code-block-container .token.doctype,
            .code-block-container .token.cdata {
              color: #6A9955 !important;
              font-style: italic;
              background: rgba(106, 153, 85, 0.05);
              padding: 0 2px;
              border-radius: 2px;
            }
            
            /* Block comments */
            .code-block-container .token.block-comment {
              background: rgba(106, 153, 85, 0.08);
              padding: 4px 8px;
              border-radius: 4px;
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
            
            /* Premium hover effect on lines */
            .code-block-container .token-line {
              transition: all 0.15s ease;
              padding: 2px 0;
              margin: 1px 0;
            }
            
            .code-block-container .token-line:hover {
              background-color: rgba(255, 255, 255, 0.05) !important;
              margin-left: -4px;
              padding-left: 4px;
              margin-right: -4px;
              padding-right: 4px;
              border-radius: 3px;
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
            
            /* Thin horizontal scrollbar at bottom only */
            .code-block-container > div {
              scrollbar-width: thin;
              scrollbar-color: #424242 #2d2d30;
              overflow-x: auto;
              overflow-y: hidden;
              scroll-behavior: smooth;
            }
            
            .code-block-container > div::-webkit-scrollbar {
              height: 6px; /* Thin horizontal scrollbar */
              width: 0px; /* No vertical scrollbar */
            }
            
            .code-block-container > div::-webkit-scrollbar-track {
              background: #2d2d30;
              border-radius: 3px;
            }
            
            .code-block-container > div::-webkit-scrollbar-thumb {
              background: #555555;
              border-radius: 3px;
              transition: background 0.2s ease;
            }
            
            .code-block-container > div::-webkit-scrollbar-thumb:hover {
              background: #666666;
            }
            
            /* Pre element */
            .code-block-container pre {
              margin: 0;
              padding: 0;
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
        
        {/* Floating Color Popup - GPT-like */}
        {showColorPopup && selection?.rect && (
          <div
            className="fixed z-[9999]"
            style={{
              left: `${selection.rect.left + selection.rect.width / 2}px`,
              top: `${selection.rect.top - 50}px`,
              transform: 'translateX(-50%)'
            }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl p-2 flex items-center gap-1.5">
              {/* Color options */}
              {[
                { color: '#fef08a', name: 'Yellow' },
                { color: '#86efac', name: 'Green' },
                { color: '#93c5fd', name: 'Blue' },
                { color: '#f9a8d4', name: 'Pink' },
                { color: '#c4b5fd', name: 'Purple' },
                { color: '#fca5a5', name: 'Red' }
              ].map(({ color, name }) => (
                <button
                  key={color}
                  onClick={() => applyColor(color)}
                  className="w-7 h-7 rounded-md transition-transform hover:scale-110 active:scale-95 border-2 border-transparent hover:border-white/30"
                  style={{ backgroundColor: color }}
                  title={name}
                />
              ))}
              
              {/* Divider */}
              <div className="w-px h-6 bg-zinc-700 mx-1" />
              
              {/* Clear button */}
              <button
                onClick={clearSelection}
                className="w-7 h-7 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors flex items-center justify-center text-zinc-400 hover:text-white"
                title="Cancel"
              >
                ×
              </button>
            </div>
            
            {/* Arrow pointer */}
            <div
              className="absolute left-1/2 -translate-x-1/2 -bottom-1.5 w-3 h-3 bg-zinc-900 border-r border-b border-zinc-700"
              style={{ transform: 'translateX(-50%) rotate(45deg)' }}
            />
          </div>
        )}
      </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if children or language actually changed
  return prevProps.children === nextProps.children && 
         prevProps.language === nextProps.language && 
         prevProps.inline === nextProps.inline;
});
