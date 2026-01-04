/**
 * Semantic Highlight Detection
 * 
 * Detects semantic labels (Important:, ⚠️ Warning:, ✅ Best Practice:, etc.)
 * and returns positions for highlighting only the label + key phrase
 */

import React from "react";

export interface SemanticHighlight {
  start: number;
  end: number;
  label: string;
}

// Allowed semantic label patterns
// Semantic labels for highlighting: label + key phrase only
const SEMANTIC_LABELS = [
  { pattern: /^Important:\s*/i },
  { pattern: /^⚠️\s*Warning:\s*/i },
  { pattern: /^✅\s*Best Practice:\s*/i },
  { pattern: /^🔑\s*Key Point:\s*/i },
  { pattern: /^📌\s*Note:\s*/i },
  { pattern: /^🚀\s*Performance:\s*/i },
  { pattern: /^❌\s*Mistake:\s*/i },
];

// Maximum length of key phrase to highlight after label
const MAX_KEY_PHRASE_LENGTH = 80;

/**
 * Detect semantic labels in text and return highlight positions
 * Only highlights the label + short key phrase, not entire paragraphs
 */
export function detectSemanticHighlights(content: string): SemanticHighlight[] {
  const highlights: SemanticHighlight[] = [];
  const lines = content.split('\n');
  
  let offset = 0;
  
  for (const line of lines) {
    // Skip code blocks
    if (line.trim().startsWith('```')) {
      offset += line.length + 1; // +1 for newline
      continue;
    }
    
    // Check each semantic label pattern
    for (const labelConfig of SEMANTIC_LABELS) {
      const match = line.match(labelConfig.pattern);
      if (match) {
        const labelStart = offset + match.index!;
        const labelEnd = labelStart + match[0].length;
        
        // Extract key phrase (up to MAX_KEY_PHRASE_LENGTH chars after label)
        const afterLabel = line.substring(match[0].length);
        const keyPhraseEnd = Math.min(
          afterLabel.length,
          MAX_KEY_PHRASE_LENGTH
        );
        
        // Find end of key phrase (end of sentence, comma, or colon, or max length)
        let actualEnd = keyPhraseEnd;
        const sentenceEnd = afterLabel.search(/[.!?:;,]/);
        if (sentenceEnd !== -1 && sentenceEnd < keyPhraseEnd) {
          actualEnd = sentenceEnd + 1;
        }
        
        // Extract the key phrase
        const keyPhrase = afterLabel.substring(0, actualEnd).trim();
        
        // Only highlight if there's actual content after the label
        if (keyPhrase.length > 0) {
          highlights.push({
            start: labelStart,
            end: labelEnd + actualEnd,
            label: match[0].trim(),
          });
        }
        
        // Only match first label per line
        break;
      }
    }
    
    offset += line.length + 1; // +1 for newline
  }
  
  return highlights;
}

/**
 * Apply semantic highlights to text content
 * Returns React nodes with highlight spans
 */
export function applySemanticHighlights(
  content: string,
  highlights: SemanticHighlight[]
): React.ReactNode[] {
  if (highlights.length === 0) {
    return [content];
  }
  
  // Sort highlights by start position
  const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);
  
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let keyCounter = 0;
  
  for (const highlight of sortedHighlights) {
    // Add text before highlight
    if (highlight.start > lastIndex) {
      parts.push(content.substring(lastIndex, highlight.start));
    }
    
    // Add highlighted text
    const highlightedText = content.substring(highlight.start, highlight.end);
    parts.push(
      <span key={`semantic-${keyCounter++}`} className="highlight">
        {highlightedText}
      </span>
    );
    
    lastIndex = highlight.end;
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }
  
  return parts.length > 0 ? parts : [content];
}

