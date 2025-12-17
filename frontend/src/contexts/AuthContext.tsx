import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setToken, getToken, removeToken, isTokenValid, getUserFromToken } from '@/lib/auth';
import { login as apiLogin, signup as apiSignup, getCurrentUser } from '@/api/accounts';
import { User, LoginRequest, SignupRequest } from '@/api/accounts/types';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (data: LoginRequest) => Promise<void>;
    register: (data: SignupRequest) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);

    // Initialize auth state
    useEffect(() => {
        const initializeAuth = async () => {
            const token = getToken();
            if (token && isTokenValid(token)) {
                // We have a token, try to fetch user details
                try {
                    // You might want to create a dedicated 'me' endpoint in backend
                    // For now, we'll decode the token to get UUID and maybe fetch profile
                    // But looking at backend, we don't have a direct /users/me endpoint standard yet
                    // except implicitly via /accounts/profile/ or similar.
                    // Let's assume we can rely on token for minimal auth state
                    // and fetch full profile later if needed.

                    const decodedUser = getUserFromToken();
                    // Ideally fetch full user profile here:
                    // const response = await api.get('/accounts/profile/');
                    // setUser(response.data);

                    // Temporary: just set basic user from token
                    if (decodedUser) {
                        setUser({ uuid: decodedUser.uuid } as User); // We initially only have UUID
                        setIsAuthenticated(true);

                        // Try to fetch full profile to get name and role
                        try {
                            const userProfile = await getCurrentUser();
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

            // Fetch profile immediately after login
            const userProfile = await getCurrentUser();
            setUser(userProfile);

        } catch (error) {
            console.error("Login failed", error);
            throw error;
        }
    };

    const register = async (data: SignupRequest) => {
        try {
            await apiSignup(data);
            // Automatically login after register? Or redirect to login? 
            // Spec says redirect to verify email mostly. 
            // We will let the calling component handle the next steps.
        } catch (error) {
            console.error("Registration failed", error);
            throw error;
        }
    };

    const logout = () => {
        removeToken();
        setUser(null);
        setIsAuthenticated(false);
        window.location.href = '/login';
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, register, logout }}>
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
