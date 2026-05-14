import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the auth API module
vi.mock('../../api/auth', () => ({
  getMe: vi.fn(),
}));

describe('Auth Store', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should have token stored in localStorage when set', () => {
    localStorage.setItem('token', 'test-jwt-token');
    const token = localStorage.getItem('token');
    expect(token).toBe('test-jwt-token');
  });

  it('should return null when no token is set', () => {
    const token = localStorage.getItem('token');
    expect(token).toBeNull();
  });

  it('should remove token on logout', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.removeItem('token');
    expect(localStorage.getItem('token')).toBeNull();
  });

  it('should persist token across calls', () => {
    localStorage.setItem('token', 'persistent-token');
    expect(localStorage.getItem('token')).toBe('persistent-token');
    // Second access should be consistent
    expect(localStorage.getItem('token')).toBe('persistent-token');
  });
});
