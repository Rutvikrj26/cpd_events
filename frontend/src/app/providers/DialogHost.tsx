import * as React from 'react';
import { useUIStore, selectTopDialog } from '@/stores';

/**
 * Dialog registry — maps a dialog `type` (string) to its component.
 *
 * Each feature contributes its dialogs at module load via
 * `registerDialog`. Pages dispatch dialogs via:
 *
 *     useUIStore.getState().openDialog({ type: 'my-feature/confirm-delete', props: {...} });
 *
 * The DialogHost mounts only one dialog at a time (the top of the
 * stack). When `closeDialog` is called the top is popped.
 *
 * This indirection eliminates ad-hoc `useState(false)` modal patterns
 * scattered across pages and ensures dialogs survive route changes if
 * the page wants them to.
 */

type DialogComponent<P = any> = React.ComponentType<P & { onClose: () => void }>;

const registry = new Map<string, DialogComponent>();

/**
 * Register a dialog component for a given `type`. Call from the feature
 * that owns the dialog. Idempotent — registering the same type twice
 * keeps the latest definition.
 */
export function registerDialog<P>(type: string, component: DialogComponent<P>) {
    registry.set(type, component as DialogComponent);
}

/**
 * Helper: open a registered dialog from anywhere (component or not).
 * Uses the store's imperative API.
 */
export function openDialog<P>(type: string, props?: P) {
    useUIStore.getState().openDialog({ type, props });
}

export function closeDialog() {
    useUIStore.getState().closeDialog();
}

/**
 * DialogHost — mount once near the root of the app. Renders the topmost
 * dialog from the uiStore. Registered components must accept `onClose`
 * in their props (the host wires it up to `closeDialog`).
 */
export function DialogHost() {
    const top = useUIStore(selectTopDialog);
    if (!top) return null;
    const Component = registry.get(top.type);
    if (!Component) {
        if (typeof console !== 'undefined') {
            console.warn(`[DialogHost] No component registered for dialog type "${top.type}"`);
        }
        return null;
    }
    return <Component {...(top.props as any)} onClose={closeDialog} />;
}
