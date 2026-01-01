import client from "../client";

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

// =============================================================================
// Types
// =============================================================================

export interface Tag {
    uuid: string;
    name: string;
    color: string;
    description: string;
    contact_count: number;
    created_at: string;
    updated_at: string;
}

export interface ContactList {
    uuid: string;
    name: string;
    description: string;
    is_default: boolean;
    contact_count: number;
    created_at: string;
    updated_at: string;
}

export interface Contact {
    uuid: string;
    contact_list: Pick<ContactList, 'uuid' | 'name'>;
    email: string;
    full_name: string;
    professional_title: string;
    organization_name: string;
    phone: string;
    notes: string;
    tags: Tag[];
    source: string;
    // Engagement
    events_invited_count: number;
    events_attended_count: number;
    last_invited_at: string | null;
    last_attended_at: string | null;
    // Status
    email_opted_out: boolean;
    email_bounced: boolean;
    is_linked: boolean;
    display_name: string;
    created_at: string;
    updated_at: string;
}

export interface CreateContactParams {
    email: string;
    full_name: string;
    professional_title?: string;
    organization_name?: string;
    phone?: string;
    notes?: string;
    tag_uuids?: string[];
}

export interface CreateContactListParams {
    name: string;
    description?: string;
    is_default?: boolean;
}

// =============================================================================
// API Functions
// =============================================================================

// Contact Lists
export async function getContactLists(): Promise<PaginatedResponse<ContactList>> {
    const response = await client.get("/api/v1/contact-lists/");
    return response.data;
}

export async function createContactList(data: CreateContactListParams): Promise<ContactList> {
    const response = await client.post("/api/v1/contact-lists/", data);
    return response.data;
}

export async function getContactList(uuid: string): Promise<ContactList> {
    const response = await client.get(`/api/v1/contact-lists/${uuid}/`);
    return response.data;
}

// Contacts (Organized by List)
export async function getContacts(listUuid: string, params?: any): Promise<PaginatedResponse<Contact>> {
    const response = await client.get(`/api/v1/contact-lists/${listUuid}/contacts/`, { params });
    return response.data;
}

export async function createContact(listUuid: string, data: CreateContactParams): Promise<Contact> {
    const response = await client.post(`/api/v1/contact-lists/${listUuid}/contacts/`, data);
    return response.data;
}

export async function deleteContact(listUuid: string, contactUuid: string): Promise<void> {
    await client.delete(`/api/v1/contact-lists/${listUuid}/contacts/${contactUuid}/`);
}

// Tags
export async function getTags(): Promise<PaginatedResponse<Tag>> {
    const response = await client.get("/api/v1/tags/");
    return response.data;
}
