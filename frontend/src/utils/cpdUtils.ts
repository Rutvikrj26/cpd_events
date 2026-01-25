/**
 * CPD utility functions for consistent data handling
 * Centralizes numeric conversion logic to avoid duplication
 */

import { CPDRequirement, CPDProgress, CPDTransaction, CPDTransactionSummary } from "@/api/cpd/types";

/**
 * Safely converts a value to a number, handling strings, nulls, and undefined
 * @param value - Value to convert (can be string, number, null, undefined)
 * @param defaultValue - Default value if conversion fails (default: 0)
 * @returns Parsed number or default value
 */
export function safeParseNumber(value: string | number | null | undefined, defaultValue: number = 0): number {
    if (value === null || value === undefined || value === '') {
        return defaultValue;
    }
    
    const parsed = typeof value === 'number' ? value : parseFloat(String(value));
    return isNaN(parsed) ? defaultValue : parsed;
}

/**
 * Formats a number to a fixed decimal places for display
 * @param value - Number to format
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted string
 */
export function formatCredits(value: number, decimals: number = 1): string {
    return value.toFixed(decimals);
}

/**
 * Calculate total credits earned from CPD progress data
 * Uses multiple sources with fallbacks for robustness
 * @param progress - CPD progress data
 * @param transactionSummary - Optional transaction summary
 * @returns Total credits earned
 */
export function calculateTotalCredits(
    progress: CPDProgress | null,
    transactionSummary?: CPDTransactionSummary | null
): number {
    // Priority 1: Use total_credits_earned from progress if available
    if (progress?.total_credits_earned !== undefined && progress?.total_credits_earned !== null) {
        const credits = safeParseNumber(progress.total_credits_earned);
        if (credits !== 0) return credits;
    }

    // Priority 2: Use current_balance from transaction summary
    if (transactionSummary?.current_balance !== undefined && transactionSummary?.current_balance !== null) {
        const balance = safeParseNumber(transactionSummary.current_balance);
        if (balance !== 0) return balance;
    }

    // Priority 3: Sum earned_credits from all requirements
    const requirements = progress?.requirements || [];
    return requirements.reduce((sum, req) => {
        const earned = safeParseNumber(req.earned_credits);
        return sum + earned;
    }, 0);
}

/**
 * Calculate total required credits from requirements
 * @param requirements - Array of CPD requirements
 * @returns Total required credits
 */
export function calculateTotalRequired(requirements: CPDRequirement[]): number {
    return requirements.reduce((sum, req) => {
        const required = safeParseNumber(req.annual_requirement);
        return sum + required;
    }, 0);
}

/**
 * Calculate overall progress percentage
 * @param earned - Total credits earned
 * @param required - Total credits required
 * @returns Progress percentage (0-100), capped at 100
 */
export function calculateProgressPercentage(earned: number, required: number): number {
    if (required <= 0) return 0;
    return Math.min((earned / required) * 100, 100);
}

/**
 * Parse requirement data for display
 * @param requirement - CPD requirement
 * @returns Parsed requirement data
 */
export function parseRequirementForDisplay(requirement: CPDRequirement) {
    return {
        earned: safeParseNumber(requirement.earned_credits),
        required: safeParseNumber(requirement.annual_requirement),
        percent: requirement.completion_percent,
        remaining: safeParseNumber(requirement.credits_remaining),
        isComplete: requirement.completion_percent >= 100,
    };
}

/**
 * Parse transaction credits for display
 * @param transaction - CPD transaction
 * @returns Parsed transaction data
 */
export function parseTransactionForDisplay(transaction: CPDTransaction) {
    const credits = safeParseNumber(transaction.credits);
    return {
        credits,
        isPositive: credits >= 0,
        balanceAfter: safeParseNumber(transaction.balance_after),
    };
}
