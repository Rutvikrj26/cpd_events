/**
 * RBAC Manifest types and API.
 * 
 * The manifest is returned by the backend and contains:
 * - The user's role
 * - Which routes they can access
 * - Which features are enabled for them
 */

import client from '../client';

export interface Manifest {
    role: 'attendee' | 'organizer' | 'course_manager' | 'admin';
    is_admin: boolean;
    routes: string[];
    features: {
        create_events: boolean;
        create_courses: boolean;
        manage_certificates: boolean;
        view_billing: boolean;
        browse_events: boolean;
        register_for_events: boolean;
        view_own_registrations: boolean;
        view_own_certificates: boolean;
        can_create_organization: boolean;
    };
}

/**
 * Fetch the user's manifest from the backend.
 * Call this after login to get the user's permissions.
 */
export const getManifest = async (): Promise<Manifest> => {
    const response = await client.get<Manifest>('/auth/manifest/');
    return response.data;
};
