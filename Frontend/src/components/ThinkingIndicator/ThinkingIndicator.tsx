/**
 * Thinking Indicator Component
 * Displays animated thinking/generating indicator
 */

import React from 'react';
import './ThinkingIndicator.css';

interface ThinkingIndicatorProps {
    isVisible: boolean;
    message?: string;
}

export function ThinkingIndicator({
    isVisible,
    message = 'Generating response...'
}: ThinkingIndicatorProps) {
    if (!isVisible) return null;

    return (
        <div className="thinking-indicator" role="status" aria-live="polite">
            <div className="thinking-animation">
                <div className="pulse-dots">
                    <span style={{ animationDelay: '0ms' }} />
                    <span style={{ animationDelay: '150ms' }} />
                    <span style={{ animationDelay: '300ms' }} />
                </div>
                <p className="thinking-text">{message}</p>
            </div>
        </div>
    );
}

export default ThinkingIndicator;
