import { describe, expect, test } from 'bun:test';
import { formatUsageNumber } from '../src/services/usageNumber';

describe('使用统计数量单位', () => {
  test('百万以下保持普通数字格式', () => {
    expect(formatUsageNumber(999_999, 'en-US')).toBe('999,999');
    expect(formatUsageNumber(Number.NaN, 'en-US')).toBe('0');
  });

  test('百万级使用 M 并在达到阈值时自动切换为 B', () => {
    expect(formatUsageNumber(1_000_000, 'en-US')).toBe('1M');
    expect(formatUsageNumber(12_340_000, 'en-US')).toBe('12.3M');
    expect(formatUsageNumber(999_949_999, 'en-US')).toBe('999.9M');
    expect(formatUsageNumber(999_950_000, 'en-US')).toBe('1B');
    expect(formatUsageNumber(1_250_000_000, 'en-US')).toBe('1.3B');
  });
});
