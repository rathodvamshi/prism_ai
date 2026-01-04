/**
 * Message Block System - Single Source of Truth
 * 
 * Every assistant response is a sequence of structured semantic blocks.
 * This ensures clean, readable, smooth, elegant, and professional rendering.
 */

export type MessageBlock =
  | { type: "text"; content: string }
  | { type: "divider" }
  | { type: "heading"; level: 1 | 2 | 3; content: string }
  | { type: "code"; language: string; content: string }
  | { type: "list"; items: string[] }
  | { type: "image"; src: string; alt?: string };

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

