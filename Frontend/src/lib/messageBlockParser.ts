/**
 * Message Block Parser
 * 
 * Converts LLM output (markdown/text) into structured MessageBlock[]
 * 
 * Pipeline: LLM Output → Block Parser → Validated MessageBlock[] → Renderer → UI
 */

import { MessageBlock, MessageBlocks } from "@/types/messageBlocks";

export class MessageBlockParser {
  /**
   * Main parsing function
   * Converts raw text/markdown into structured blocks
   */
  static parse(content: string): MessageBlocks {
    if (!content || !content.trim()) {
      return [{ type: "text", content: "" }];
    }

    const blocks: MessageBlocks = [];
    const lines = content.split('\n');
    let i = 0;
    let currentTextBlock = "";
    let inCodeBlock = false;
    let codeBlockLanguage = "text";
    let codeBlockContent = "";

    // Helper: flush current text block if it has content
    const flushTextBlock = () => {
      if (currentTextBlock.trim()) {
        blocks.push({ type: "text", content: currentTextBlock.trim() });
        currentTextBlock = "";
      }
    };

    // Helper: detect if line is a heading
    const isHeading = (line: string): { level: 1 | 2 | 3; content: string } | null => {
      const h1Match = line.match(/^#\s+(.+)$/);
      if (h1Match) return { level: 1, content: h1Match[1].trim() };
      
      const h2Match = line.match(/^##\s+(.+)$/);
      if (h2Match) return { level: 2, content: h2Match[1].trim() };
      
      const h3Match = line.match(/^###\s+(.+)$/);
      if (h3Match) return { level: 3, content: h3Match[1].trim() };
      
      return null;
    };

    // Helper: detect if line is a divider
    const isDivider = (line: string): boolean => {
      return /^[-*_]{3,}$/.test(line.trim()) || line.trim() === "---";
    };

    // Helper: detect if line starts a code block
    const isCodeBlockStart = (line: string): { language: string } | null => {
      const match = line.match(/^```(\w+)?$/);
      if (match) {
        return { language: match[1] || "text" };
      }
      return null;
    };

    // Helper: detect if line ends a code block
    const isCodeBlockEnd = (line: string): boolean => {
      return line.trim() === "```";
    };

    // Helper: detect if line is a list item
    const isListItem = (line: string): string | null => {
      const match = line.match(/^[\s]*[-*+]\s+(.+)$/);
      if (match) return match[1].trim();
      
      const numberedMatch = line.match(/^[\s]*\d+[.)]\s+(.+)$/);
      if (numberedMatch) return numberedMatch[1].trim();
      
      return null;
    };

    // Process lines
    while (i < lines.length) {
      const line = lines[i];
      const trimmedLine = line.trim();

      // Handle code blocks
      if (inCodeBlock) {
        if (isCodeBlockEnd(line)) {
          // End of code block
          flushTextBlock();
          blocks.push({
            type: "code",
            language: codeBlockLanguage,
            content: codeBlockContent.trim()
          });
          codeBlockContent = "";
          inCodeBlock = false;
          i++;
          continue;
        } else {
          codeBlockContent += line + "\n";
          i++;
          continue;
        }
      }

      // Check for code block start
      const codeStart = isCodeBlockStart(line);
      if (codeStart) {
        flushTextBlock();
        inCodeBlock = true;
        codeBlockLanguage = codeStart.language;
        i++;
        continue;
      }

      // Check for divider
      if (isDivider(line)) {
        flushTextBlock();
        blocks.push({ type: "divider" });
        i++;
        continue;
      }

      // Check for heading
      const heading = isHeading(line);
      if (heading) {
        flushTextBlock();
        blocks.push({
          type: "heading",
          level: heading.level,
          content: heading.content
        });
        i++;
        continue;
      }

      // Check for list item
      const listItem = isListItem(line);
      if (listItem) {
        // Collect consecutive list items
        const listItems: string[] = [listItem];
        i++;
        
        while (i < lines.length) {
          const nextListItem = isListItem(lines[i]);
          if (nextListItem) {
            listItems.push(nextListItem);
            i++;
          } else if (lines[i].trim() === "") {
            // Empty line - might be end of list or spacing
            i++;
            break;
          } else {
            break;
          }
        }
        
        flushTextBlock();
        blocks.push({ type: "list", items: listItems });
        continue;
      }

      // Regular text line
      if (trimmedLine === "") {
        // Empty line - flush current text block and add spacing
        if (currentTextBlock.trim()) {
          flushTextBlock();
        }
      } else {
        if (currentTextBlock) {
          currentTextBlock += "\n" + line;
        } else {
          currentTextBlock = line;
        }
      }
      
      i++;
    }

    // Flush remaining content
    if (inCodeBlock && codeBlockContent) {
      // Unclosed code block - treat as code
      blocks.push({
        type: "code",
        language: codeBlockLanguage,
        content: codeBlockContent.trim()
      });
    } else {
      flushTextBlock();
    }

    // Post-process: merge consecutive text blocks, clean up, insert dividers for long responses
    return this.postProcess(blocks, content);
  }

  /**
   * Estimate reading time in seconds (average reading speed: 200 words/min = 3.33 words/sec)
   */
  private static estimateReadingTime(content: string): number {
    const words = content.trim().split(/\s+/).filter(w => w.length > 0).length;
    return words / 3.33; // words per second
  }

  /**
   * Post-process blocks: merge consecutive text blocks, remove empty blocks, insert dividers for long responses
   */
  private static postProcess(blocks: MessageBlocks, originalContent?: string): MessageBlocks {
    if (blocks.length === 0) {
      return [{ type: "text", content: "" }];
    }

    const processed: MessageBlocks = [];
    let lastBlock: MessageBlock | null = null;
    let totalReadingTime = 0;

    // Calculate total reading time if original content provided
    if (originalContent) {
      totalReadingTime = this.estimateReadingTime(originalContent);
    }

    // Determine if we need automatic dividers (>8 seconds to read)
    const needsDividers = totalReadingTime > 8;

    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i];
      const nextBlock = blocks[i + 1];

      // Skip empty text blocks
      if (block.type === "text" && !block.content.trim()) {
        continue;
      }

      // Merge consecutive text blocks
      if (block.type === "text" && lastBlock?.type === "text") {
        processed[processed.length - 1] = {
          type: "text",
          content: (lastBlock.content + "\n\n" + block.content).trim()
        };
        lastBlock = processed[processed.length - 1];
      } else {
        processed.push(block);
        lastBlock = block;
      }

      // Auto-insert dividers for long responses
      if (needsDividers && nextBlock) {
        const shouldInsertDivider =
          // Before code blocks
          (block.type === "text" && nextBlock.type === "code") ||
          // After code blocks
          (block.type === "code" && nextBlock.type === "text") ||
          // Between major sections (heading followed by content)
          (block.type === "heading" && nextBlock.type === "text" && nextBlock.content.length > 100) ||
          // Between large text blocks (both > 200 chars)
          (block.type === "text" && nextBlock.type === "text" && 
           block.content.length > 200 && nextBlock.content.length > 200);

        if (shouldInsertDivider && processed[processed.length - 1]?.type !== "divider") {
          // Don't insert if last block was already a divider
          processed.push({ type: "divider" });
          lastBlock = { type: "divider" };
        }
      }
    }

    // Remove consecutive dividers
    const finalProcessed: MessageBlocks = [];
    for (let i = 0; i < processed.length; i++) {
      const block = processed[i];
      const prevBlock = finalProcessed[finalProcessed.length - 1];
      
      // Skip if this is a divider and previous was also a divider
      if (block.type === "divider" && prevBlock?.type === "divider") {
        continue;
      }
      
      finalProcessed.push(block);
    }

    // Ensure at least one block
    if (finalProcessed.length === 0) {
      return [{ type: "text", content: "" }];
    }

    return finalProcessed;
  }

  /**
   * Parse streaming content incrementally
   * Returns partial blocks for smooth streaming rendering
   */
  static parseStreaming(content: string): {
    blocks: MessageBlocks;
    partialBlock?: { type: string; content: string; language?: string };
  } {
    // For streaming, we parse what we have and identify the current partial block
    const completeContent = content;
    let partialBlock: { type: string; content: string; language?: string } | undefined;

    // Check if we're in the middle of a code block
    const codeBlockMatches = completeContent.match(/```(\w+)?\n([\s\S]*?)$/);
    if (codeBlockMatches && !completeContent.includes("```", codeBlockMatches[0].length)) {
      // Incomplete code block
      partialBlock = {
        type: "code",
        language: codeBlockMatches[1] || "text",
        content: codeBlockMatches[2]
      };
      // Parse everything before the incomplete code block
      const beforeCode = completeContent.substring(0, completeContent.lastIndexOf("```"));
      const blocks = this.parse(beforeCode);
      return { blocks, partialBlock };
    }

    // Check if we're in the middle of a heading
    const headingMatch = completeContent.match(/(^|\n)(#{1,3})\s+(.+)$/);
    if (headingMatch && !headingMatch[3].includes("\n")) {
      // Might be incomplete heading - parse everything before it
      const beforeHeading = completeContent.substring(0, completeContent.lastIndexOf("#"));
      const blocks = this.parse(beforeHeading);
      partialBlock = {
        type: "heading",
        content: headingMatch[3]
      };
      return { blocks, partialBlock };
    }

    // Otherwise, parse normally
    const blocks = this.parse(completeContent);
    
    // If last block is text and content ends mid-sentence, it's partial
    if (blocks.length > 0 && blocks[blocks.length - 1].type === "text") {
      const lastBlock = blocks[blocks.length - 1];
      // Check if content seems incomplete (no ending punctuation, not ending with space)
      if (lastBlock.content && !/[.!?]\s*$/.test(lastBlock.content)) {
        partialBlock = {
          type: "text",
          content: lastBlock.content
        };
        // Remove the last block as it's partial
        blocks.pop();
      }
    }

    return { blocks, partialBlock };
  }

  /**
   * Extract images from markdown content
   */
  static extractImages(content: string): Array<{ src: string; alt?: string }> {
    const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    const images: Array<{ src: string; alt?: string }> = [];
    let match;

    while ((match = imageRegex.exec(content)) !== null) {
      images.push({
        alt: match[1] || undefined,
        src: match[2]
      });
    }

    return images;
  }
}

