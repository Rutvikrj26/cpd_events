import { describe, it, expect } from 'vitest';
import {
  safeParseNumber,
  calculateTotalCredits,
  calculateTotalRequired,
  calculateProgressPercentage,
  formatCredits,
  parseRequirementForDisplay,
  parseTransactionForDisplay,
} from '../cpdUtils';

describe('cpdUtils', () => {
  describe('safeParseNumber', () => {
    it('should return 0 for null', () => {
      expect(safeParseNumber(null)).toBe(0);
    });

    it('should return 0 for undefined', () => {
      expect(safeParseNumber(undefined)).toBe(0);
    });

    it('should parse string numbers correctly', () => {
      expect(safeParseNumber('11.50')).toBe(11.5);
      expect(safeParseNumber('0.00')).toBe(0);
      expect(safeParseNumber('100')).toBe(100);
    });

    it('should handle already-numeric values', () => {
      expect(safeParseNumber(42)).toBe(42);
      expect(safeParseNumber(0)).toBe(0);
      expect(safeParseNumber(11.5)).toBe(11.5);
    });

    it('should return 0 for invalid strings', () => {
      expect(safeParseNumber('invalid')).toBe(0);
      expect(safeParseNumber('NaN')).toBe(0);
      expect(safeParseNumber('')).toBe(0);
    });

    it('should handle edge cases', () => {
      expect(safeParseNumber(NaN)).toBe(0);
      expect(safeParseNumber(Infinity)).toBe(Infinity);
      expect(safeParseNumber(-Infinity)).toBe(-Infinity);
    });
  });

  describe('calculateTotalCredits', () => {
    it('should prioritize progress.total_credits_earned', () => {
      const progress: any = {
        total_credits_earned: '15.75',
        requirements: [
          { earned_credits: '5.00' },
        ],
      };

      expect(calculateTotalCredits(progress)).toBe(15.75);
    });

    it('should fall back to transactionSummary.current_balance', () => {
      const progress: any = {
        total_credits_earned: '0.00',
        requirements: [],
      };

      const transactionSummary: any = {
        current_balance: '12.50',
      };

      expect(calculateTotalCredits(progress, transactionSummary)).toBe(12.5);
    });

    it('should calculate from requirements when progress is zero', () => {
      const progress: any = {
        total_credits_earned: '0.00',
        requirements: [
          { earned_credits: '5.50' },
          { earned_credits: '3.25' },
          { earned_credits: '2.25' },
        ],
      };

      expect(calculateTotalCredits(progress)).toBe(11.0);
    });

    it('should return 0 when all sources are zero', () => {
      const progress: any = {
        total_credits_earned: '0.00',
        requirements: [],
      };

      expect(calculateTotalCredits(progress)).toBe(0);
    });

    it('should handle null/undefined inputs gracefully', () => {
      const progress: any = {
        total_credits_earned: null,
        requirements: [
          { earned_credits: '5.00' },
          { earned_credits: '6.00' },
        ],
      };

      expect(calculateTotalCredits(progress)).toBe(11.0);
    });
  });

  describe('calculateTotalRequired', () => {
    it('should sum annual requirements correctly', () => {
      const requirements: any[] = [
        { annual_requirement: '10.00' },
        { annual_requirement: '15.50' },
        { annual_requirement: '24.50' },
      ];

      expect(calculateTotalRequired(requirements)).toBe(50.0);
    });

    it('should handle string and number types', () => {
      const requirements: any[] = [
        { annual_requirement: '10.00' },
        { annual_requirement: 15 },
      ];

      expect(calculateTotalRequired(requirements)).toBe(25.0);
    });

    it('should return 0 for empty array', () => {
      expect(calculateTotalRequired([])).toBe(0);
    });

    it('should handle null/undefined values', () => {
      const requirements: any[] = [
        { annual_requirement: '10.00' },
        { annual_requirement: null },
        { annual_requirement: undefined },
      ];

      expect(calculateTotalRequired(requirements)).toBe(10.0);
    });
  });

  describe('calculateProgressPercentage', () => {
    it('should calculate percentage correctly', () => {
      expect(calculateProgressPercentage(25, 100)).toBe(25);
      expect(calculateProgressPercentage(11, 50)).toBe(22);
      expect(calculateProgressPercentage(75, 100)).toBe(75);
    });

    it('should return 0 when total is 0', () => {
      expect(calculateProgressPercentage(10, 0)).toBe(0);
    });

    it('should cap at 100%', () => {
      expect(calculateProgressPercentage(150, 100)).toBe(100);
      expect(calculateProgressPercentage(200, 100)).toBe(100);
    });

    it('should handle decimal values', () => {
      expect(calculateProgressPercentage(11.5, 50)).toBe(23);
      expect(calculateProgressPercentage(33.33, 100)).toBe(33.33);
    });
  });

  describe('formatCredits', () => {
    it('should format to 1 decimal place', () => {
      expect(formatCredits(11.567)).toBe('11.6');
      expect(formatCredits(0)).toBe('0.0');
      expect(formatCredits(100)).toBe('100.0');
    });

    it('should handle 2 decimal places', () => {
      expect(formatCredits(11.567, 2)).toBe('11.57');
      expect(formatCredits(0, 2)).toBe('0.00');
    });
  });

  describe('parseRequirementForDisplay', () => {
    it('should parse requirement data correctly', () => {
      const requirement: any = {
        earned_credits: '8.50',
        annual_requirement: '10.00',
        completion_percent: 85,
        credits_remaining: '1.50',
      };

      const result = parseRequirementForDisplay(requirement);

      expect(result.earned).toBe(8.5);
      expect(result.required).toBe(10.0);
      expect(result.percent).toBe(85);
      expect(result.remaining).toBe(1.5);
      expect(result.isComplete).toBe(false);
    });

    it('should handle null/undefined values', () => {
      const requirement: any = {
        earned_credits: null,
        annual_requirement: undefined,
        completion_percent: 0,
        credits_remaining: null,
      };

      const result = parseRequirementForDisplay(requirement);

      expect(result.earned).toBe(0);
      expect(result.required).toBe(0);
      expect(result.percent).toBe(0);
      expect(result.remaining).toBe(0);
      expect(result.isComplete).toBe(false);
    });

    it('should mark as complete when 100%', () => {
      const requirement: any = {
        earned_credits: '15.00',
        annual_requirement: '10.00',
        completion_percent: 100,
        credits_remaining: '0.00',
      };

      const result = parseRequirementForDisplay(requirement);

      expect(result.percent).toBe(100);
      expect(result.isComplete).toBe(true);
    });
  });

  describe('parseTransactionForDisplay', () => {
    it('should parse transaction data correctly', () => {
      const transaction: any = {
        credits: '3.50',
        balance_after: '15.50',
      };

      const result = parseTransactionForDisplay(transaction);

      expect(result.credits).toBe(3.5);
      expect(result.isPositive).toBe(true);
      expect(result.balanceAfter).toBe(15.5);
    });

    it('should handle null/undefined values', () => {
      const transaction: any = {
        credits: null,
        balance_after: undefined,
      };

      const result = parseTransactionForDisplay(transaction);

      expect(result.credits).toBe(0);
      expect(result.isPositive).toBe(true);
      expect(result.balanceAfter).toBe(0);
    });

    it('should handle negative credits', () => {
      const transaction: any = {
        credits: '-2.00',
        balance_after: '8.00',
      };

      const result = parseTransactionForDisplay(transaction);

      expect(result.credits).toBe(-2.0);
      expect(result.isPositive).toBe(false);
      expect(result.balanceAfter).toBe(8.0);
    });
  });
});
