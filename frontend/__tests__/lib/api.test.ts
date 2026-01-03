/**
 * Unit tests for image URL cache busting in api.ts
 */
import { api } from '../../lib/api';

describe('getSpreadImageUrl', () => {
  const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://dev.exoselfsystems.com';

  describe('without timestamp (no cache busting)', () => {
    it('returns base URL without query params', () => {
      const url = api.getSpreadImageUrl('abc', 3);
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image`);
    });

    it('handles different story IDs and spread numbers', () => {
      const url = api.getSpreadImageUrl('story-123', 7);
      expect(url).toBe(`${API_BASE_URL}/stories/story-123/spreads/7/image`);
    });

    it('handles spread number 1 (first spread)', () => {
      const url = api.getSpreadImageUrl('abc', 1);
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/1/image`);
    });

    it('handles spread number 12 (last spread)', () => {
      const url = api.getSpreadImageUrl('abc', 12);
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/12/image`);
    });
  });

  describe('with timestamp (cache busting)', () => {
    it('appends version param with ISO timestamp', () => {
      const url = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00Z');
      const expectedMs = new Date('2024-01-15T10:30:00Z').getTime();
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image?v=${expectedMs}`);
    });

    it('handles different timestamps', () => {
      const url = api.getSpreadImageUrl('abc', 3, '2025-06-20T15:45:30Z');
      const expectedMs = new Date('2025-06-20T15:45:30Z').getTime();
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image?v=${expectedMs}`);
    });

    it('handles timestamps with timezone offset', () => {
      // This tests that the conversion works with timezone-aware strings
      const url = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00+05:00');
      const expectedMs = new Date('2024-01-15T10:30:00+05:00').getTime();
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image?v=${expectedMs}`);
    });

    it('handles timestamps without timezone (interpreted as local)', () => {
      const url = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00');
      const expectedMs = new Date('2024-01-15T10:30:00').getTime();
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image?v=${expectedMs}`);
    });
  });

  describe('cache busting behavior', () => {
    it('different timestamps produce different URLs', () => {
      const url1 = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00Z');
      const url2 = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:01Z');
      expect(url1).not.toBe(url2);
    });

    it('same timestamp produces same URL', () => {
      const url1 = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00Z');
      const url2 = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00Z');
      expect(url1).toBe(url2);
    });

    it('undefined timestamp differs from defined timestamp', () => {
      const urlNoTimestamp = api.getSpreadImageUrl('abc', 3);
      const urlWithTimestamp = api.getSpreadImageUrl('abc', 3, '2024-01-15T10:30:00Z');
      expect(urlNoTimestamp).not.toBe(urlWithTimestamp);
      expect(urlNoTimestamp).not.toContain('?v=');
      expect(urlWithTimestamp).toContain('?v=');
    });
  });

  describe('edge cases', () => {
    it('handles empty string timestamp by returning base URL', () => {
      // Empty string is falsy, so implementation returns base URL without cache buster
      const url = api.getSpreadImageUrl('abc', 3, '');
      // This is correct behavior - empty string means no cache busting
      expect(url).toBe(`${API_BASE_URL}/stories/abc/spreads/3/image`);
      expect(url).not.toContain('?v=');
    });

    it('handles UUIDs as story IDs', () => {
      const uuid = '123e4567-e89b-12d3-a456-426614174000';
      const url = api.getSpreadImageUrl(uuid, 5, '2024-01-15T10:30:00Z');
      expect(url).toContain(`/stories/${uuid}/spreads/5/image`);
    });
  });
});
