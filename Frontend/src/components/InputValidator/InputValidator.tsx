/**
 * Input Validator Component
 * Displays validation errors and warnings with real-time feedback
 */

import React from 'react';
import { InputValidation, formatFileSize } from '../../hooks/useInputValidation';
import './InputValidator.css';

interface InputValidatorProps {
    validation: InputValidation;
    showStats?: boolean;
}

export function InputValidatorFeedback({
    validation,
    showStats = true
}: InputValidatorProps) {
    const hasErrors = validation.errors.length > 0;
    const hasWarnings = validation.warnings.length > 0;

    if (!hasErrors && !hasWarnings && !showStats) {
        return null;
    }

    return (
        <div className="input-validator">
            {/* Errors */}
            {hasErrors && (
                <div className="validation-messages errors">
                    <div className="validation-icon error-icon">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" />
                            <path d="M10 6V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                            <circle cx="10" cy="14" r="1" fill="currentColor" />
                        </svg>
                    </div>
                    <div className="messages-content">
                        {validation.errors.map((error, index) => (
                            <p key={index} className="message error-message">{error}</p>
                        ))}
                    </div>
                </div>
            )}

            {/* Warnings */}
            {hasWarnings && !hasErrors && (
                <div className="validation-messages warnings">
                    <div className="validation-icon warning-icon">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <path
                                d="M10 3L17 16H3L10 3Z"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinejoin="round"
                            />
                            <path d="M10 8V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                            <circle cx="10" cy="14.5" r="0.5" fill="currentColor" />
                        </svg>
                    </div>
                    <div className="messages-content">
                        {validation.warnings.map((warning, index) => (
                            <p key={index} className="message warning-message">{warning}</p>
                        ))}
                    </div>
                </div>
            )}

            {/* Stats */}
            {showStats && (
                <div className="validation-stats">
                    <div className="stat-item">
                        <span className="stat-label">Lines:</span>
                        <span className={`stat-value ${validation.lineCount > 2400 ? 'stat-warning' : ''}`}>
                            {validation.lineCount.toLocaleString()}
                        </span>
                        <span className="stat-max">/ 3,000</span>
                    </div>

                    <div className="stat-divider">•</div>

                    <div className="stat-item">
                        <span className="stat-label">Size:</span>
                        <span className={`stat-value ${validation.sizeBytes > 240 * 1024 ? 'stat-warning' : ''}`}>
                            {formatFileSize(validation.sizeBytes)}
                        </span>
                        <span className="stat-max">/ 300 KB</span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default InputValidatorFeedback;
