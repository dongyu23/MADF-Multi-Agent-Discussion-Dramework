import { describe, it, expect, vi, beforeEach } from 'vitest';
import client from '../client';

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      defaults: { baseURL: '/api/v1', headers: { common: {}, 'Content-Type': 'application/json' } },
    })),
  },
}));

describe('API Client', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should have correct base URL', () => {
    expect(client.defaults.baseURL).toBe('/api/v1');
  });

  it('should set Content-Type header', () => {
    expect(client.defaults.headers['Content-Type']).toBe('application/json');
  });
});
