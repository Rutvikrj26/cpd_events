import { create } from 'zustand';

/**
 * UI store — cross-cutting transient client state.
 *
 * Use for things that span features and don't belong in a URL or in
 * server state: dialog dispatch, command-menu open, sidebar collapsed,
 * mobile-drawer open, etc.
 *
 * **Don't** use for feature-local UI state (a feature's tab selection
 * lives in that feature's own store or in URL params).
 */

export interface DialogDescriptor<P = unknown> {
    /** Stable type name registered in the DialogHost. */
    type: string;
    /** Props passed to the dialog component. */
    props?: P;
}

interface UIState {
    /** Dialog stack — multiple dialogs can be open at once (e.g. confirm-on-cancel). */
    dialogs: DialogDescriptor[];
    /** Mobile sidebar / nav drawer. */
    mobileNavOpen: boolean;
    /** Desktop sidebar collapsed flag. */
    sidebarCollapsed: boolean;
    /** Cmd-K command menu. */
    commandMenuOpen: boolean;

    openDialog: <P>(descriptor: DialogDescriptor<P>) => void;
    closeDialog: () => void;
    closeAllDialogs: () => void;

    setMobileNavOpen: (open: boolean) => void;
    toggleMobileNav: () => void;

    setSidebarCollapsed: (collapsed: boolean) => void;
    toggleSidebar: () => void;

    setCommandMenuOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
    dialogs: [],
    mobileNavOpen: false,
    sidebarCollapsed: false,
    commandMenuOpen: false,

    openDialog: (descriptor) =>
        set((s) => ({ dialogs: [...s.dialogs, descriptor as DialogDescriptor] })),
    closeDialog: () => set((s) => ({ dialogs: s.dialogs.slice(0, -1) })),
    closeAllDialogs: () => set({ dialogs: [] }),

    setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
    toggleMobileNav: () => set((s) => ({ mobileNavOpen: !s.mobileNavOpen })),

    setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
    toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

    setCommandMenuOpen: (open) => set({ commandMenuOpen: open }),
}));

/** Selectors — encourage usage so subscribers re-render only when their slice changes. */
export const selectTopDialog = (s: UIState): DialogDescriptor | null =>
    s.dialogs.length > 0 ? s.dialogs[s.dialogs.length - 1] : null;
