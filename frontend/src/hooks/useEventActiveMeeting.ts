import { useQuery } from '@tanstack/react-query';
import { getEventActiveMeeting } from '@/api/video';
import type { ActiveMeetingResponse, ActiveMeetingStatus } from '@/api/video/types';

/**
 * Polls `/meetings/active/` for an event every 10s and returns the
 * canonical lifecycle status.
 *
 * Used by both the event lobby (large CTA) and the management header
 * (compact pill) so the two surfaces never disagree about whether a
 * meeting is live. Without a shared poll, the header's stale
 * "Join as host" pill would 409 the moment the host leaves and
 * the room transitions to ENDED — which is exactly the bug we're
 * fixing.
 */
export interface UseActiveMeetingResult {
  status: ActiveMeetingStatus;
  data: ActiveMeetingResponse | undefined;
  isLoading: boolean;
}

export function useEventActiveMeeting(
  eventUuid: string | undefined,
  options: { enabled?: boolean } = {},
): UseActiveMeetingResult {
  const enabled = (options.enabled ?? true) && !!eventUuid;
  const query = useQuery({
    queryKey: ['meeting-active', eventUuid ?? 'noop'],
    queryFn: () => getEventActiveMeeting(eventUuid!),
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
    enabled,
  });
  return {
    status: query.data?.status ?? 'none',
    data: query.data,
    isLoading: query.isLoading,
  };
}
