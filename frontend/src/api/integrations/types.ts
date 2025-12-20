export interface ZoomStatus {
    is_connected: boolean;
    zoom_email?: string;
}

export interface ZoomCallbackResponse {
    status: string;
}

export interface ZoomDisconnectResponse {
    status: string;
}
