/**
 * Message Block System - Single Source of Truth
 * 
 * Every assistant response is a sequence of structured semantic blocks.
 * This ensures clean, readable, smooth, elegant, and professional rendering.
 * 
 * 🎨 PRO-LEVEL STRUCTURE:
 * - Tables for organized data
 * - Blockquotes for emphasis
 * - Ordered/unordered lists with icons
 * - Task lists with checkboxes
 * - Callouts for important info
 * - Definition lists for terms
 * - Steps/procedures with progress
 * - Keyboard shortcuts styling
 * - Clean visual hierarchy
 */

export type MessageBlock = { startIndex?: number; endIndex?: number } & (
  | { type: "text"; content: string }
  | { type: "divider" }
  | { type: "heading"; level: 1 | 2 | 3; content: string }
  | { type: "code"; language: string; content: string }
  | { type: "list"; items: string[]; ordered?: boolean }
  | { type: "tasklist"; items: { text: string; checked: boolean }[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "blockquote"; content: string }
  | { type: "callout"; variant: "info" | "warning" | "success" | "tip"; content: string; title?: string }
  | { type: "steps"; items: string[] }
  | { type: "definition"; term: string; definition: string }
  | { type: "image"; src: string; alt?: string }
  | { type: "image"; src: string; alt?: string }
  | { type: "action"; data: any }
  | { type: "ask_flow"; selectedText: string; instruction: string }
);

/**
 * Validated message blocks array
 */
export type MessageBlocks = MessageBlock[];

/**
 * Streaming state for partial blocks
 */
export interface StreamingBlockState {
  blocks: MessageBlocks;
  currentBlockIndex: number;
  currentBlockContent: string;
  isComplete: boolean;
}

