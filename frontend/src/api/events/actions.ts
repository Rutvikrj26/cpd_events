import client from '../client';

/**
 * Publish an event (transitions from draft to published)
 */
export const publishEvent = async (uuid: string): Promise<void> => {
    await client.post(`/events/${uuid}/publish/`);
};

/**
 * Cancel an event
 */
export const cancelEvent = async (uuid: string): Promise<void> => {
    await client.post(`/events/${uuid}/cancel/`);
};

/**
 * Duplicate an event (creates a new draft copy)
 */
export const duplicateEvent = async (uuid: string): Promise<any> => {
    const response = await client.post(`/events/${uuid}/duplicate/`);
    return response.data;
};

/**
 * Revert an event to draft status
 */
export const unpublishEvent = async (uuid: string): Promise<void> => {
    await client.post(`/events/${uuid}/unpublish/`);
};
