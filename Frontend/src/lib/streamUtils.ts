/**
 * 🛡️ STREAM UTILITIES
 * Centralized utilities for streaming text processing
 * Used by: api.ts, chatStore.ts, StreamingMessage.tsx
 */

// Pre-compiled regex for metadata filtering (NEVER show to users)
export const METADATA_PATTERN = /<!--\s*(?:THINKING_DATA|ACTION):.*?-->/gs;

/**
 * Creates a stateful metadata filter that handles partial tags across chunks
 */
export const createMetadataFilter = () => {
  let partialTagBuffer = '';
  
  return (text: string): string => {
    if (!text) return '';
    
    // Combine with any buffered partial tag
    const combined = partialTagBuffer + text;
    partialTagBuffer = '';
    
    // Remove complete metadata tags
    let clean = combined.replace(METADATA_PATTERN, '');
    
    // Check for partial opening tag at end (e.g., "<!--THIN")
    const partialMatch = clean.match(/<!--[^>]*$/);
    if (partialMatch) {
      partialTagBuffer = partialMatch[0];
      clean = clean.slice(0, -partialMatch[0].length);
    }
    
    return clean;
  };
};

/**
 * Simple one-shot metadata filter (for complete text)
 */
export const filterMetadata = (text: string): string => {
  if (!text) return '';
  return text.replace(METADATA_PATTERN, '');
};
