import api from "../client";
import type { Speaker, CreateSpeakerRequest, UpdateSpeakerRequest } from "./types";

export async function getSpeakers(): Promise<Speaker[]> {
    const response = await api.get<Speaker[]>("/speakers/");
    return response.data;
}

export async function getSpeaker(uuid: string): Promise<Speaker> {
    const response = await api.get<Speaker>(`/speakers/${uuid}/`);
    return response.data;
}

export async function createSpeaker(data: CreateSpeakerRequest): Promise<Speaker> {
    const response = await api.post<Speaker>("/speakers/", data);
    return response.data;
}

export async function updateSpeaker(uuid: string, data: UpdateSpeakerRequest): Promise<Speaker> {
    const response = await api.patch<Speaker>(`/speakers/${uuid}/`, data);
    return response.data;
}

export async function deleteSpeaker(uuid: string): Promise<void> {
    await api.delete(`/speakers/${uuid}/`);
}
