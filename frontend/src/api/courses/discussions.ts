import client from '../client';
import {
    DiscussionFlag,
    DiscussionReply,
    DiscussionThread,
    DiscussionThreadList,
    CourseMemberMini,
    FlagReason,
    FlagResolveAction,
} from './types';

const base = (courseUuid: string) => `/courses/${courseUuid}/discussions`;

const unwrap = <T,>(data: any): T[] =>
    Array.isArray(data) ? data : (data?.results ?? []);

// ============================================
// Threads
// ============================================

export const listThreads = async (
    courseUuid: string,
    params?: { page?: number; page_size?: number }
): Promise<DiscussionThreadList[]> => {
    const response = await client.get<any>(`${base(courseUuid)}/`, { params });
    return unwrap<DiscussionThreadList>(response.data);
};

export const createThread = async (
    courseUuid: string,
    data: { title: string; body_html: string }
): Promise<DiscussionThread> => {
    const response = await client.post<DiscussionThread>(`${base(courseUuid)}/`, data);
    return response.data;
};

export const getThread = async (
    courseUuid: string,
    threadUuid: string
): Promise<DiscussionThread> => {
    const response = await client.get<DiscussionThread>(`${base(courseUuid)}/${threadUuid}/`);
    return response.data;
};

export const updateThread = async (
    courseUuid: string,
    threadUuid: string,
    data: Partial<{ title: string; body_html: string }>
): Promise<DiscussionThread> => {
    const response = await client.patch<DiscussionThread>(
        `${base(courseUuid)}/${threadUuid}/`,
        data
    );
    return response.data;
};

export const deleteThread = async (courseUuid: string, threadUuid: string): Promise<void> => {
    await client.delete(`${base(courseUuid)}/${threadUuid}/`);
};

// Moderation actions ==========================

const threadAction = (verb: string) => async (
    courseUuid: string,
    threadUuid: string
): Promise<DiscussionThread> => {
    const response = await client.post<DiscussionThread>(
        `${base(courseUuid)}/${threadUuid}/${verb}/`
    );
    return response.data;
};

export const pinThread = threadAction('pin');
export const unpinThread = threadAction('unpin');
export const lockThread = threadAction('lock');
export const unlockThread = threadAction('unlock');
export const hideThread = threadAction('hide');
export const unhideThread = threadAction('unhide');

// Flagging ====================================

export const flagThread = async (
    courseUuid: string,
    threadUuid: string,
    data: { reason: FlagReason; note?: string }
): Promise<DiscussionFlag> => {
    const response = await client.post<DiscussionFlag>(
        `${base(courseUuid)}/${threadUuid}/flag/`,
        data
    );
    return response.data;
};

// ============================================
// Replies
// ============================================

export const listReplies = async (
    courseUuid: string,
    threadUuid: string
): Promise<DiscussionReply[]> => {
    const response = await client.get<any>(
        `${base(courseUuid)}/${threadUuid}/replies/`
    );
    return unwrap<DiscussionReply>(response.data);
};

export const createReply = async (
    courseUuid: string,
    threadUuid: string,
    data: { body_html: string }
): Promise<DiscussionReply> => {
    const response = await client.post<DiscussionReply>(
        `${base(courseUuid)}/${threadUuid}/replies/`,
        data
    );
    return response.data;
};

export const deleteReply = async (
    courseUuid: string,
    threadUuid: string,
    replyUuid: string
): Promise<void> => {
    await client.delete(`${base(courseUuid)}/${threadUuid}/replies/${replyUuid}/`);
};

const replyAction = (verb: string) => async (
    courseUuid: string,
    threadUuid: string,
    replyUuid: string
): Promise<DiscussionReply> => {
    const response = await client.post<DiscussionReply>(
        `${base(courseUuid)}/${threadUuid}/replies/${replyUuid}/${verb}/`
    );
    return response.data;
};

export const hideReply = replyAction('hide');
export const unhideReply = replyAction('unhide');

export const flagReply = async (
    courseUuid: string,
    threadUuid: string,
    replyUuid: string,
    data: { reason: FlagReason; note?: string }
): Promise<DiscussionFlag> => {
    const response = await client.post<DiscussionFlag>(
        `${base(courseUuid)}/${threadUuid}/replies/${replyUuid}/flag/`,
        data
    );
    return response.data;
};

// ============================================
// Flag queue (staff)
// ============================================

export const listOpenFlags = async (
    courseUuid: string,
    params?: { status?: 'open' | 'resolved_kept' | 'resolved_hidden' }
): Promise<DiscussionFlag[]> => {
    const response = await client.get<any>(`${base(courseUuid)}/flags/`, { params });
    return unwrap<DiscussionFlag>(response.data);
};

export const resolveFlag = async (
    courseUuid: string,
    flagUuid: string,
    action: FlagResolveAction
): Promise<DiscussionFlag> => {
    const response = await client.post<DiscussionFlag>(
        `${base(courseUuid)}/flags/${flagUuid}/resolve/`,
        { action }
    );
    return response.data;
};

// ============================================
// Course member search (mentions)
// ============================================

export const searchCourseMembers = async (
    courseUuid: string,
    q: string
): Promise<CourseMemberMini[]> => {
    const response = await client.get<any>(`/courses/${courseUuid}/members/search/`, {
        params: { q },
    });
    return Array.isArray(response.data) ? response.data : response.data?.results ?? [];
};
