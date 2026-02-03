export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  highlights?: Highlight[];
  miniAgentId?: string;  // DEPRECATED: Use Mini Agent tied to message_id instead
  attachments?: Attachment[];
  // Optional rich action payload (e.g., video/charts)
  action?: {
    type: "video" | "chart" | "link" | "custom" | "media_play" | "task_draft" | "task_update_draft" | "task_cancel_draft";
    data?: any;
    payload?: any;  // Support both data and payload for backwards compatibility
  };
  // Optional streaming status for long-running tools (e.g., deep_research)
  streamStatus?: string | null;
  // 🆕 API source info - shows which API key generated this response
  keySource?: "platform" | "user";  // "platform" = app's API, "user" = user's own BYOK
  model?: string;  // e.g., "llama-3.1-8b-instant"
}

export interface Highlight {
  id: string;
  text: string;
  color: string; // Accepts any HEX color code (e.g., "#FFD93D" or "#FF4B4BCC")
  startIndex: number;  // Absolute character offset (inclusive) - ✅ RENAMED from startOffset
  endIndex: number;    // Absolute character offset (exclusive) - ✅ RENAMED from endOffset
  note?: string;
  messageHash?: string;  // ✅ NEW: SHA256 hash for drift detection
  _broken?: boolean;     // Runtime flag: Highlight cannot be displayed
  _realigned?: boolean;  // Runtime flag: Highlight was fuzzy-matched
}

/**
 * Mini Agent - Isolated Doubt-Clarifier Agent
 * 
 * 🎯 PURPOSE:
 * - Explain/clarify selected parts of Main Agent responses
 * - Each Mini Agent is permanently tied to ONE message_id
 * - Maintains isolated conversation context (never mixes with Main Agent)
 * 
 * 🔒 ISOLATION GUARANTEE:
 * - Uses same AI pipeline as Main Agent
 * - Maintains separate conversation history
 * - Never receives Main Agent messages
 * - Never shares messages with Main Agent
 * 
 * 📨 REQUEST PAYLOAD (per spec):
 * - message_id: The Main Agent message this Mini Agent relates to
 * - selected_text_snippet: The selected text (nullable/editable)
 * - user_input: The actual query typed inside Mini Agent
 * - mini_agent_session_id: Unique ID per Mini Agent thread (agentId)
 */
export interface MiniAgent {
  id: string;  // Frontend ID (maps to agentId from backend)
  messageId: string;  // The Main Agent message this Mini Agent is tied to
  sessionId?: string; // The session ID this Mini Agent belongs to (optional for backwards compatibility)
  title?: string; // Title of the Mini Agent thread
  selectedText: string;  // The text snippet (editable/removable in UI)
  messages: MiniAgentMessage[];  // Isolated conversation history
  createdAt: Date;
  hasConversation?: boolean;  // Track if any messages have been exchanged
}

export interface MiniAgentMessage {
  id: string;
  role: "user" | "assistant";
  content: string;  // For user messages: includes [SNIPPET]...[/SNIPPET] prefix if snippet exists
  timestamp: Date;
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  miniAgents: MiniAgent[];
  createdAt: Date;
  updatedAt: Date;
  isPinned?: boolean;  // Stored in MongoDB - single source of truth
  isSaved?: boolean;   // Stored in MongoDB - single source of truth
  messageCount?: number;  // Message count from MongoDB (for filtering)
}

export interface Attachment {
  id: string;
  type: "image" | "file";
  url: string;
  thumbUrl?: string;
  name: string;
  size?: number;
  mime?: string;
  width?: number;
  height?: number;
}

export interface Task {
  id: string;
  title: string;
  completed: boolean;
  createdAt: Date;
  chatId?: string;
  dueDate?: Date;
  timeSeconds?: number;
  imageUrl?: string;
}

// 🎵 Media Play Feature Types
export interface MediaPlayPayload {
  mode: "link" | "video" | "embed";  // link = redirect, video = inline, embed = embedded player
  url?: string;  // Full URL for redirect mode
  video_id?: string;  // YouTube video ID for inline mode
  query: string;  // Original search query
  message: string;  // User-friendly message
  cached: boolean;  // Whether result came from cache
  source: "cache" | "api" | "scraper" | "redirect";  // Where the result came from
  executeOnce?: boolean;
}

export interface MediaPlayAction {
  type: "media_play";
  payload: MediaPlayPayload;
}
