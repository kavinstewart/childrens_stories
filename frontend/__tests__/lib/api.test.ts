/**
 * Unit tests for api.ts
 */
import { api, _resetStoriesCache } from '../../lib/api';

// Mock fetch for listStories tests
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('getSpreadImageUrl', () => {
  const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://dev.exoselfsystems.com';

  describe('returns absolute URL', () => {
    it('always returns URL starting with https:// or http://', () => {
      // This is critical - the native downloader requires absolute URLs
      // Relative URLs like /stories/abc/spreads/1/image will fail
      const url = api.getSpreadImageUrl('story-123', 1);
      expect(url).toMatch(/^https?:\/\//);
    });

    it('never returns a relative URL', () => {
      const url = api.getSpreadImageUrl('story-123', 1);
      expect(url).not.toMatch(/^\/[^/]/); // Not starting with single slash
    });
  });

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

describe('listStories caching', () => {
  const mockStoriesResponse = {
    stories: [
      { id: 'story-1', title: 'Story 1', status: 'completed' },
      { id: 'story-2', title: 'Story 2', status: 'completed' },
    ],
    total: 2,
    limit: 10,
    offset: 0,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    _resetStoriesCache();
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockStoriesResponse),
    });
  });

  it('returns cached response within TTL', async () => {
    // First call
    const result1 = await api.listStories();
    expect(result1.stories).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Second call should use cache
    const result2 = await api.listStories();
    expect(result2.stories).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledTimes(1); // Still 1, no new fetch
  });

  it('fetches fresh data after cache expires', async () => {
    // First call
    await api.listStories();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Reset cache to simulate expiration
    _resetStoriesCache();

    // Second call should fetch fresh
    await api.listStories();
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('does not cache different query params', async () => {
    // Call with limit=5
    await api.listStories({ limit: 5 });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Call with limit=10 should fetch again
    await api.listStories({ limit: 10 });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('caches same params separately', async () => {
    // Call with limit=5 twice
    await api.listStories({ limit: 5 });
    await api.listStories({ limit: 5 });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Call with limit=10 twice
    await api.listStories({ limit: 10 });
    await api.listStories({ limit: 10 });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('invalidates cache on invalidateStoriesCache call', async () => {
    // First call
    await api.listStories();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Invalidate
    api.invalidateStoriesCache();

    // Should fetch fresh
    await api.listStories();
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
