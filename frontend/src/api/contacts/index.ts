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
    organization_uuid: string | null;
    is_shared: boolean;
    created_at: string;
    updated_at: string;
}

export interface ContactList {
    uuid: string;
    name: string;
    description: string;
    contact_count: number;
    organization_uuid: string | null;
    is_shared: boolean;
    created_at: string;
    updated_at: string;
}

export interface Contact {
    uuid: string;
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

export interface UpdateContactParams {
    email?: string;
    full_name?: string;
    professional_title?: string;
    organization_name?: string;
    phone?: string;
    notes?: string;
    tag_uuids?: string[];
}

export interface CreateTagParams {
    name: string;
    color?: string;
    description?: string;
    organization_uuid?: string;
}

export interface BulkImportParams {
    contacts: Array<{
        email: string;
        full_name: string;
        professional_title?: string;
        organization_name?: string;
        phone?: string;
        notes?: string;
    }>;
}

// =============================================================================
// Contacts API (simplified - auto-resolves user's list)
// =============================================================================

export async function getContacts(params?: Record<string, string>): Promise<PaginatedResponse<Contact>> {
    const response = await client.get("/contacts/", { params });
    return response.data;
}

export async function createContact(data: CreateContactParams): Promise<Contact> {
    const response = await client.post("/contacts/", data);
    return response.data;
}

export async function updateContact(uuid: string, data: UpdateContactParams): Promise<Contact> {
    const response = await client.patch(`/contacts/${uuid}/`, data);
    return response.data;
}

export async function deleteContact(uuid: string): Promise<void> {
    await client.delete(`/contacts/${uuid}/`);
}

export async function exportContacts(): Promise<void> {
    const response = await client.get("/contacts/export/", {
        responseType: 'blob'
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    const contentDisposition = response.headers['content-disposition'];
    let filename = 'contacts.csv';
    if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) filename = match[1];
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}

export async function bulkImportContacts(data: BulkImportParams): Promise<{ created: number; skipped: number }> {
    const response = await client.post("/contacts/bulk_create/", data);
    return response.data;
}

// =============================================================================
// Tags API
// =============================================================================

export async function getTags(): Promise<PaginatedResponse<Tag>> {
    const response = await client.get("/tags/");
    return response.data;
}

export async function createTag(data: CreateTagParams): Promise<Tag> {
    const response = await client.post("/tags/", data);
    return response.data;
}

// =============================================================================
// Contact Lists API (read-only, for org viewing)
// =============================================================================

export async function getContactLists(): Promise<PaginatedResponse<ContactList>> {
    const response = await client.get("/contact-lists/");
    return response.data;
}

export async function getContactList(uuid: string): Promise<ContactList> {
    const response = await client.get(`/contact-lists/${uuid}/`);
    return response.data;
}
