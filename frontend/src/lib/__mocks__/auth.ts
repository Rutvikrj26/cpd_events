import { vi } from 'vitest';

export const setToken = vi.fn();
export const getToken = vi.fn(() => "fake-valid-token");
export const removeToken = vi.fn();
export const isTokenValid = vi.fn(() => true);
export const getUserFromToken = vi.fn(() => ({ uuid: "org-user-id" }));
