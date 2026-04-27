/**
 * Hooks for the EventManagement surface.
 *
 * Covers: attendee list, event feedback, check-in mutation,
 * cancel/refund registration, and certificate operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getEventRegistrations,
    checkInAttendee,
    cancelEventRegistration,
    publishEvent,
    unpublishEvent,
    deleteEvent,
} from '@/api/events';
import { refundPurchase } from '@/api/billing';
import { getEventFeedback } from '@/api/feedback';
import {
    issueCertificates,
    revokeCertificate,
    reissueCertificate,
} from '@/api/certificates';
import { eventKeys } from './queryKeys';

// ---------------------------------------------------------------------------
// Attendees
// ---------------------------------------------------------------------------

export function useEventAttendees(eventUuid: string | undefined) {
    return useQuery({
        queryKey: eventUuid ? eventKeys.attendees(eventUuid) : ['events', 'attendees', 'noop'],
        queryFn: () => getEventRegistrations(eventUuid!),
        enabled: Boolean(eventUuid),
        staleTime: 1000 * 30,
    });
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export function useEventFeedbackList(eventUuid: string | undefined) {
    return useQuery({
        queryKey: eventUuid ? eventKeys.feedback(eventUuid) : ['events', 'feedback', 'noop'],
        queryFn: () => getEventFeedback(eventUuid!),
        enabled: Boolean(eventUuid),
        staleTime: 1000 * 60,
    });
}

// ---------------------------------------------------------------------------
// Check-in mutation
// ---------------------------------------------------------------------------

export function useCheckInAttendee(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            registrationUuid,
            attended,
        }: {
            registrationUuid: string;
            attended: boolean;
        }) => checkInAttendee(eventUuid!, registrationUuid, attended),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Cancel / Refund
// ---------------------------------------------------------------------------

export function useCancelRegistration(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            registrationUuid,
            reason,
        }: {
            registrationUuid: string;
            reason?: string;
        }) => cancelEventRegistration(eventUuid!, registrationUuid, reason),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}

export function useRefundRegistration(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            purchaseUuid,
            reason,
        }: {
            // Use the purchase uuid from the registration row — see
            // serializers.RegistrationDetailSerializer for the field. The
            // unified refund endpoint cascades to Registration cancel +
            // payment_status=REFUNDED on a full refund.
            purchaseUuid: string;
            reason: string;
        }) => refundPurchase(purchaseUuid, { reason }),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Publish / Unpublish
// ---------------------------------------------------------------------------

export function usePublishEvent(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: () => publishEvent(eventUuid!),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.detail(eventUuid) });
            }
        },
    });
}

export function useUnpublishEvent(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: () => unpublishEvent(eventUuid!),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.detail(eventUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

export function useDeleteEventMutation(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: () => deleteEvent(eventUuid!),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: eventKeys.all });
        },
    });
}

// ---------------------------------------------------------------------------
// Certificates
// ---------------------------------------------------------------------------

export function useIssueCertificates(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: { registration_uuids?: string[]; issue_all_eligible?: boolean }) =>
            issueCertificates(eventUuid!, payload),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}

export function useRevokeCertificate(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            certificateUuid,
            reason,
        }: {
            certificateUuid: string;
            reason?: string;
        }) => revokeCertificate(eventUuid!, certificateUuid, reason ?? ''),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}

export function useReissueCertificate(eventUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ registrationUuid }: { registrationUuid: string }) =>
            reissueCertificate(eventUuid!, registrationUuid),
        onSuccess: () => {
            if (eventUuid) {
                qc.invalidateQueries({ queryKey: eventKeys.attendees(eventUuid) });
            }
        },
    });
}
