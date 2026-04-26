/**
 * features/auth — public surface.
 *
 * Pages and other features import from here. Internal store + plumbing
 * stay un-exported.
 */
export {
    useAuth,
    useCurrentUser,
    useManifest,
    useDeployment,
    useLogin,
    useCompleteLogin,
    useLogout,
    authKeys,
} from './hooks';
export type { UseAuthReturn } from './hooks';
export { ProtectedRoute, BrandTheme } from './components';
export { useAuthStore } from './store/authStore';
