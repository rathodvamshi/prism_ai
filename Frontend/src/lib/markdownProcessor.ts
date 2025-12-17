/**
 * 🎯 MARKDOWN CODE PROCESSOR
 * 
 * Processes markdown content and automatically beautifies code blocks
 * Integrates with React Markdown rendering
 */

import { beautifyCode, detectLanguage } from './codeBeautifier';

export interface ProcessedCodeBlock {
  originalCode: string;
  beautifiedCode: string;
  language: string;
  wasBeautified: boolean;
  lineCount: number;
}

/**
 * ✨ Process code blocks in markdown content
 */
export const processMarkdownCode = (content: string): string => {
  // Match code blocks with language specification
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)\n```/g;
  
  let processedContent = content;
  let match;
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const [fullMatch, language, code] = match;
    
    if (code && code.trim()) {
      try {
        const result = beautifyCode(code, language);
        
        if (result.success && result.code !== code) {
          const beautifiedBlock = `\`\`\`${result.language}\n${result.code}\n\`\`\``;
          processedContent = processedContent.replace(fullMatch, beautifiedBlock);
          
          console.log(`🎨 Beautified ${result.language} code block in markdown`);
        }
      } catch (error) {
        console.warn('Failed to beautify code block:', error);
      }
    }
  }
  
  return processedContent;
};

/**
 * 🔧 Extract and process individual code block
 */
export const processCodeBlock = (
  code: string, 
  language?: string
): ProcessedCodeBlock => {
  if (!code || !code.trim()) {
    return {
      originalCode: code,
      beautifiedCode: code,
      language: language || 'text',
      wasBeautified: false,
      lineCount: 0
    };
  }

  try {
    const result = beautifyCode(code, language);
    
    return {
      originalCode: code,
      beautifiedCode: result.success ? result.code : code,
      language: result.language,
      wasBeautified: result.success && result.code !== code,
      lineCount: result.code.split('\n').length
    };
  } catch (error) {
    console.warn('Error processing code block:', error);
    return {
      originalCode: code,
      beautifiedCode: code,
      language: language || detectLanguage(code),
      wasBeautified: false,
      lineCount: code.split('\n').length
    };
  }
};

/**
 * 📝 Smart markdown code renderer configuration
 * Returns configuration object for react-markdown components
 */
export const createSmartCodeRenderer = () => {
  return {
    code: ({ node, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      const codeString = String(children).replace(/\n$/, '');
      const inline = !className && typeof children === 'string';
      const language = match ? match[1] : undefined;
      
      if (inline) {
        // Return inline code configuration
        return {
          type: 'inline',
          code: codeString,
          props
        };
      }
      
      // Block code - apply beautification
      const processed = processCodeBlock(codeString, language);
      
      // Return block code configuration
      return {
        type: 'block',
        code: processed.beautifiedCode,
        language: processed.language,
        wasBeautified: processed.wasBeautified
      };
    }
  };
};

/**
 * 🚀 Real-time code beautification for streaming content
 */
export const beautifyStreamingCode = (content: string): string => {
  // Handle partial code blocks in streaming content
  const partialCodeRegex = /```(\w+)?\n([\s\S]*)$/;
  const match = partialCodeRegex.exec(content);
  
  if (match && match[2]) {
    const [, language, code] = match;
    try {
      const result = beautifyCode(code, language);
      if (result.success) {
        return content.replace(match[0], `\`\`\`${result.language}\n${result.code}`);
      }
    } catch (error) {
      // Ignore errors for streaming content
    }
  }
  
  return content;
};

export default {
  processMarkdownCode,
  processCodeBlock,
  createSmartCodeRenderer,
  beautifyStreamingCode
};