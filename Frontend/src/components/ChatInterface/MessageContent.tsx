/**
 * MessageContent Component
 * Renders Markdown content with code syntax highlighting
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './MessageContent.css';

interface MessageContentProps {
    content: string;
}

export function MessageContent({ content }: MessageContentProps) {
    return (
        <div className="markdown-content">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                            <SyntaxHighlighter
                                {...props}
                                style={vscDarkPlus}
                                language={match[1]}
                                PreTag="div"
                                className="code-block"
                                customStyle={{
                                    margin: 0,
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                }}
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                        ) : (
                            <code {...props} className={className}>
                                {children}
                            </code>
                        );
                    },
                    // Style links to open in new tab
                    a: ({ node, ...props }) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}

export default MessageContent;
