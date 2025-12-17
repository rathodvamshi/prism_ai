/**
 * Text Formatter Engine
 * Automatically formats messy AI output into clean, readable text
 */

export class TextFormatter {
  /**
   * Main formatting pipeline
   */
  static format(text: string): string {
    if (!text) return '';
    
    let formatted = text;
    formatted = this.fixMissingPeriods(formatted);
    formatted = this.fixWrongLineBreaks(formatted);
    formatted = this.createParagraphs(formatted);
    formatted = this.formatLists(formatted);
    formatted = this.spaceCodeBlocks(formatted);
    formatted = this.highlightInlineCode(formatted);
    
    return formatted;
  }

  /**
   * Add periods when missing at end of sentences
   */
  private static fixMissingPeriods(text: string): string {
    const lines = text.split('\n');
    
    return lines.map(line => {
      const trimmed = line.trim();
      if (!trimmed) return line;
      
      const lastChar = trimmed[trimmed.length - 1];
      const needsPeriod = /[a-zA-Z0-9]/.test(lastChar);
      const isListItem = /^[\d\-\*\+]/.test(trimmed);
      
      if (needsPeriod && !isListItem && trimmed.length > 10) {
        return line + '.';
      }
      
      return line;
    }).join('\n');
  }

  /**
   * Fix wrong line breaks - merge lines that belong together
   */
  private static fixWrongLineBreaks(text: string): string {
    const lines = text.split('\n');
    const result: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const current = lines[i].trim();
      const next = lines[i + 1]?.trim();
      
      if (!current) {
        result.push(lines[i]);
        continue;
      }
      
      // Check if next line should be merged
      if (next && this.shouldMergeLines(current, next)) {
        result.push(lines[i] + ' ' + lines[i + 1]);
        i++; // Skip next line
      } else {
        result.push(lines[i]);
      }
    }
    
    return result.join('\n');
  }

  /**
   * Check if two lines should be merged
   */
  private static shouldMergeLines(current: string, next: string): boolean {
    // Don't merge if next starts with capital (likely new sentence)
    if (/^[A-Z]/.test(next) && !this.isConjunction(next)) return false;
    
    // Merge if next starts with lowercase
    if (/^[a-z]/.test(next)) return true;
    
    // Merge if next starts with conjunction
    if (this.isConjunction(next)) return true;
    
    // Merge if current line is short (< 60 chars)
    if (current.length < 60 && next.length < 60) return true;
    
    return false;
  }

  /**
   * Check if line starts with conjunction
   */
  private static isConjunction(line: string): boolean {
    const conjunctions = ['and', 'but', 'so', 'or', 'yet', 'nor', 'for'];
    const firstWord = line.split(' ')[0].toLowerCase();
    return conjunctions.includes(firstWord);
  }

  /**
   * Create proper paragraphs based on keywords and structure
   */
  private static createParagraphs(text: string): string {
    const paragraphKeywords = [
      'However,', 'Additionally,', 'Important:', 'Note:', 'For example,',
      'In conclusion,', 'Next,', 'Firstly', 'Secondly', 'Thirdly',
      'Therefore,', 'Moreover,', 'Furthermore,', 'Meanwhile,'
    ];
    
    let result = text;
    
    paragraphKeywords.forEach(keyword => {
      const regex = new RegExp(`([.!?])\\s*(${keyword})`, 'gi');
      result = result.replace(regex, '$1\n\n$2');
    });
    
    return result;
  }

  /**
   * Format lists automatically
   */
  private static formatLists(text: string): string {
    // Detect numbered lists: "1)" or "1." or "first,"
    let result = text;
    
    // Add line breaks before list items
    result = result.replace(/([.!?])\s*(\d+[\.)]\s)/g, '$1\n\n$2');
    result = result.replace(/(first,|second,|third,|fourth,|fifth,)/gi, '\n$1');
    
    return result;
  }

  /**
   * Add spacing around code blocks
   */
  private static spaceCodeBlocks(text: string): string {
    // Add extra line before code blocks
    return text.replace(/(```)/g, '\n\n$1');
  }

  /**
   * Auto-detect and wrap function-like patterns in backticks
   */
  private static highlightInlineCode(text: string): string {
    // Don't process code blocks
    const codeBlockRegex = /```[\s\S]*?```/g;
    const codeBlocks: string[] = [];
    
    // Extract code blocks temporarily
    let result = text.replace(codeBlockRegex, (match) => {
      codeBlocks.push(match);
      return `__CODEBLOCK_${codeBlocks.length - 1}__`;
    });
    
    // Detect function calls: word()
    result = result.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\(\)/g, '`$1()`');
    
    // Detect common code patterns: file.ext, variable_name
    result = result.replace(/\b([a-z_][a-z0-9_]+\.[a-z]{2,4})\b/gi, '`$1`');
    
    // Restore code blocks
    codeBlocks.forEach((block, index) => {
      result = result.replace(`__CODEBLOCK_${index}__`, block);
    });
    
    return result;
  }

  /**
   * Split long paragraphs into smaller ones
   */
  static splitLongParagraphs(text: string, maxLength: number = 400): string {
    const paragraphs = text.split('\n\n');
    
    return paragraphs.map(para => {
      if (para.length <= maxLength) return para;
      
      // Split at sentence boundaries
      const sentences = para.match(/[^.!?]+[.!?]+/g) || [para];
      const chunks: string[] = [];
      let current = '';
      
      sentences.forEach(sentence => {
        if ((current + sentence).length > maxLength && current) {
          chunks.push(current.trim());
          current = sentence;
        } else {
          current += sentence;
        }
      });
      
      if (current) chunks.push(current.trim());
      
      return chunks.join('\n\n');
    }).join('\n\n');
  }

  /**
   * Detect and format callouts (warnings, tips, notes)
   */
  static detectCallouts(text: string): string {
    // Convert "Important:" to callout
    text = text.replace(/^(Important|Warning|Note|Tip):\s*(.+)$/gim, 
      ':::$1\n$2\n:::');
    
    return text;
  }

  /**
   * Auto-detect code-like content and wrap in code blocks
   */
  static autoDetectCodeBlocks(text: string): string {
    const lines = text.split('\n');
    const result: string[] = [];
    let inCodeBlock = false;
    let codeBuffer: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (this.looksLikeCode(line)) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeBuffer = [];
        }
        codeBuffer.push(line);
      } else {
        if (inCodeBlock && codeBuffer.length > 0) {
          result.push('```');
          result.push(...codeBuffer);
          result.push('```');
          codeBuffer = [];
          inCodeBlock = false;
        }
        result.push(line);
      }
    }
    
    // Flush remaining code
    if (codeBuffer.length > 0) {
      result.push('```');
      result.push(...codeBuffer);
      result.push('```');
    }
    
    return result.join('\n');
  }

  /**
   * Check if line looks like code
   */
  private static looksLikeCode(line: string): boolean {
    const codePatterns = [
      /^\s*(const|let|var|function|class|import|export)\s+/,
      /^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*.+;?$/,
      /^\s*(if|for|while|switch)\s*\(/,
      /{\s*$/,
      /}\s*$/,
      /;\s*$/,
      /^\s*\/\//,
      /^\s*#/,
      /^\s*--/,
    ];
    
    return codePatterns.some(pattern => pattern.test(line));
  }
}
