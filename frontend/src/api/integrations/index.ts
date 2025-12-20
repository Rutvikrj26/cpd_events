import client from '../client';
import { ZoomStatus, ZoomCallbackResponse, ZoomDisconnectResponse } from './types';

const BASE_URL = '/integrations/zoom';

export const getZoomStatus = async (): Promise<ZoomStatus> => {
    const response = await client.get<ZoomStatus>(`${BASE_URL}/status/`);
    return response.data;
};

export const disconnectZoom = async (): Promise<ZoomDisconnectResponse> => {
    const response = await client.post<ZoomDisconnectResponse>(`${BASE_URL}/disconnect/`);
    return response.data;
};

export const completeZoomOAuth = async (code: string): Promise<ZoomCallbackResponse> => {
    const response = await client.get<ZoomCallbackResponse>(`${BASE_URL}/callback/`, {
        params: { code }
    });
    return response.data;
};

// Generate OAuth URL
export const initiateZoomOAuth = async (): Promise<string> => {
    const response = await client.get<{ url: string }>(`${BASE_URL}/initiate/`);
    return response.data.url;
};
