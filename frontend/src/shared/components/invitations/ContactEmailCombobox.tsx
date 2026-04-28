/**
 * ContactEmailCombobox — multi-select picker for the InviteLearnerDialog.
 *
 * Behavior:
 *   - Type to search → debounced GET /api/v1/contacts/?search= → render
 *     matching contacts in a popover dropdown.
 *   - If the typed value parses as a valid email AND no contact matches,
 *     surface an "Add as new invitee" row at the top of the list.
 *   - Paste-many: when the user pastes a string containing `,`, `;`, or
 *     newlines, split + dedupe + validate + bulk-add. Invalid tokens
 *     become red chips with an X tooltip explaining why.
 *   - Each selection (contact OR free-form) becomes a chip with remove.
 *   - Output (`onChange`) is `Array<InviteeInput>` ready to ship to
 *     `POST /events/{uuid}/invite/`.
 *
 * Built on shadcn primitives we already have (`Popover`, `Input`); no
 * cmdk dependency. Filtering is server-side via the Contacts search API.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, ClipboardEvent, KeyboardEvent } from 'react';
import { Mail, Plus, User, X } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Input } from '@/shared/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover';
import { getContacts } from '@/api/contacts';
import type { Contact } from '@/api/contacts';
import type { InviteeInput } from '@/api/invitations/types';

/**
 * Chip narrows `InviteeInput.email` to required — once a chip exists in
 * the picker we always know its email, even for free-form entries.
 * (`InviteeInput.email` is optional only because the backend payload
 * accepts contact_uuid OR email; the picker constructs both from email.)
 */
export interface Chip extends Omit<InviteeInput, 'email'> {
    email: string;
    /** Stable id for keyed rendering. */
    id: string;
    /** Set when the email failed validation, surfaces in red. */
    invalid?: boolean;
}

