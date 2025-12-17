import axios from 'axios';
import { getToken, removeToken } from '@/lib/auth'; // We'll keep auth helpers in lib for now or move them later if strictly modular

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

client.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

client.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            removeToken();
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default client;
