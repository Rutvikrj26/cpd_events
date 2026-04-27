import { useMediaQuery } from './useMediaQuery';

/**
 * Tailwind-aligned breakpoint hook. Returns the largest breakpoint the
 * viewport currently satisfies, plus boolean flags for each tier.
 *
 * Mirror of tailwind.config.cjs defaults:
 *   sm  640
 *   md  768
 *   lg  1024
 *   xl  1280
 *   2xl 1400 (custom container; we treat as 1400)
 */

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface BreakpointState {
    current: Breakpoint;
    isXs: boolean;
    isSm: boolean;
    isMd: boolean;
    isLg: boolean;
    isXl: boolean;
    is2xl: boolean;
    /** true on tablet and up — convenience for "show desktop layout". */
    isTabletUp: boolean;
    /** true on desktop and up. */
    isDesktopUp: boolean;
}

export function useBreakpoint(): BreakpointState {
    const isSm = useMediaQuery('(min-width: 640px)');
    const isMd = useMediaQuery('(min-width: 768px)');
    const isLg = useMediaQuery('(min-width: 1024px)');
    const isXl = useMediaQuery('(min-width: 1280px)');
    const is2xl = useMediaQuery('(min-width: 1400px)');

    const current: Breakpoint = is2xl ? '2xl' : isXl ? 'xl' : isLg ? 'lg' : isMd ? 'md' : isSm ? 'sm' : 'xs';

    return {
        current,
        isXs: !isSm,
        isSm,
        isMd,
        isLg,
        isXl,
        is2xl,
        isTabletUp: isMd,
        isDesktopUp: isLg,
    };
}
