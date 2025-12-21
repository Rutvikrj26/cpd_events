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

// Get all events with Zoom meetings for the current user
export const getZoomMeetings = async (): Promise<ZoomMeeting[]> => {
    const response = await client.get<ZoomMeeting[]>(`${BASE_URL}/meetings/`);
    return response.data;
};

export interface ZoomMeeting {
    uuid: string;
    title: string;
    status: string;
    starts_at: string;
    zoom_meeting_id: string;
    zoom_join_url: string;
    zoom_password: string;
    created_at: string;
}
