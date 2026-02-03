/**
 * Message Block Parser
 * 
 * Converts LLM output (markdown/text) into structured MessageBlock[]
 * 
 * Pipeline: LLM Output → Block Parser → Validated MessageBlock[] → Renderer → UI
 * 
 * 🎨 PRO-LEVEL PARSING:
 * - Tables (pipe-separated)
 * - Blockquotes (> prefix)
 * - Ordered/unordered lists
 * - Callouts (> [!NOTE], > [!TIP], etc.)
 * - Clean structure detection
 */

import { MessageBlock, MessageBlocks } from "@/types/messageBlocks";
import { stripMarkdown } from "@/lib/semanticHighlight";
import { filterMetadata, METADATA_PATTERN } from "@/lib/streamUtils";

export class MessageBlockParser {
  /**
   * Main parsing function
   * Converts raw text/markdown into structured blocks
   */
  static parse(content: string): MessageBlocks {
    if (!content || !content.trim()) {
      return [{ type: "text", content: "" }];
    }

    const blocks: MessageBlock[] = [];

    // STEP 0: Check for Ask Flow Structure (Exact Logic)
    // Matches the template sent from ChatInput
    const askFlowRegex = /The user has selected the following text:\s*<<<SELECTED_TEXT>>>\s*([\s\S]*?)\s*<<<END_SELECTED_TEXT>>>\s*The user's instruction is:\s*"([\s\S]*?)"/i;
    const askFlowMatch = content.match(askFlowRegex);

    if (askFlowMatch) {
      return [{
        type: "ask_flow",
        selectedText: askFlowMatch[1].trim(),
        instruction: askFlowMatch[2].trim()
      }];
    }

    // STEP 1: Extract ALL ACTION blocks
    const detectedActions: any[] = [];

    // Regex for generic actions (Global)
    const actionRegex = /<!--ACTION:(.*?)-->/gs;
    let match;

    while ((match = actionRegex.exec(content)) !== null) {
      try {
        const actionContent = match[1];

        // Handle specific MEDIA_PLAY format if it exists (captured by generic regex too if formatted as JSON)
        if (actionContent.startsWith("MEDIA_PLAY:")) {
          const jsonStr = actionContent.substring(11);
          const rawPayload = JSON.parse(jsonStr);
          detectedActions.push({
            type: "media_play",
            payload: rawPayload
          });
          continue;
        }

        // Generic JSON action
        if (actionContent.trim().startsWith("{")) {
          const actionData = JSON.parse(actionContent);
          detectedActions.push(actionData);
        } else {
          // Simple tag action e.g. REFRESH_TASKS
          detectedActions.push({ type: actionContent.trim(), payload: {} });
        }
      } catch (e) {
        console.error("❌ Failed to parse action block:", e);
      }
    }

    if (detectedActions.length > 0) {
      console.log(`🔍 Extracted ${detectedActions.length} actions:`, detectedActions);
    }

    // STEP 2: Clean ALL special blocks from content (using centralized filter)
    let cleanContent = filterMetadata(content).trim();

    // Explicitly remove ACTION tags (captured above)
    cleanContent = cleanContent.replace(/<!--ACTION:(.*?)-->/gs, "");

    // 🛡️ RESILIENCE: Fix inline lists (e.g. "Text • Item 1 • Item 2") by forcing newlines
    // This handles cases where the LLM forgets to add newlines between bullet points
    cleanContent = cleanContent
      // Replace " • " with "\n- " (inline bullet separator)
      .replace(/([^\n])\s+[•●]\s+/g, "$1\n- ")
      // Replace start-of-line bullet "• " with "- "
      .replace(/^[•●]\s+/gm, "- ");

    console.log("🧹 Cleaned content (first 100 chars):", cleanContent.substring(0, 100));

    // STEP 3: Parse the cleaned content into blocks
    const lines = cleanContent.split('\n');
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

    // Helper: detect if line is a list item (unordered)
    const isUnorderedListItem = (line: string): string | null => {
      const match = line.match(/^[\s]*[-*+]\s+(.+)$/);
      if (match) return match[1].trim();
      return null;
    };

    // Helper: detect if line is an ordered list item
    const isOrderedListItem = (line: string): string | null => {
      const match = line.match(/^[\s]*\d+[.)]\s+(.+)$/);
      if (match) return match[1].trim();
      return null;
    };

    // Helper: detect if line is a task list item (- [ ] or - [x])
    const isTaskListItem = (line: string): { text: string; checked: boolean } | null => {
      const match = line.match(/^[\s]*[-*+]\s+\[([ xX])\]\s+(.+)$/);
      if (match) {
        return {
          checked: match[1].toLowerCase() === 'x',
          text: match[2].trim()
        };
      }
      return null;
    };

