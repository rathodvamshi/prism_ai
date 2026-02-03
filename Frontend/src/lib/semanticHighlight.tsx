/**
 * Semantic Highlight Detection
 * 
 * Automatically detects and highlights important content in AI responses:
 * - Semantic labels (Important:, ⚠️ Warning:, etc.)
 * - Bold text (**text**)
 * - Inline code (`code`)
 * - Keyboard shortcuts (Ctrl+C, Cmd+V, etc.)
 * - Links and URLs
 * - Key terms and definitions
 */

import React from "react";

export interface SemanticHighlight {
  start: number;
  end: number;
  label: string;
  type: 'label' | 'bold' | 'code' | 'number' | 'keyword' | 'link' | 'kbd';
  url?: string;
}

/**
 * Strip markdown syntax from text to get rendered output
 * This matches what the user sees in the DOM after markdown rendering
 */
export function stripMarkdown(content: string): string {
  if (!content) return "";
  let stripped = content;
  
  // 1. Remove bold markers **text** → text
  stripped = stripped.replace(/\*\*([^*]+)\*\*/g, '$1');
  // 2. Remove italic markers *text* or _text_ → text
  stripped = stripped.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '$1');
  stripped = stripped.replace(/_([^_]+)_/g, '$1');
  // 3. Remove inline code backticks `code` → code
  stripped = stripped.replace(/`([^`]+)`/g, '$1');
  // 4. Remove strikethrough ~~text~~ → text
  stripped = stripped.replace(/~~([^~]+)~~/g, '$1');
  // 5. Remove headers # ## ### etc (keep the text)
  stripped = stripped.replace(/^#{1,6}\s+/gm, '');
  // 6. Remove link syntax [text](url) → text
  stripped = stripped.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  
  return stripped;
}

// Semantic label patterns
const SEMANTIC_LABELS = [
  { pattern: /^Important:\s*/i },
  { pattern: /^⚠️\s*Warning:\s*/i },
  { pattern: /^✅\s*Best Practice:\s*/i },
  { pattern: /^🔑\s*Key Point:\s*/i },
  { pattern: /^📌\s*Note:\s*/i },
  { pattern: /^🚀\s*Performance:\s*/i },
  { pattern: /^❌\s*Mistake:\s*/i },
  { pattern: /^💡\s*Tip:\s*/i },
  { pattern: /^⭐\s*/i },
  { pattern: /^🎯\s*Goal:\s*/i },
  { pattern: /^📋\s*Summary:\s*/i },
  { pattern: /^🔧\s*Fix:\s*/i },
  { pattern: /^✨\s*Feature:\s*/i },
];

// Maximum length of key phrase to highlight after label
const MAX_KEY_PHRASE_LENGTH = 80;

/**
 * Detect semantic labels in text and return highlight positions
 */
export function detectSemanticHighlights(content: string): SemanticHighlight[] {
  const highlights: SemanticHighlight[] = [];
  
  // Skip if in code block
  if (content.includes('```')) {
    return highlights;
  }
  
  const lines = content.split('\n');
  let offset = 0;
  
  for (const line of lines) {
    // Skip code blocks
    if (line.trim().startsWith('```')) {
      offset += line.length + 1;
      continue;
    }
    
    // 1. Check semantic label patterns
    for (const labelConfig of SEMANTIC_LABELS) {
      const match = line.match(labelConfig.pattern);
      if (match) {
        const labelStart = offset + match.index!;
        const labelEnd = labelStart + match[0].length;
        
        const afterLabel = line.substring(match[0].length);
        const keyPhraseEnd = Math.min(afterLabel.length, MAX_KEY_PHRASE_LENGTH);
        
        let actualEnd = keyPhraseEnd;
        const sentenceEnd = afterLabel.search(/[.!?:;,]/);
        if (sentenceEnd !== -1 && sentenceEnd < keyPhraseEnd) {
          actualEnd = sentenceEnd + 1;
        }
        
        const keyPhrase = afterLabel.substring(0, actualEnd).trim();
        
        if (keyPhrase.length > 0) {
          highlights.push({
            start: labelStart,
            end: labelEnd + actualEnd,
            label: match[0].trim(),
            type: 'label'
          });
        }
        break;
      }
    }
    
    // 2. Detect bold text (**text**)
    const boldRegex = /\*\*([^*]+)\*\*/g;
    let boldMatch;
    while ((boldMatch = boldRegex.exec(line)) !== null) {
      highlights.push({
        start: offset + boldMatch.index,
        end: offset + boldMatch.index + boldMatch[0].length,
        label: boldMatch[1],
        type: 'bold'
      });
    }
    
    // 3. Detect inline code (`code`)
    const codeRegex = /`([^`]+)`/g;
    let codeMatch;
    while ((codeMatch = codeRegex.exec(line)) !== null) {
      highlights.push({
        start: offset + codeMatch.index,
        end: offset + codeMatch.index + codeMatch[0].length,
        label: codeMatch[1],
        type: 'code'
      });
    }

    // 4. Detect URLs (https://, http://, www.)
    const urlRegex = /(https?:\/\/[^\s<>"\]]+|www\.[^\s<>"\]]+)/gi;
    let urlMatch;
    while ((urlMatch = urlRegex.exec(line)) !== null) {
      const url = urlMatch[1].startsWith('www.') ? `https://${urlMatch[1]}` : urlMatch[1];
      highlights.push({
        start: offset + urlMatch.index,
        end: offset + urlMatch.index + urlMatch[0].length,
        label: urlMatch[1],
        type: 'link',
        url: url
      });
    }

    // 5. Detect keyboard shortcuts (Ctrl+C, Cmd+V, Alt+Tab, etc.)
    const kbdRegex = /\b(Ctrl|Cmd|Alt|Shift|Option|Meta|Super|Win|Enter|Esc|Tab|Space|Delete|Backspace|Home|End|Page\s?Up|Page\s?Down|Arrow\s?(?:Up|Down|Left|Right)|F[1-9]|F1[0-2]?)(?:\s*\+\s*(Ctrl|Cmd|Alt|Shift|Option|Meta|[A-Z0-9]))*\b/gi;
    let kbdMatch;
    while ((kbdMatch = kbdRegex.exec(line)) !== null) {
      highlights.push({
        start: offset + kbdMatch.index,
        end: offset + kbdMatch.index + kbdMatch[0].length,
        label: kbdMatch[0],
        type: 'kbd'
      });
    }
    
    offset += line.length + 1;
  }
  
  // Remove overlapping highlights (prefer bold over code)
  return deduplicateHighlights(highlights);
}

