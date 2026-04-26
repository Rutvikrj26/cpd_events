import { useCallback, useEffect, useReducer, useRef } from 'react';

type State<T, E = unknown> =
    | { status: 'idle'; data: undefined; error: undefined }
    | { status: 'pending'; data: undefined; error: undefined }
    | { status: 'success'; data: T; error: undefined }
    | { status: 'error'; data: undefined; error: E };

type Action<T, E> =
    | { type: 'pending' }
    | { type: 'success'; data: T }
    | { type: 'error'; error: E }
    | { type: 'reset' };

function reducer<T, E>(state: State<T, E>, action: Action<T, E>): State<T, E> {
    switch (action.type) {
        case 'pending':
            return { status: 'pending', data: undefined, error: undefined };
        case 'success':
            return { status: 'success', data: action.data, error: undefined };
        case 'error':
            return { status: 'error', data: undefined, error: action.error };
        case 'reset':
            return { status: 'idle', data: undefined, error: undefined };
        default:
            return state;
    }
}

export interface UseAsyncResult<T, E, Args extends unknown[]> {
    status: State<T, E>['status'];
    data: T | undefined;
    error: E | undefined;
    isIdle: boolean;
    isLoading: boolean;
    isSuccess: boolean;
    isError: boolean;
    /** Trigger the async function; previous in-flight calls are cancelled (their result is ignored). */
    run: (...args: Args) => Promise<T | undefined>;
    /** Reset to idle state. */
    reset: () => void;
}

/**
 * useAsync — minimal generic async runner for one-off imperative calls
 * outside React Query (e.g. file uploads, form submissions in legacy code).
 *
 * **Prefer React Query** for reads and most mutations. This hook exists so
 * raw `useState + useEffect + try/catch` doesn't get reinvented per-component.
 *
 * Usage:
 *     const upload = useAsync(uploadAvatar);
 *     <button onClick={() => upload.run(file)} disabled={upload.isLoading}>
 *         {upload.isLoading ? 'Uploading…' : 'Upload'}
 *     </button>
 *     {upload.isError && <Error message={upload.error.message} />}
 */
export function useAsync<T, E = Error, Args extends unknown[] = []>(
    fn: (...args: Args) => Promise<T>
): UseAsyncResult<T, E, Args> {
    const [state, dispatch] = useReducer(reducer<T, E>, {
        status: 'idle',
        data: undefined,
        error: undefined,
    } as State<T, E>);

    const callIdRef = useRef(0);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    const run = useCallback(
        async (...args: Args) => {
            const callId = ++callIdRef.current;
            dispatch({ type: 'pending' });
            try {
                const data = await fn(...args);
                if (callId === callIdRef.current && mountedRef.current) {
                    dispatch({ type: 'success', data });
                }
                return data;
            } catch (error) {
                if (callId === callIdRef.current && mountedRef.current) {
                    dispatch({ type: 'error', error: error as E });
                }
                return undefined;
            }
        },
        [fn]
    );

    const reset = useCallback(() => dispatch({ type: 'reset' }), []);

    return {
        status: state.status,
        data: state.data,
        error: state.error,
        isIdle: state.status === 'idle',
        isLoading: state.status === 'pending',
        isSuccess: state.status === 'success',
        isError: state.status === 'error',
        run,
        reset,
    };
}