export interface ContactEmailComboboxProps {
    value: Chip[];
    onChange: (value: Chip[]) => void;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SEARCH_DEBOUNCE_MS = 200;

function chipFromContact(c: Contact): Chip {
    return {
        id: `contact:${c.uuid}`,
        contact_uuid: c.uuid,
        email: c.email,
        full_name: c.full_name,
    };
}

function chipFromEmail(email: string, fullName?: string): Chip {
    const lc = email.trim().toLowerCase();
    return {
        id: `email:${lc}`,
        email: lc,
        full_name: fullName,
        invalid: !EMAIL_RE.test(lc),
    };
}

function dedupeAppend(existing: Chip[], incoming: Chip[]): Chip[] {
    const seenEmails = new Set(existing.map(c => c.email.toLowerCase()));
    const out = [...existing];
    for (const c of incoming) {
        if (seenEmails.has(c.email.toLowerCase())) continue;
        seenEmails.add(c.email.toLowerCase());
        out.push(c);
    }
    return out;
}

export function ContactEmailCombobox({
    value,
    onChange,
    placeholder = 'Search contacts or type an email…',
    disabled,
    className,
}: ContactEmailComboboxProps) {
    const [query, setQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [open, setOpen] = useState(false);
    const [results, setResults] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    /* Debounce search */
    useEffect(() => {
        const id = window.setTimeout(() => setDebouncedQuery(query.trim()), SEARCH_DEBOUNCE_MS);
        return () => window.clearTimeout(id);
    }, [query]);

    /* Fetch matching contacts */
    useEffect(() => {
        if (!debouncedQuery) {
            setResults([]);
            return;
        }
        let cancelled = false;
        setLoading(true);
        getContacts({ search: debouncedQuery, page_size: '10' })
            .then((res) => {
                if (cancelled) return;
                const list = Array.isArray(res) ? res : (res.results || []);
                setResults(list as Contact[]);
            })
            .catch(() => !cancelled && setResults([]))
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [debouncedQuery]);

    /* Already-selected emails (case-insensitive) — used to grey-out
       results that are already chips and to short-circuit duplicate-add. */
    const selectedEmails = useMemo(
        () => new Set(value.map((c) => c.email.toLowerCase())),
        [value],
    );

    const selectContact = (c: Contact) => {
        if (selectedEmails.has(c.email.toLowerCase())) return;
        onChange(dedupeAppend(value, [chipFromContact(c)]));
        setQuery('');
        setDebouncedQuery('');
        inputRef.current?.focus();
    };

    const addEmail = (raw: string) => {
        const trimmed = raw.trim();
        if (!trimmed) return;
        // If a contact already matches, prefer that (richer chip).
        const match = results.find((r) => r.email.toLowerCase() === trimmed.toLowerCase());
        if (match) {
            selectContact(match);
            return;
        }
        if (selectedEmails.has(trimmed.toLowerCase())) return;
        onChange(dedupeAppend(value, [chipFromEmail(trimmed)]));
        setQuery('');
        setDebouncedQuery('');
    };

    const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
        const text = e.clipboardData.getData('text');
        if (!/[,;\n]/.test(text)) return;  // single token — let normal input handle it
        e.preventDefault();
        const tokens = text
            .split(/[,;\n]/)
            .map((t) => t.trim())
            .filter(Boolean);
        const newChips = tokens.map((t) => chipFromEmail(t));
        onChange(dedupeAppend(value, newChips));
        setQuery('');
        setDebouncedQuery('');
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if ((e.key === 'Enter' || e.key === ',') && query.trim()) {
            e.preventDefault();
            addEmail(query);
        } else if (e.key === 'Backspace' && !query && value.length > 0) {
            // Remove the trailing chip on backspace-into-empty.
            onChange(value.slice(0, -1));
        }
    };

    const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
        const v = e.target.value;
        setQuery(v);
        if (!open) setOpen(true);
    };

    const removeChip = (id: string) => {
        onChange(value.filter((c) => c.id !== id));
    };

    /* The "Add as new invitee" row appears when:
       - input parses as a valid email
       - no current contact result already has this email
       - no chip already exists for this email */
    const showAddNewRow = useMemo(() => {
        const lc = debouncedQuery.toLowerCase();
        if (!EMAIL_RE.test(lc)) return false;
        if (selectedEmails.has(lc)) return false;
        if (results.some((r) => r.email.toLowerCase() === lc)) return false;
        return true;
    }, [debouncedQuery, results, selectedEmails]);

    return (
        <div className={cn('w-full', className)}>
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <div
                        className={cn(
                            'flex min-h-10 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5 text-sm ring-offset-background',
                            'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
                            disabled && 'cursor-not-allowed opacity-50',
                        )}
                        onClick={() => inputRef.current?.focus()}
                    >
                        {value.map((chip) => (
                            <span
                                key={chip.id}
                                className={cn(
                                    'inline-flex max-w-[240px] items-center gap-1 rounded-full px-2 py-0.5 text-xs',
                                    chip.invalid
                                        ? 'bg-destructive/10 text-destructive'
                                        : chip.contact_uuid
                                          ? 'bg-primary/10 text-primary'
                                          : 'bg-muted text-foreground',
                                )}
                                title={chip.invalid ? 'Not a valid email address' : chip.email}
                            >
                                {chip.invalid ? (
                                    <X className="h-3 w-3" />
                                ) : chip.contact_uuid ? (
                                    <User className="h-3 w-3 shrink-0" />
                                ) : (
                                    <Mail className="h-3 w-3 shrink-0" />
                                )}
                                <span className="truncate">{chip.full_name || chip.email}</span>
                                <button
                                    type="button"
                                    aria-label={`Remove ${chip.email}`}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        removeChip(chip.id);
                                    }}
                                    className="-mr-0.5 rounded p-0.5 hover:bg-foreground/10"
                                >
                                    <X className="h-3 w-3" />
                                </button>
                            </span>
                        ))}
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={handleChange}
                            onPaste={handlePaste}
                            onKeyDown={handleKeyDown}
                            onFocus={() => setOpen(true)}
                            placeholder={value.length === 0 ? placeholder : ''}
                            disabled={disabled}
                            className="min-w-[120px] flex-1 bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-muted-foreground"
                            aria-label="Add invitees"
                        />
                    </div>
                </PopoverTrigger>
                <PopoverContent
                    className="w-[var(--radix-popover-trigger-width)] p-1"
                    align="start"
                    sideOffset={4}
                    onOpenAutoFocus={(e) => e.preventDefault()}
                >
                    {!debouncedQuery && results.length === 0 && (
                        <div className="px-3 py-3 text-sm text-muted-foreground">
                            Start typing to search your contacts, or paste comma-separated emails.
                        </div>
                    )}
                    {loading && debouncedQuery && (
                        <div className="px-3 py-2 text-xs text-muted-foreground">Searching…</div>
                    )}
                    {showAddNewRow && (
                        <button
                            type="button"
                            onClick={() => addEmail(debouncedQuery)}
                            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent"
                        >
                            <Plus className="h-4 w-4 text-muted-foreground" />
                            <span>
                                Invite{' '}
                                <span className="font-medium">{debouncedQuery}</span>{' '}
                                <span className="text-xs text-muted-foreground">(new)</span>
                            </span>
                        </button>
                    )}
                    {results.map((c) => {
                        const already = selectedEmails.has(c.email.toLowerCase());
                        return (
                            <button
                                key={c.uuid}
                                type="button"
                                disabled={already}
                                onClick={() => selectContact(c)}
                                className={cn(
                                    'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm',
                                    already
                                        ? 'cursor-not-allowed opacity-50'
                                        : 'hover:bg-accent',
                                )}
                            >
                                <User className="h-4 w-4 text-muted-foreground" />
                                <div className="min-w-0 flex-1">
                                    <div className="truncate text-sm">{c.full_name || c.email}</div>
                                    <div className="truncate text-xs text-muted-foreground">{c.email}</div>
                                </div>
                                {already && <span className="text-xs text-muted-foreground">added</span>}
                            </button>
                        );
                    })}
                    {!loading && debouncedQuery && results.length === 0 && !showAddNewRow && (
                        <div className="px-3 py-2 text-xs text-muted-foreground">
                            No matching contacts. Type a valid email to add as a new invitee.
                        </div>
                    )}
                </PopoverContent>
            </Popover>
            {value.some((c) => c.invalid) && (
                <p className="mt-1 text-xs text-destructive">
                    One or more entries aren't valid email addresses. Remove them to proceed.
                </p>
            )}
        </div>
    );
}
