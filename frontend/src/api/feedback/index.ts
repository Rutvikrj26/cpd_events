import client from '../client';
import {
    EventFeedback,
    EventFeedbackCreateRequest,
    EventFeedbackUpdateRequest
} from './types';

/**
 * Get all feedback accessible to the current user.
 * - Organizers see feedback for their events
 * - Attendees see their own feedback submissions
 */
export async function getFeedback(): Promise<EventFeedback[]> {
    const response = await client.get<EventFeedback[]>('/feedback/');
    return response.data;
}

/**
 * Get feedback for a specific event (organizer only)
 */
export async function getEventFeedback(eventUuid: string): Promise<EventFeedback[]> {
    const response = await client.get<EventFeedback[]>('/feedback/', {
        params: { event: eventUuid }
    });
    return response.data;
}

/**
 * Get a single feedback by UUID
 */
export async function getFeedbackById(uuid: string): Promise<EventFeedback> {
    const response = await client.get<EventFeedback>(`/feedback/${uuid}/`);
    return response.data;
}

/**
 * Check if user has already submitted feedback for a registration
 */
export async function getRegistrationFeedback(registrationUuid: string): Promise<EventFeedback | null> {
    try {
        const response = await client.get<EventFeedback[]>('/feedback/', {
            params: { registration: registrationUuid }
        });
        return response.data.length > 0 ? response.data[0] : null;
    } catch {
        return null;
    }
}

/**
 * Submit new feedback for an event registration
 */
export async function createFeedback(data: EventFeedbackCreateRequest): Promise<EventFeedback> {
    const response = await client.post<EventFeedback>('/feedback/', data);
    return response.data;
}

/**
 * Update existing feedback
 */
export async function updateFeedback(
    uuid: string,
    data: EventFeedbackUpdateRequest
): Promise<EventFeedback> {
    const response = await client.patch<EventFeedback>(`/feedback/${uuid}/`, data);
    return response.data;
}

/**
 * Delete feedback
 */
export async function deleteFeedback(uuid: string): Promise<void> {
    await client.delete(`/feedback/${uuid}/`);
}

/**
 * Calculate feedback summary from a list of feedback
 * (Client-side calculation since backend doesn't provide aggregates)
 */
export function calculateFeedbackSummary(feedbackList: EventFeedback[]) {
    if (feedbackList.length === 0) {
        return {
            total_count: 0,
            average_rating: 0,
            average_content_quality: 0,
            average_speaker_rating: 0,
            rating_distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
        };
    }

    const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } as Record<number, number>;
    let totalRating = 0;
    let totalContentQuality = 0;
    let totalSpeaker = 0;

    feedbackList.forEach(fb => {
        totalRating += fb.rating;
        totalContentQuality += fb.content_quality_rating;
        totalSpeaker += fb.speaker_rating;
        distribution[fb.rating] = (distribution[fb.rating] || 0) + 1;
    });

    const count = feedbackList.length;

    return {
        total_count: count,
        average_rating: Math.round((totalRating / count) * 10) / 10,
        average_content_quality: Math.round((totalContentQuality / count) * 10) / 10,
        average_speaker_rating: Math.round((totalSpeaker / count) * 10) / 10,
        rating_distribution: distribution as { 1: number; 2: number; 3: number; 4: number; 5: number }
    };
}
