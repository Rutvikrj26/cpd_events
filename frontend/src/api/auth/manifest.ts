/**
 * RBAC Manifest types and API.
 *
 * The manifest is returned by the backend and contains:
 * - The user's roles (Django Groups)
 * - Which routes they can access
 * - Which features are enabled for them
 * - Deployment configuration
 */

import client from '../client';

export interface DeploymentConfig {
    mode: 'single_tenant' | 'saas';
    registration_mode: 'invite_only' | 'admin_approval' | 'open';
    institution_name: string;
    institution_logo_url: string;
}

export interface Manifest {
    user: {
        roles: string[];
        primary_role: 'learner' | 'educator' | 'course_manager' | 'admin';
        is_staff: boolean;
    };
    routes: string[];
    features: {
        create_events: boolean;
        create_courses: boolean;
        manage_certificates: boolean;
        manage_users: boolean;
        configure_billing: boolean;
        browse_events: boolean;
        register_for_events: boolean;
        view_own_registrations: boolean;
        view_own_certificates: boolean;
    };
    deployment: DeploymentConfig;
}

/**
 * Fetch the user's manifest from the backend.
 * Call this after login to get the user's permissions.
 */
export const getManifest = async (): Promise<Manifest> => {
    const response = await client.get<Manifest>('/auth/manifest/');
    return response.data;
};