/**
 * Remove overlapping highlights
 */
function deduplicateHighlights(highlights: SemanticHighlight[]): SemanticHighlight[] {
  if (highlights.length <= 1) return highlights;
  
  const sorted = [...highlights].sort((a, b) => a.start - b.start);
  const result: SemanticHighlight[] = [sorted[0]];
  
  for (let i = 1; i < sorted.length; i++) {
    const current = sorted[i];
    const last = result[result.length - 1];
    
    // Skip if overlapping
    if (current.start < last.end) {
      continue;
    }
    
    result.push(current);
  }
  
  return result;
}

/**
 * Apply semantic highlights to text content
 * Returns React nodes with styled highlight spans
 */
export function applySemanticHighlights(
  content: string,
  highlights: SemanticHighlight[]
): React.ReactNode[] {
  if (highlights.length === 0) {
    return [content];
  }
  
  const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);
  
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let keyCounter = 0;
  
  for (const highlight of sortedHighlights) {
    // Add text before highlight
    if (highlight.start > lastIndex) {
      parts.push(content.substring(lastIndex, highlight.start));
    }
    
    // Get the highlighted text
    let highlightedText = content.substring(highlight.start, highlight.end);
    
    // Style based on type
    let className = "";
    let displayText = highlightedText;
    let isLink = false;
    let linkUrl = "";
    
    switch (highlight.type) {
      case 'bold':
        // Remove ** markers and make bold
        displayText = highlightedText.replace(/\*\*/g, '');
        className = "font-bold text-foreground";
        break;
      case 'code':
        // Remove backticks and style as inline code
        displayText = highlightedText.replace(/`/g, '');
        className = "px-1.5 py-0.5 bg-muted/80 text-primary font-mono text-[13px] rounded-md border border-border/50";
        break;
      case 'label':
        className = "font-semibold text-primary/90 bg-primary/10 px-1 py-0.5 rounded";
        break;
      case 'kbd':
        // Style as keyboard shortcut
        className = "px-1.5 py-0.5 bg-muted text-foreground/90 font-mono text-[12px] rounded-md border border-border shadow-sm font-medium";
        break;
      case 'link':
        isLink = true;
        linkUrl = highlight.url || highlightedText;
        className = "text-primary hover:text-primary/80 underline underline-offset-2 decoration-primary/40 hover:decoration-primary/80 transition-colors cursor-pointer";
        break;
      default:
        className = "font-semibold";
    }

    if (isLink) {
      parts.push(
        <a 
          key={`semantic-${keyCounter++}`} 
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={className}
          onClick={(e) => e.stopPropagation()}
        >
          {displayText}
        </a>
      );
    } else {
      parts.push(
        <span key={`semantic-${keyCounter++}`} className={className}>
          {displayText}
        </span>
      );
    }
    
    lastIndex = highlight.end;
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }
  
  return parts.length > 0 ? parts : [content];
}

