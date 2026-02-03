/**
 * Highlight Utility Functions
 * 
 * Provides consistent indexing and hash generation for text highlighting system.
 * Follows golden rules:
 * - NEVER mutate message text
 * - Use absolute character offsets
 * - Generate checksums for drift detection
 * 
 * Performance optimizations:
 * - Caching for repeated operations
 * - Early returns for common cases
 * - Efficient string matching
 */

// Performance: Cache for rendered text to avoid repeated markdown stripping
const renderedTextCache = new Map<string, string>();
const MAX_CACHE_SIZE = 100; // Limit cache size to prevent memory issues

/**
 * Generate SHA-256 hash of message text for drift detection
 * 
 * @param text - The message text to hash
 * @returns Hexadecimal hash string
 */
export async function generateMessageHash(text: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(text);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Synchronous version using simple hash for client-side validation
 * Not cryptographically secure but sufficient for drift detection
 */
export function generateMessageHashSync(text: string): string {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
        const char = text.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).padStart(16, '0');
}

/**
 * Validate highlight indexes against message text
 * 
 * Rules:
 * - 0 <= startIndex < endIndex <= text.length
 * - extracted text must match provided text
 * 
 * Uses RENDERED text (markdown stripped) for validation since that's what 
 * the user sees and selects in the DOM.
 * 
 * @returns { valid, error?, correctedIndexes? }
 */
export function validateHighlightIndexes(
    messageText: string,
    startIndex: number,
    endIndex: number,
    selectedText: string
): { valid: boolean; error?: string; correctedIndexes?: { startIndex: number; endIndex: number } } {
    // Use RENDERED text for validation (this is what user sees/selects)
    const renderedText = getRenderedText(messageText);

    // Check bounds against rendered text
    if (startIndex < 0) {
        return { valid: false, error: `startIndex cannot be negative (got ${startIndex})` };
    }

    if (endIndex > renderedText.length) {
        // Try to find the text in rendered content
        const foundIndex = renderedText.indexOf(selectedText);
        if (foundIndex !== -1) {
            console.log(`🔧 Auto-correcting: endIndex exceeded but found text at ${foundIndex}`);
            return {
                valid: true,
                correctedIndexes: { startIndex: foundIndex, endIndex: foundIndex + selectedText.length }
            };
        }
        return {
            valid: false,
            error: `endIndex (${endIndex}) exceeds rendered length (${renderedText.length})`
        };
    }

    if (startIndex >= endIndex) {
        return {
            valid: false,
            error: `Invalid range: startIndex (${startIndex}) must be < endIndex (${endIndex})`
        };
    }

    // Verify substring matches in RENDERED text at the EXACT position
    const extracted = renderedText.substring(startIndex, endIndex);
    if (extracted !== selectedText) {
        // Text mismatch - this is expected due to DOM vs regex differences
        // The calling code (chatStore) will handle position correction
        // Return mismatch info without logging errors (it's not an error, just needs correction)
        if (import.meta.env.DEV) {
            console.log(`[validateHighlightIndexes] Position mismatch detected - will auto-correct`);
        }

        return {
            valid: false,
            needsCorrection: true,
            error: `Text mismatch at position [${startIndex}:${endIndex}]`
        };
    }

    return { valid: true };
}

/**
 * Check if two highlights overlap
 */
export function highlightsOverlap(
    h1: { startIndex: number; endIndex: number },
    h2: { startIndex: number; endIndex: number }
): boolean {
    return h1.startIndex < h2.endIndex && h2.startIndex < h1.endIndex;
}

/**
 * Debug logging for highlight operations (only in development)
 */
export function logHighlightDebug(
    operation: 'CREATE' | 'DELETE' | 'LOAD' | 'VALIDATE',
    data: {
        messageId?: string;
        startIndex?: number;
        endIndex?: number;
        text?: string;
        hash?: string;
        error?: string;
    }
) {
    if (import.meta.env.DEV) {
        const prefix = operation === 'CREATE' ? '✅' : operation === 'DELETE' ? '🗑️' : operation === 'VALIDATE' ? '🔍' : '📥';
        console.log(`${prefix} [HIGHLIGHT_${operation}]`, {
            ...data,
            text: data.text ? `"${data.text.substring(0, 50)}..."` : undefined,
            hash: data.hash ? data.hash.substring(0, 16) + '...' : undefined
        });
    }
}

import { filterMetadata } from "@/lib/streamUtils";

/**
 * Clean message content by removing internal metadata (like thinking blocks)
 * Uses centralized filterMetadata from streamUtils
 */
export function cleanMessageContent(content: string): string {
    if (!content) return "";
    return filterMetadata(content).trim();
}

/**
 * Get the RENDERED text from content (strips markdown syntax)
 * This matches what the user actually sees and selects in the DOM
 * Used for highlight index validation/correction
 * 
 * Performance: Caches results to avoid repeated regex operations
 */
