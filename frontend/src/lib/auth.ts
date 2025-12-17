import { jwtDecode } from 'jwt-decode';

const TOKEN_KEY = 'cpd_auth_token';
const REFRESH_key = 'cpd_refresh_token';

export interface DecodedToken {
    user_uuid: string;
    exp: number;
    iat: number;
    jti: string;
}

export const setToken = (access: string, refresh?: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) {
        localStorage.setItem(REFRESH_key, refresh);
    }
};

export const getToken = () => {
    return localStorage.getItem(TOKEN_KEY);
};

export const getRefreshToken = () => {
    return localStorage.getItem(REFRESH_key);
};

export const removeToken = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_key);
};

export const isTokenValid = (token: string): boolean => {
    try {
        const decoded: DecodedToken = jwtDecode(token);
        return decoded.exp * 1000 > Date.now();
    } catch (error) {
        return false;
    }
};

export const getUserFromToken = () => {
    const token = getToken();
    if (!token) return null;

    try {
        const decoded: DecodedToken = jwtDecode(token);
        return {
            uuid: decoded.user_uuid,
        };
    } catch (error) {
        return null;
    }
};
