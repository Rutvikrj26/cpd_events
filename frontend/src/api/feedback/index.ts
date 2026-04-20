import client from '../client';
import {
    EventFeedback,
    EventFeedbackCreateRequest,
    EventFeedbackUpdateRequest,
    FeedbackField,
    FeedbackFieldInput,
    FeedbackSummary,
} from './types';

export async function getFeedback(): Promise<EventFeedback[]> {
    const response = await client.get<any>('/feedback/');
    return Array.isArray(response.data) ? response.data : response.data.results || [];
}

export async function getEventFeedback(eventUuid: string): Promise<EventFeedback[]> {
    const response = await client.get<any>('/feedback/', {
        params: { event: eventUuid },
    });
    return Array.isArray(response.data) ? response.data : response.data.results || [];
}

export async function getFeedbackById(uuid: string): Promise<EventFeedback> {
    const response = await client.get<EventFeedback>(`/feedback/${uuid}/`);
    return response.data;
}

export async function getRegistrationFeedback(
    registrationUuid: string,
): Promise<EventFeedback | null> {
    try {
        const response = await client.get<any>('/feedback/', {
            params: { registration: registrationUuid },
        });
        const results = Array.isArray(response.data) ? response.data : response.data.results || [];
        return results.length > 0 ? results[0] : null;
    } catch {
        return null;
    }
}

export async function createFeedback(data: EventFeedbackCreateRequest): Promise<EventFeedback> {
    const response = await client.post<EventFeedback>('/feedback/', data);
    return response.data;
}

export async function updateFeedback(
    uuid: string,
    data: EventFeedbackUpdateRequest,
): Promise<EventFeedback> {
    const response = await client.patch<EventFeedback>(`/feedback/${uuid}/`, data);
    return response.data;
}

export async function deleteFeedback(uuid: string): Promise<void> {
    await client.delete(`/feedback/${uuid}/`);
}

// --- Feedback form schema CRUD (organizer-only) ---------------------------

export async function getFeedbackFields(eventUuid: string): Promise<FeedbackField[]> {
    const response = await client.get(`/events/${eventUuid}/feedback-fields/`);
    const data = response.data as any;
    const list: FeedbackField[] = Array.isArray(data) ? data : data.results || [];
    return list.sort((a, b) => a.order - b.order);
}

export async function createFeedbackField(
    eventUuid: string,
    data: FeedbackFieldInput,
): Promise<FeedbackField> {
    const response = await client.post<FeedbackField>(
        `/events/${eventUuid}/feedback-fields/`,
        data,
    );
    return response.data;
}

export async function updateFeedbackField(
    eventUuid: string,
    fieldUuid: string,
    data: Partial<FeedbackFieldInput>,
): Promise<FeedbackField> {
    const response = await client.patch<FeedbackField>(
        `/events/${eventUuid}/feedback-fields/${fieldUuid}/`,
        data,
    );
    return response.data;
}

export async function deleteFeedbackField(
    eventUuid: string,
    fieldUuid: string,
): Promise<void> {
    await client.delete(`/events/${eventUuid}/feedback-fields/${fieldUuid}/`);
}

export async function reorderFeedbackFields(
    eventUuid: string,
    orderedUuids: string[],
): Promise<void> {
    await client.post(`/events/${eventUuid}/feedback-fields/reorder/`, {
        order: orderedUuids,
    });
}

// --- Client-side aggregates over dynamic responses ------------------------

function asNumber(value: unknown): number | null {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

export function calculateFeedbackSummary(
    feedbackList: EventFeedback[],
    fields?: FeedbackField[],
): FeedbackSummary {
    const total = feedbackList.length;
    if (total === 0) {
        return { total_count: 0, per_field: [] };
    }

    const fieldMap = new Map<string, { field_label: string; field_type: any; order: number }>();
    if (fields) {
        for (const f of fields) {
            fieldMap.set(f.uuid, {
                field_label: f.label,
                field_type: f.field_type,
                order: f.order,
            });
        }
    }
    for (const fb of feedbackList) {
        for (const r of fb.field_responses || []) {
            if (!fieldMap.has(r.field_uuid)) {
                fieldMap.set(r.field_uuid, {
                    field_label: r.field_label,
                    field_type: r.field_type,
                    order: r.field_order,
                });
            }
        }
    }

    const per_field = Array.from(fieldMap.entries())
        .map(([field_uuid, meta]) => {
            const values = feedbackList
                .flatMap((fb) => fb.field_responses || [])
                .filter((r) => r.field_uuid === field_uuid);

            if (meta.field_type === 'rating' || meta.field_type === 'number') {
                const numeric = values
                    .map((v) => asNumber(v.value))
                    .filter((n): n is number => n !== null);
                const distribution: Record<string, number> = {};
                for (const n of numeric) {
                    const key = String(n);
                    distribution[key] = (distribution[key] || 0) + 1;
                }
                const avg =
                    numeric.length > 0
                        ? Math.round((numeric.reduce((a, b) => a + b, 0) / numeric.length) * 10) / 10
                        : undefined;
                return {
                    field_uuid,
                    field_label: meta.field_label,
                    field_type: meta.field_type,
                    average: avg,
                    distribution,
                    responses: numeric.length,
                    _order: meta.order,
                };
            }

            return {
                field_uuid,
                field_label: meta.field_label,
                field_type: meta.field_type,
                responses: values.filter((v) => v.value !== null && v.value !== '').length,
                _order: meta.order,
            };
        })
        .sort((a, b) => a._order - b._order)
        .map(({ _order, ...rest }) => rest);

    return { total_count: total, per_field };
}
