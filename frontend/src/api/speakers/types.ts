export interface Speaker {
    uuid: string;
    name: string;
    bio: string;
    qualifications: string;
    photo: string | null;
    email: string;
    linkedin_url: string;
    is_active: boolean;
    owner_name: string;
    created_at: string;
}

export interface CreateSpeakerRequest {
    name: string;
    bio?: string;
    qualifications?: string;
    email?: string;
    linkedin_url?: string;
    is_active?: boolean;
}

export type UpdateSpeakerRequest = Partial<CreateSpeakerRequest>;
