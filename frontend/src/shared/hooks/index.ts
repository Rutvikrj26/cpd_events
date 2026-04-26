/**
 * Shared hooks — generic utilities used across features.
 *
 * Public surface only; internal helpers stay un-exported.
 */
export { useAsync } from './useAsync';
export type { UseAsyncResult } from './useAsync';
export { useBreakpoint } from './useBreakpoint';
export type { Breakpoint, BreakpointState } from './useBreakpoint';
export { useDebounce } from './useDebounce';
export { useDocumentTitle } from './useDocumentTitle';
export { useLocalStorage } from './useLocalStorage';
export { useMediaQuery } from './useMediaQuery';
export { usePagination } from './usePagination';