export function getRenderedText(content: string): string {
    if (!content) return "";
    
    // Check cache first
    const cached = renderedTextCache.get(content);
    if (cached !== undefined) {
        return cached;
    }
    
    let rendered = cleanMessageContent(content);

    // Strip markdown syntax to match rendered DOM text
    // 1. Remove bold markers **text** → text
    rendered = rendered.replace(/\*\*([^*]+)\*\*/g, '$1');
    // 2. Remove italic markers *text* or _text_ → text (but be careful with *)
    rendered = rendered.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '$1');
    rendered = rendered.replace(/_([^_]+)_/g, '$1');
    // 3. Remove inline code backticks `code` → code
    rendered = rendered.replace(/`([^`]+)`/g, '$1');
    // 4. Remove strikethrough ~~text~~ → text
    rendered = rendered.replace(/~~([^~]+)~~/g, '$1');
    // 5. Remove headers # ## ### etc (keep the text)
    rendered = rendered.replace(/^#{1,6}\s+/gm, '');
    // 6. Remove link syntax [text](url) → text
    rendered = rendered.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

    // Cache the result (with size limit)
    if (renderedTextCache.size >= MAX_CACHE_SIZE) {
        // Clear oldest entries (simple approach: clear half)
        const entries = Array.from(renderedTextCache.entries());
        entries.slice(0, Math.floor(MAX_CACHE_SIZE / 2)).forEach(([key]) => {
            renderedTextCache.delete(key);
        });
    }
    renderedTextCache.set(content, rendered);

    return rendered;
}

/**
 * Realign highlights if content has drifted
 * Attempts to find the exact text quote near the original index
 * 
 * IMPORTANT: Uses RENDERED text (markdown stripped) because that's what
 * highlight indexes are based on (DOM selection positions)
 * 
 * 🚀 Performance optimizations:
 * - Caches rendered text via getRenderedText()
 * - Uses efficient string matching algorithms
 * - Early return for valid highlights
 */
export function realignHighlights(
    content: string,
    highlights: any[]
): any[] {
    // Early return for empty inputs
    if (!content || !highlights || highlights.length === 0) {
        return highlights || [];
    }

    // Use RENDERED text (markdown stripped) - same as what user sees/selects
    // getRenderedText() handles caching internally
    const rendered = getRenderedText(content);

    // Process highlights in batch for better performance
    return highlights.map(h => {
        // Skip if already broken or invalid
        if (h._broken || !h.text || h.text.length === 0) {
            return { ...h, _broken: true };
        }

        // Validate bounds first
        if (h.startIndex < 0 || h.endIndex > rendered.length || h.startIndex >= h.endIndex) {
            // Try to find the text anywhere
            const foundIndex = rendered.indexOf(h.text);
            if (foundIndex !== -1) {
                return {
                    ...h,
                    startIndex: foundIndex,
                    endIndex: foundIndex + h.text.length,
                    _realigned: true
                };
            }
            return { ...h, _broken: true };
        }

        // 1. Check if valid as-is in RENDERED content (fast path)
        const substring = rendered.substring(h.startIndex, h.endIndex);
        if (substring === h.text) {
            return h; // Perfect match - no changes needed
        }

        // 2. Fuzzy search: Look for exact text match near the original index (± 150 chars)
        const searchRadius = 150;
        const searchStart = Math.max(0, h.startIndex - searchRadius);
        const searchEnd = Math.min(rendered.length, h.endIndex + searchRadius);
        const searchArea = rendered.substring(searchStart, searchEnd);

        const localIndex = searchArea.indexOf(h.text);
        if (localIndex !== -1) {
            const newStart = searchStart + localIndex;
            return {
                ...h,
                startIndex: newStart,
                endIndex: newStart + h.text.length,
                _realigned: true
            };
        }

        // 3. Global search fallback in RENDERED content
        const globalIndex = rendered.indexOf(h.text);
        if (globalIndex !== -1) {
            return {
                ...h,
                startIndex: globalIndex,
                endIndex: globalIndex + h.text.length,
                _realigned: true
            };
        }

        // 4. Try partial match (if text was truncated or slightly modified)
        // Look for at least 70% of the text
        const minMatchLength = Math.floor(h.text.length * 0.7);
        if (minMatchLength >= 10) {
            const partialText = h.text.substring(0, minMatchLength);
            const partialIndex = rendered.indexOf(partialText);
            if (partialIndex !== -1) {
                // Found partial match - try to extend to full word boundaries
                const potentialEnd = Math.min(rendered.length, partialIndex + h.text.length + 20);
                return {
                    ...h,
                    startIndex: partialIndex,
                    endIndex: Math.min(potentialEnd, partialIndex + h.text.length),
                    _realigned: true,
                    _partialMatch: true
                };
            }
        }

        // 5. Failed to align - mark as broken/stale
        return { ...h, _broken: true };
    });
}

/**
 * Clear the rendered text cache (call when message content changes significantly)
 */
export function clearRenderedTextCache(): void {
    renderedTextCache.clear();}