    // Helper: detect if line is a step item (Step 1:, 1️⃣, etc.)
    const isStepItem = (line: string): string | null => {
      const stepMatch = line.match(/^(?:Step\s+\d+[:.]\s*|[1-9]️⃣\s*|➊|➋|➌|➍|➎|➏|➐|➑|➒|➓)\s*(.+)$/i);
      if (stepMatch) return stepMatch[1].trim();
      return null;
    };

    // Helper: detect if line is a definition (Term: Definition or **Term**: Definition)
    const isDefinition = (line: string): { term: string; definition: string } | null => {
      // Match "**Term**: Definition" or "Term: Definition" (where term is short)
      const boldMatch = line.match(/^\*\*([^*]+)\*\*:\s+(.+)$/);
      if (boldMatch) {
        return { term: boldMatch[1].trim(), definition: boldMatch[2].trim() };
      }

      // Simple "Term: Definition" - term should be short (< 30 chars) and not look like a sentence
      const simpleMatch = line.match(/^([A-Z][^:]{2,28}):\s+(.{10,})$/);
      if (simpleMatch && !simpleMatch[1].includes(' ')) {
        return { term: simpleMatch[1].trim(), definition: simpleMatch[2].trim() };
      }

      return null;
    };

    // Helper: detect if line is any list item
    const isListItem = (line: string): { content: string; ordered: boolean } | null => {
      // Check task list first (more specific)
      if (isTaskListItem(line)) return null; // Let task list handler deal with it

      const unordered = isUnorderedListItem(line);
      if (unordered) return { content: unordered, ordered: false };

      const ordered = isOrderedListItem(line);
      if (ordered) return { content: ordered, ordered: true };

      return null;
    };

    // Helper: detect if line is a table row
    const isTableRow = (line: string): string[] | null => {
      const trimmed = line.trim();
      if (!trimmed.includes('|')) return null;

      // Parse pipe-separated values
      const cells = trimmed
        .replace(/^\||\|$/g, '') // Remove leading/trailing pipes
        .split('|')
        .map(cell => cell.trim());

      // Must have at least 2 cells to be a table
      if (cells.length >= 2) return cells;
      return null;
    };

    // Helper: detect if line is a table separator (|---|---|)
    const isTableSeparator = (line: string): boolean => {
      return /^\|?[\s-:|]+\|?$/.test(line.trim()) && line.includes('-');
    };

    // Helper: detect if line is a blockquote
    const isBlockquote = (line: string): string | null => {
      const match = line.match(/^>\s*(.*)$/);
      if (match) return match[1];
      return null;
    };

