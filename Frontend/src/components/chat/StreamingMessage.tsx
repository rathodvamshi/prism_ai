import { memo } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from "./CodeBlock";
import { Separator } from "@/components/ui/separator-premium";
import { Callout } from "@/components/ui/callout";

interface StreamingMessageProps {
  content: string;
  isStreaming: boolean;
  isThinking: boolean;
  className?: string;
}

/**
 * GPT-Style Streaming Message Component
 * 
 * Key Principles:
 * 1. NO re-rendering on every chunk (stable component)
 * 2. Content passed directly from store (append-only)
 * 3. Layout stability (no flickering/jumping)
 * 4. Smooth cursor animation during streaming
 * 5. Clean thinking state with animated dots
 */
export const StreamingMessage = memo(({
  content,
  isStreaming,
  isThinking,
  className = "",
}: StreamingMessageProps) => {
  
  // Thinking State - Before first chunk
  if (isThinking) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="flex items-center gap-2 sm:gap-2.5 py-2 sm:py-2.5"
      >
        <motion.div
          className="flex items-center gap-2 sm:gap-2.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-full bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20"
          animate={{
            boxShadow: [
              "0 0 0 0 rgba(59, 130, 246, 0)",
              "0 0 0 8px rgba(59, 130, 246, 0.1)",
              "0 0 0 0 rgba(59, 130, 246, 0)"
            ]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <motion.span
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="text-xs sm:text-sm font-medium text-primary"
          >
            Thinking
          </motion.span>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-primary rounded-full"
                animate={{
                  scale: [1, 1.4, 1],
                  opacity: [0.5, 1, 0.5]
                }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut"
                }}
              />
            ))}
          </div>
        </motion.div>
      </motion.div>
    );
  }

  // GPT-Style Content Rendering
  // Content comes pre-appended from store (no internal buffering)
  return (
    <div className={className}>
      <div className="markdown-content relative">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              const codeString = String(children).replace(/\n$/, '');
              
              return !inline ? (
                <CodeBlock language={match ? match[1] : 'text'}>
                  {codeString}
                </CodeBlock>
              ) : (
                <CodeBlock inline>{codeString}</CodeBlock>
              );
            },
            p({ children }) {
              return <p className="mb-2 sm:mb-3 leading-6 sm:leading-7 text-[14px] sm:text-[15px]">{children}</p>;
            },
            blockquote({ children }) {
              const content = String(children);
              
              // Check if it's a callout
              const calloutMatch = content.match(/:::(warning|tip|info|important)\s*([\s\S]*?):::/i);
              if (calloutMatch) {
                const type = calloutMatch[1].toLowerCase() as 'warning' | 'tip' | 'info' | 'important';
                const text = calloutMatch[2].trim();
                return <Callout type={type}>{text}</Callout>;
              }
              
              return (
                <blockquote className="border-l-2 sm:border-l-4 border-primary/40 pl-2 sm:pl-4 py-1.5 sm:py-2 my-2 sm:my-3 bg-muted/30 rounded-r-md italic text-muted-foreground text-sm">
                  {children}
                </blockquote>
              );
            },
            hr: () => <Separator />,
            strong({ children }) {
              return <strong className="font-semibold text-foreground">{children}</strong>;
            },
            em({ children }) {
              return <em className="italic text-foreground/90">{children}</em>;
            },
            ul({ children }) {
              return <ul className="list-disc list-outside ml-4 sm:ml-5 mb-2 sm:mb-3 space-y-1 sm:space-y-1.5">{children}</ul>;
            },
            ol({ children }) {
              return <ol className="list-decimal list-outside ml-4 sm:ml-5 mb-2 sm:mb-3 space-y-1 sm:space-y-1.5">{children}</ol>;
            },
            li({ children }) {
              return <li className="leading-6 sm:leading-7 pl-0.5 sm:pl-1 text-[14px] sm:text-[15px]">{children}</li>;
            },
            table({ children }) {
              return (
                <div className="my-2 sm:my-4 overflow-x-auto rounded-md sm:rounded-lg border border-border">
                  <table className="w-full border-collapse">{children}</table>
                </div>
              );
            },
            thead({ children }) {
              return <thead className="bg-muted/50">{children}</thead>;
            },
            tbody({ children }) {
              return <tbody className="divide-y divide-border">{children}</tbody>;
            },
            tr({ children }) {
              return <tr className="hover:bg-muted/30 transition-colors">{children}</tr>;
            },
            th({ children }) {
              return <th className="px-2 sm:px-4 py-1.5 sm:py-2 text-left text-xs sm:text-sm font-semibold border-b border-border">{children}</th>;
            },
            td({ children }) {
              return <td className="px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm">{children}</td>;
            },
            h1({ children }) {
              return <h1 className="text-xl sm:text-2xl font-bold mb-2 sm:mb-3 mt-4 sm:mt-6">{children}</h1>;
            },
            h2({ children }) {
              return <h2 className="text-lg sm:text-xl font-bold mb-2 sm:mb-3 mt-3 sm:mt-5">{children}</h2>;
            },
            h3({ children }) {
              return <h3 className="text-base sm:text-lg font-semibold mb-1.5 sm:mb-2 mt-3 sm:mt-4">{children}</h3>;
            },
            h4({ children }) {
              return <h4 className="text-sm sm:text-base font-semibold mb-1.5 sm:mb-2 mt-2 sm:mt-3">{children}</h4>;
            },
            a({ href, children }) {
              return <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">{children}</a>;
            },
          }}
        >
          {content}
        </ReactMarkdown>
        
        {/* GPT-Style animated cursor during streaming */}
        {isStreaming && (
          <motion.span
            initial={{ opacity: 1 }}
            animate={{ opacity: [1, 0.2, 1] }}
            transition={{
              duration: 0.8,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="inline-block w-1 sm:w-1.5 h-4 sm:h-5 ml-0.5 sm:ml-1 bg-primary/80 align-middle rounded-sm"
          />
        )}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for memo - only re-render when actually needed
  // This prevents unnecessary re-renders during streaming
  return (
    prevProps.content === nextProps.content &&
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.isThinking === nextProps.isThinking
  );
});

StreamingMessage.displayName = "StreamingMessage";
