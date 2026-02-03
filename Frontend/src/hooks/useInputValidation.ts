/**
 * Input Validator Hook
 * Client-side validation for AI prompts with real-time feedback
 */

import { useState, useEffect, useMemo } from 'react';

export interface InputValidation {
    isValid: boolean;
    lineCount: number;
    sizeBytes: number;
    sizeMB: number;
    errors: string[];
    warnings: string[];
}

export interface InputLimits {
    maxLines: number;
    maxSizeBytes: number;
    warnLinesThreshold: number;
    warnSizeThreshold: number;
}

export const DEFAULT_LIMITS: InputLimits = {
    maxLines: 3000,
    maxSizeBytes: 300 * 1024, // 300 KB
    warnLinesThreshold: 2400, // 80% of max
    warnSizeThreshold: 240 * 1024, // 80% of max
};

export function validateInput(
    content: string,
    limits: InputLimits = DEFAULT_LIMITS
): InputValidation {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Count lines
    const lines = content.split('\n');
    const lineCount = lines.length;

    // Calculate size
    const sizeBytes = new Blob([content]).size;
    const sizeMB = sizeBytes / (1024 * 1024);

    // Check line count limit
    if (lineCount > limits.maxLines) {
        errors.push(
            `Input too large. Please split your message. (Current: ${lineCount.toLocaleString()} lines, Maximum: ${limits.maxLines.toLocaleString()} lines)`
        );
    } else if (lineCount > limits.warnLinesThreshold) {
        warnings.push(
            `Approaching line limit (${lineCount.toLocaleString()} / ${limits.maxLines.toLocaleString()})`
        );
    }

    // Check size limit
    if (sizeBytes > limits.maxSizeBytes) {
        errors.push(
            `Input too large. Please split your message. (Current: ${(sizeBytes / 1024).toFixed(0)} KB, Maximum: ${(limits.maxSizeBytes / 1024).toFixed(0)} KB)`
        );
    } else if (sizeBytes > limits.warnSizeThreshold) {
        warnings.push(
            `Approaching size limit (${(sizeBytes / 1024).toFixed(0)} / ${(limits.maxSizeBytes / 1024).toFixed(0)} KB)`
        );
    }

    // Check for extremely long lines
    const maxLineLength = Math.max(...lines.map(line => line.length), 0);
    if (maxLineLength > 10000) {
        warnings.push(
            `Very long line detected (${maxLineLength.toLocaleString()} characters). Consider breaking it up.`
        );
    }

    const isValid = errors.length === 0;

    return {
        isValid,
        lineCount,
        sizeBytes,
        sizeMB: Number(sizeMB.toFixed(2)),
        errors,
        warnings,
    };
}

export function useInputValidation(
    content: string,
    limits?: InputLimits
): InputValidation {
    const validation = useMemo(
        () => validateInput(content, limits),
        [content, limits]
    );

    return validation;
}

export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
}

export function getValidationSeverity(validation: InputValidation): 'error' | 'warning' | 'success' {
    if (!validation.isValid) return 'error';
    if (validation.warnings.length > 0) return 'warning';
    return 'success';
}
