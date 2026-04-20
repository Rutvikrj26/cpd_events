import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setToken, getToken, removeToken, isTokenValid, getUserFromToken } from '@/lib/auth';
import { login as apiLogin, getCurrentUser } from '@/api/accounts';
import { User, LoginRequest } from '@/api/accounts/types';
import { getManifest, getDeploymentConfig, Manifest, DeploymentConfig } from '@/api/auth/manifest';

/** Convert "#rrggbb" / "#rgb" → "H S% L%" string used by hsl(var(--x)) in Tailwind. */
function hexToHslTriplet(hex: string): string | null {
    const cleaned = hex.trim().replace(/^#/, '');
    const full =
        cleaned.length === 3
            ? cleaned.split('').map((c) => c + c).join('')
            : cleaned.length === 6
                ? cleaned
                : null;
    if (!full || !/^[0-9a-f]{6}$/i.test(full)) return null;
    const r = parseInt(full.slice(0, 2), 16) / 255;
    const g = parseInt(full.slice(2, 4), 16) / 255;
    const b = parseInt(full.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h *= 60;
    }
    return `${Math.round(h)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    manifest: Manifest | null;
    deployment: DeploymentConfig | null;
    login: (data: LoginRequest) => Promise<void>;
    logout: () => void;
    hasRoute: (routeKey: string) => boolean;
    hasFeature: (feature: keyof Manifest['features']) => boolean;
    refreshManifest: () => Promise<void>;
    refreshUser: () => Promise<void>;
    setToken: (access: string, refresh: string) => void;
    setIsAuthenticated: (value: boolean) => void;
    setUser: (user: User | null) => void;
    fetchManifest: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [manifest, setManifest] = useState<Manifest | null>(null);
    const [deployment, setDeployment] = useState<DeploymentConfig | null>(null);

    // Fetch manifest from backend (also populates deployment config)
    const fetchManifest = async () => {
        try {
            const data = await getManifest();
            setManifest(data);
            setDeployment(data.deployment);
        } catch (error) {
            console.error('Failed to fetch manifest', error);
        }
    };

    // Fetch public deployment config (no auth required)
    const fetchDeployment = async () => {
        try {
            const data = await getDeploymentConfig();
            setDeployment(data);
        } catch (error) {
            console.error('Failed to fetch deployment config', error);
        }
    };

    // Fetch user profile from backend
    const refreshUser = async () => {
        try {
            const userProfile = await getCurrentUser();
            setUser(userProfile);
        } catch (error) {
            console.error('Failed to refresh user profile', error);
        }
    };

    // Apply brand primary color + favicon whenever deployment config changes.
    useEffect(() => {
        const color = deployment?.institution_primary_color;
        if (color) {
            // Convert #RRGGBB → "H S% L%" so Tailwind's hsl(var(--primary)) picks it up.
            const hsl = hexToHslTriplet(color);
            if (hsl) {
                document.documentElement.style.setProperty('--primary', hsl);
                // Derive readable foreground: white on dark brand, dark on light brand.
                const [, , l] = hsl.match(/(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%/) || [];
                const lightness = parseFloat(l || '0');
                document.documentElement.style.setProperty(
                    '--primary-foreground',
                    lightness > 55 ? '220 13% 18%' : '0 0% 100%',
                );
            }
            // Keep raw hex accessible for components that want it verbatim.
            document.documentElement.style.setProperty('--brand-primary', color);
        }
        const favicon = deployment?.institution_favicon_url;
        if (favicon) {
            let link = document.querySelector<HTMLLinkElement>("link[rel='icon']");
            if (!link) {
                link = document.createElement('link');
                link.rel = 'icon';
                document.head.appendChild(link);
            }
            link.href = favicon;
        }
        const name = deployment?.institution_name;
        if (name && !document.title.startsWith(name)) {
            document.title = name;
        }
    }, [deployment?.institution_primary_color, deployment?.institution_favicon_url, deployment?.institution_name]);

    // Helper: Check if user has access to a route
    const hasRoute = (routeKey: string): boolean => {
        if (!manifest) return false;
        return manifest.routes.includes(routeKey);
    };

    // Helper: Check if user has a feature enabled
    const hasFeature = (feature: keyof Manifest['features']): boolean => {
        if (!manifest) return false;
        return manifest.features[feature] ?? false;
    };

    // Initialize auth state
    useEffect(() => {
        const initializeAuth = async () => {
            const token = getToken();
            if (token && isTokenValid(token)) {
                try {
                    const decodedUser = getUserFromToken();
                    if (decodedUser) {
                        setUser({ uuid: decodedUser.uuid } as User);
                        setIsAuthenticated(true);

                        // Fetch full profile and manifest
                        try {
                            const [userProfile] = await Promise.all([
                                getCurrentUser(),
                                fetchManifest(),
                            ]);
                            setUser(userProfile);
                        } catch (e) {
                            console.error("Failed to fetch profile", e);
                        }
                    }
                } catch (error) {
                    console.error("Auth initialization failed", error);
                    removeToken();
                }
            } else {
                // Unauthenticated: still fetch public deployment config so
                // login pages can gate UI on registration_mode.
                await fetchDeployment();
            }
            setIsLoading(false);
        };

        initializeAuth();
    }, []);

    const login = async (data: LoginRequest) => {
        try {
            const { access, refresh } = await apiLogin(data);
            setToken(access, refresh);
            setIsAuthenticated(true);

            // Fetch profile and manifest after login
            const [userProfile] = await Promise.all([
                getCurrentUser(),
                fetchManifest(),
            ]);
            setUser(userProfile);

        } catch (error) {
            console.error("Login failed", error);
            throw error;
        }
    };

    const logout = () => {
        removeToken();
        setUser(null);
        setManifest(null);
        setIsAuthenticated(false);
        window.location.href = '/login';
    };

    return (
        <AuthContext.Provider value={{
            user,
            isAuthenticated,
            isLoading,
            manifest,
            deployment,
            login,
            logout,
            hasRoute,
            hasFeature,
            refreshManifest: fetchManifest,
            refreshUser,
            setToken,
            setIsAuthenticated,
            setUser,
            fetchManifest,
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
