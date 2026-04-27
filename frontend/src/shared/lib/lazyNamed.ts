import { lazy, type ComponentType, type LazyExoticComponent } from 'react';

/**
 * lazyNamed — like React.lazy but for named exports.
 *
 * Usage:
 *     const LoginPage = lazyNamed(() => import('@/pages/auth/LoginPage'), 'LoginPage');
 *
 * Why not just rely on default exports? Many of our pages use named
 * exports (e.g. `export function LoginPage`) to make them more
 * grep-able. This wrapper bridges the gap without forcing a
 * `default-export` rewrite.
 */
export function lazyNamed<TName extends string, TModule extends Record<TName, ComponentType<any>>>(
    factory: () => Promise<TModule>,
    exportName: TName
): LazyExoticComponent<TModule[TName]> {
    return lazy(async () => {
        const mod = await factory();
        return { default: mod[exportName] };
    });
}
