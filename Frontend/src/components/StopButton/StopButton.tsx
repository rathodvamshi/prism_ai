/**
 * Stop Button Component
 * Instant cancellation button for AI generation
 */

import React from 'react';
import './StopButton.css';

interface StopButtonProps {
    onClick: () => void;
    disabled?: boolean;
    isLoading?: boolean;
}

export function StopButton({
    onClick,
    disabled = false,
    isLoading = false
}: StopButtonProps) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`stop-button ${isLoading ? 'loading' : ''}`}
            aria-label="Stop generation"
            title="Stop generating response"
        >
            <svg
                className="stop-icon"
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
            >
                <rect
                    x="4"
                    y="4"
                    width="10"
                    height="10"
                    rx="2"
                    fill="currentColor"
                />
            </svg>
            <span className="stop-text">Stop</span>
        </button>
    );
}

export default StopButton;
