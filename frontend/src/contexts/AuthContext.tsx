import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setToken, getToken, removeToken, isTokenValid, getUserFromToken } from '@/lib/auth';
import { login as apiLogin, signup as apiSignup, getCurrentUser } from '@/api/accounts';
import { User, LoginRequest, SignupRequest } from '@/api/accounts/types';
import { getManifest, Manifest } from '@/api/auth/manifest';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    manifest: Manifest | null;
    login: (data: LoginRequest) => Promise<void>;
    register: (data: SignupRequest) => Promise<void>;
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

    // Fetch manifest from backend
    const fetchManifest = async () => {
        try {
            const data = await getManifest();
            setManifest(data);
        } catch (error) {
            console.error('Failed to fetch manifest', error);
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

    const register = async (data: SignupRequest) => {
        try {
            const response = await apiSignup(data);

            // If we got tokens, log the user in (legacy/Google/future-proof)
            if (response.access && response.refresh && response.user) {
                setToken(response.access, response.refresh);
                setIsAuthenticated(true);
                setUser(response.user);
                await fetchManifest();
            }
            // If no tokens (email verification required), we just return successfully
            // The calling component (SignupPage) will handle the redirect.
        } catch (error) {
            console.error("Registration failed", error);
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
            login,
            register,
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