    // Helper: detect callout type from blockquote content
    const parseCallout = (content: string): { variant: "info" | "warning" | "success" | "tip"; text: string; title?: string } | null => {
      const calloutMatch = content.match(/^\[!(NOTE|TIP|WARNING|IMPORTANT|CAUTION|INFO|SUCCESS)\]\s*(.*)$/i);
      if (calloutMatch) {
        const type = calloutMatch[1].toUpperCase();
        const variantMap: Record<string, "info" | "warning" | "success" | "tip"> = {
          'NOTE': 'info',
          'INFO': 'info',
          'TIP': 'tip',
          'SUCCESS': 'success',
          'WARNING': 'warning',
          'IMPORTANT': 'warning',
          'CAUTION': 'warning',
        };
        return {
          variant: variantMap[type] || 'info',
          text: calloutMatch[2].trim(),
          title: type.charAt(0) + type.slice(1).toLowerCase()
        };
      }
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

      // Check for table (look ahead to verify it's a complete table)
      const tableRow = isTableRow(line);
      if (tableRow && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        flushTextBlock();

        // First row is headers
        const headers = tableRow;
        i += 2; // Skip header and separator

        // Collect data rows
        const rows: string[][] = [];
        while (i < lines.length) {
          const dataRow = isTableRow(lines[i]);
          if (dataRow && !isTableSeparator(lines[i])) {
            rows.push(dataRow);
            i++;
          } else {
            break;
          }
        }

        blocks.push({ type: "table", headers, rows });
        continue;
      }

      // Check for blockquote / callout
      const quoteContent = isBlockquote(line);
      if (quoteContent !== null) {
        flushTextBlock();

        // Check if it's a callout
        const callout = parseCallout(quoteContent);
        if (callout) {
          // Collect multi-line callout content
          let calloutContent = callout.text;
          i++;
          while (i < lines.length) {
            const nextQuote = isBlockquote(lines[i]);
            if (nextQuote !== null) {
              calloutContent += '\n' + nextQuote;
              i++;
            } else {
              break;
            }
          }
          blocks.push({ type: "callout", variant: callout.variant, content: calloutContent.trim() });
          continue;
        }

        // Regular blockquote - collect consecutive quoted lines
        let blockquoteContent = quoteContent;
        i++;
        while (i < lines.length) {
          const nextQuote = isBlockquote(lines[i]);
          if (nextQuote !== null) {
            blockquoteContent += '\n' + nextQuote;
            i++;
          } else {
            break;
          }
        }
        blocks.push({ type: "blockquote", content: blockquoteContent.trim() });
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

      // Check for task list item (- [ ] or - [x])
      const taskItem = isTaskListItem(line);
      if (taskItem) {
        flushTextBlock();
        const taskItems: { text: string; checked: boolean }[] = [taskItem];
        i++;

        while (i < lines.length) {
          const nextTask = isTaskListItem(lines[i]);
          if (nextTask) {
            taskItems.push(nextTask);
            i++;
          } else if (lines[i].trim() === "") {
            i++;
            break;
          } else {
            break;
          }
        }

        blocks.push({ type: "tasklist", items: taskItems });
        continue;
      }

      // Check for step items (Step 1:, 1️⃣, etc.)
      const stepItem = isStepItem(line);
      if (stepItem) {
        flushTextBlock();
        const stepItems: string[] = [stepItem];
        i++;

        while (i < lines.length) {
          const nextStep = isStepItem(lines[i]);
          if (nextStep) {
            stepItems.push(nextStep);
            i++;
          } else if (lines[i].trim() === "") {
            i++;
            break;
          } else {
            break;
          }
        }

        blocks.push({ type: "steps", items: stepItems });
        continue;
      }

      // Check for definition (Term: Definition)
      const definition = isDefinition(line);
      if (definition) {
        flushTextBlock();
        blocks.push({ type: "definition", term: definition.term, definition: definition.definition });
        i++;
        continue;
      }

      // Check for list item
      const listItem = isListItem(line);
      if (listItem) {
        // Collect consecutive list items of same type
        const listItems: string[] = [listItem.content];
        const isOrdered = listItem.ordered;
        i++;

        while (i < lines.length) {
          const nextItem = isListItem(lines[i]);
          if (nextItem && nextItem.ordered === isOrdered) {
            listItems.push(nextItem.content);
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
        blocks.push({ type: "list", items: listItems, ordered: isOrdered });
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

    // STEP 4: Add action block(s) at END
    if (detectedActions.length > 0) {
      detectedActions.forEach(action => {
        blocks.push({ type: "action", data: action });
      });
      console.log(`📍 Added ${detectedActions.length} action blocks`);
    }

    // Post-process: merge consecutive text blocks, clean up, insert dividers for long responses
    const processedBlocks = this.postProcess(blocks, content);

    // Assign offsets relative to RENDERED content (markdown stripped) for highlighting
    // This is critical: highlights use positions based on what user sees in DOM
    const renderedContent = stripMarkdown(cleanContent);
    return this.assignOffsets(processedBlocks, renderedContent);
  }

  /**
   * Assign start/end indices to blocks matching RENDERED content (markdown stripped)
   * This ensures highlight positions align with what users select in the DOM
   */
  private static assignOffsets(blocks: MessageBlocks, renderedContent: string): MessageBlocks {
    let cursor = 0;
    return blocks.map(block => {
      // Only track offsets for textual blocks where highlights matter
      if (block.type === 'text' || block.type === 'heading' || block.type === 'code') {
        // Use RENDERED (markdown-stripped) content for matching
        const rawContent = block.content || '';
        const contentToMatch = stripMarkdown(rawContent);
        if (!contentToMatch) return block;

        // Find match starting from current cursor in rendered content
        const matchIndex = renderedContent.indexOf(contentToMatch, cursor);

        if (matchIndex !== -1) {
          const startIndex = matchIndex;
          const endIndex = matchIndex + contentToMatch.length;

          // Advance cursor to end of this matching block
          cursor = endIndex;

          return { ...block, startIndex, endIndex };
        }
      }
      return block;
    });
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

      // Don't merge consecutive text blocks - keep them separate to preserve original structure/whitespace fidelity
      // which is crucial for highlight offset alignment
      processed.push(block);
      lastBlock = block;

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
      // Explicit cast needed as TS doesn't narrow array access automatically
      if ((lastBlock as any).content && !/[.!?]\s*$/.test((lastBlock as any).content)) {
        partialBlock = {
          type: "text",
          content: (lastBlock as any).content
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

