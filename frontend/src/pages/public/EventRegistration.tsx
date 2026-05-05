import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertCircle, Calendar, CheckCircle, Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Checkbox } from "@/shared/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Separator } from "@/shared/ui/separator";
import { Badge } from "@/shared/ui/badge";
import { getPublicEvent } from "@/api/events";
import { registerForEvent, startRegistrationCheckout } from "@/api/registrations";
import { Event } from "@/api/events/types";
import { RegistrationCreateRequest } from "@/api/registrations/types";
import { useAuth } from "@/features/auth";
import { toast } from "sonner";
import { CustomFieldsForm } from "@/components/registration/CustomFieldInput";
import { splitFullName } from "@/lib/initials";

type Step = "form" | "success";

interface AttendeeForm {
    email: string;
    firstName: string;
    lastName: string;
    professionalTitle: string;
    organizationName: string;
    allowPublicVerification: boolean;
}

const MAX_ATTENDEES = 25;

const emptyAttendee = (): AttendeeForm => ({
    email: "",
    firstName: "",
    lastName: "",
    professionalTitle: "",
    organizationName: "",
    allowPublicVerification: true,
});

export function EventRegistration() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [event, setEvent] = useState<Event | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [step, setStep] = useState<Step>("form");

    // The form starts with one attendee (the buyer when authenticated, a
    // blank row otherwise). "+ Add another attendee" appends rows up to
    // MAX_ATTENDEES; multi-row submissions go through the multi-attendee
    // backend path.
    const [attendees, setAttendees] = useState<AttendeeForm[]>([
        { ...emptyAttendee(), email: user?.email || "" },
    ]);

    const updateAttendee = (idx: number, patch: Partial<AttendeeForm>) =>
        setAttendees((prev) => prev.map((a, i) => (i === idx ? { ...a, ...patch } : a)));
    const addAttendee = () =>
        setAttendees((prev) => (prev.length < MAX_ATTENDEES ? [...prev, emptyAttendee()] : prev));
    const removeAttendee = (idx: number) =>
        setAttendees((prev) => prev.filter((_, i) => i !== idx));

    const [customFieldValues, setCustomFieldValues] = useState<Record<string, any>>({});

    const isPaidEvent = Boolean(event && !event.is_free && event.price && Number(event.price) > 0);

    useEffect(() => {
        async function fetchEvent() {
            if (!id) return;
            try {
                const data = await getPublicEvent(id);
                setEvent(data);
                if (user) {
                    const { first, last } = splitFullName(user.full_name);
                    setAttendees((prev) => {
                        const next = [...prev];
                        next[0] = {
                            ...next[0],
                            email: user.email,
                            firstName: first,
                            lastName: last,
                        };
                        return next;
                    });
                }
            } catch (e) {
                setError("Event not found or registration is closed.");
            } finally {
                setLoading(false);
            }
        }
        fetchEvent();
    }, [id, user]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!event?.uuid) return;

        setSubmitting(true);
        setError(null);

        try {
            // Multi-attendee shape when there's more than one row, OR
            // when a guest is registering even a single attendee — using
            // the unified shape for guests keeps the response branching
            // predictable. Single authenticated attendee still uses the
            // legacy shape for backward compat.
            const useMultiShape = attendees.length > 1 || !user;
            const buyerEmail = attendees[0]?.email || "";

            let payload: RegistrationCreateRequest;
            if (useMultiShape) {
                payload = {
                    attendees: attendees.map((a) => ({
                        email: a.email,
                        full_name: `${a.firstName} ${a.lastName}`.trim(),
                        professional_title: a.professionalTitle || undefined,
                        organization_name: a.organizationName || undefined,
                        allow_public_verification: a.allowPublicVerification,
                    })),
                    custom_field_responses: customFieldValues,
                } as any;
            } else {
                const a = attendees[0];
                payload = {
                    email: a.email,
                    full_name: `${a.firstName} ${a.lastName}`.trim(),
                    professional_title: a.professionalTitle || undefined,
                    organization_name: a.organizationName || undefined,
                    allow_public_verification: a.allowPublicVerification,
                    custom_field_responses: customFieldValues,
                };
            }

            const response = await registerForEvent(event.uuid, payload);

            if (response.requires_payment && response.checkout_url) {
                toast.info("Redirecting to secure checkout…");
                window.location.href = response.checkout_url;
                return;
            }
            // Anonymous free flow: send them to the "check your email" page.
            // For multi-attendee, we surface the buyer's email; each
            // attendee has received their own claim link.
            if (response.anonymous) {
                navigate(
                    `/events/${event.slug || event.uuid}/registration-pending?email=${encodeURIComponent(buyerEmail)}`,
                    { replace: true },
                );
                return;
            }
            if (response.status === "waitlisted") {
                toast.info("You've been added to the waitlist.");
            } else {
                toast.success(
                    attendees.length > 1
                        ? `Registered ${attendees.length} attendees.`
                        : "Registration successful!",
                );
            }
            setStep("success");
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === "EMAIL_HAS_ACCOUNT") {
                setError("EMAIL_HAS_ACCOUNT");
                toast.error("An email in this submission already has an account.");
                return;
            }
            if (code === "DUPLICATE_EMAIL_IN_BATCH") {
                setError(err?.response?.data?.error?.message || "Each attendee must have a distinct email.");
                toast.error("Duplicate attendee email.");
                return;
            }
            const message =
                err?.response?.data?.error?.message || err?.response?.data?.detail || "Registration failed.";
            setError(message);
            toast.error(message);
        } finally {
            setSubmitting(false);
        }
    };

    const handleResumePayment = async (registrationUuid: string) => {
        try {
            const result = await startRegistrationCheckout(registrationUuid);
            window.location.href = result.url;
        } catch (err: any) {
            toast.error(err?.response?.data?.error?.message || "Unable to start checkout.");
        }
    };

    const formatPrice = (price: number | string | undefined, currency = "USD") => {
        if (!price) return "Free";
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: currency.toUpperCase(),
        }).format(Number(price));
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (error && !event) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-foreground">{error}</h2>
                    <Link to="/discover/events">
                        <Button className="mt-4">Browse Events</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const eventEnded = (() => {
        if (!event?.starts_at) return false;
        const end = new Date(event.starts_at).getTime() + (event.duration_minutes ?? 0) * 60_000;
        return end < Date.now();
    })();

    if (event && eventEnded) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Card className="max-w-md w-full mx-4">
                    <CardContent className="pt-6 text-center space-y-4">
                        <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                            <Calendar className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h2 className="text-2xl font-bold text-foreground">This event has ended</h2>
                        <p className="text-muted-foreground">
                            Registration for <strong>{event.title}</strong> is closed.
                            If a recording is published, it will appear on the event page.
                        </p>
                        <div className="space-y-2 pt-2">
                            <Link to={`/events/${event.slug || id}/details`}>
                                <Button className="w-full">View Event Details</Button>
                            </Link>
                            <Link to="/discover/events">
                                <Button variant="outline" className="w-full">
                                    Browse More Events
                                </Button>
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === "success") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Card className="max-w-md w-full mx-4">
                    <CardContent className="pt-6 text-center">
                        <div className="h-16 w-16 bg-success-subtle rounded-full flex items-center justify-center mx-auto mb-4">
                            <CheckCircle className="h-8 w-8 text-success" />
                        </div>
                        <h2 className="text-2xl font-bold text-foreground mb-2">You're Registered!</h2>
                        <p className="text-muted-foreground mb-6">
                            Check your email for confirmation details and event information.
                        </p>
                        <div className="space-y-3">
                            <Link to={`/events/${event?.slug || id}/details`}>
                                <Button className="w-full">View Event Details</Button>
                            </Link>
                            <Link to="/discover/events">
                                <Button variant="outline" className="w-full">
                                    Browse More Events
                                </Button>
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background py-10">
            <div className="max-w-3xl mx-auto px-4">
                <div className="mb-8">
                    <Badge variant="outline" className="mb-3">
                        Registration
                    </Badge>
                    <h1 className="text-3xl font-semibold text-foreground">{event?.title}</h1>
                    {event?.starts_at && (
                        <p className="text-muted-foreground mt-2 flex items-center gap-2">
                            <Calendar className="h-4 w-4" />
                            {new Date(event.starts_at).toLocaleString()}
                        </p>
                    )}
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>Attendee details</CardTitle>
                        <CardDescription>
                            {isPaidEvent
                                ? `After you submit we'll take you to secure checkout (${formatPrice(
                                      Number(event?.price || 0) * attendees.length,
                                      event?.currency || "USD",
                                  )}${attendees.length > 1 ? ` for ${attendees.length} attendees` : ""}). Promo codes are entered there.`
                                : "Fill in your details to complete free registration."}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {attendees.map((attendee, idx) => {
                                const isFirst = idx === 0;
                                const idPrefix = `att-${idx}`;
                                const emailDisabled = isFirst && Boolean(user);
                                return (
                                    <div key={idx} className="space-y-3 rounded-md border p-4">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-sm font-semibold">
                                                {attendees.length > 1
                                                    ? `Attendee ${idx + 1}`
                                                    : "Your details"}
                                            </h3>
                                            {!isFirst && (
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeAttendee(idx)}
                                                    aria-label={`Remove attendee ${idx + 1}`}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <Label htmlFor={`${idPrefix}-firstName`}>First name</Label>
                                                <Input
                                                    id={`${idPrefix}-firstName`}
                                                    required
                                                    value={attendee.firstName}
                                                    onChange={(e) => updateAttendee(idx, { firstName: e.target.value })}
                                                />
                                            </div>
                                            <div>
                                                <Label htmlFor={`${idPrefix}-lastName`}>Last name</Label>
                                                <Input
                                                    id={`${idPrefix}-lastName`}
                                                    required
                                                    value={attendee.lastName}
                                                    onChange={(e) => updateAttendee(idx, { lastName: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <Label htmlFor={`${idPrefix}-email`}>Email</Label>
                                            <Input
                                                id={`${idPrefix}-email`}
                                                type="email"
                                                required
                                                value={attendee.email}
                                                onChange={(e) => updateAttendee(idx, { email: e.target.value })}
                                                disabled={emailDisabled}
                                            />
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <Label htmlFor={`${idPrefix}-title`}>Professional title</Label>
                                                <Input
                                                    id={`${idPrefix}-title`}
                                                    value={attendee.professionalTitle}
                                                    onChange={(e) => updateAttendee(idx, { professionalTitle: e.target.value })}
                                                    placeholder="MD, PhD, etc."
                                                />
                                            </div>
                                            <div>
                                                <Label htmlFor={`${idPrefix}-org`}>Organization</Label>
                                                <Input
                                                    id={`${idPrefix}-org`}
                                                    value={attendee.organizationName}
                                                    onChange={(e) => updateAttendee(idx, { organizationName: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-2">
                                            <Checkbox
                                                id={`${idPrefix}-verify`}
                                                checked={attendee.allowPublicVerification}
                                                onCheckedChange={(checked) =>
                                                    updateAttendee(idx, { allowPublicVerification: Boolean(checked) })
                                                }
                                            />
                                            <div className="text-sm">
                                                <Label htmlFor={`${idPrefix}-verify`} className="cursor-pointer">
                                                    Allow public certificate verification
                                                </Label>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}

                            {attendees.length < MAX_ATTENDEES && (
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={addAttendee}
                                >
                                    <Plus className="h-4 w-4 mr-1" />
                                    Add another attendee
                                </Button>
                            )}

                            {event?.custom_fields?.length ? (
                                <>
                                    <Separator className="my-4" />
                                    <CustomFieldsForm
                                        fields={event.custom_fields}
                                        values={customFieldValues}
                                        onChange={setCustomFieldValues}
                                    />
                                </>
                            ) : null}

                            {error === "EMAIL_HAS_ACCOUNT" ? (
                                <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm">
                                    <div className="flex items-start gap-2 text-amber-900">
                                        <AlertCircle className="h-4 w-4 mt-0.5" />
                                        <div className="space-y-2">
                                            <p>
                                                An account already exists for one of the emails in this submission.
                                                Sign in to register, or use a different email.
                                            </p>
                                            <Button asChild size="sm" variant="outline">
                                                <Link
                                                    to={`/login?email=${encodeURIComponent(attendees[0]?.email || '')}&returnUrl=${encodeURIComponent(window.location.pathname + window.location.search)}`}
                                                >
                                                    Sign in to continue
                                                </Link>
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ) : error ? (
                                <div className="flex items-start gap-2 text-sm text-destructive">
                                    <AlertCircle className="h-4 w-4 mt-0.5" />
                                    <span>{error}</span>
                                </div>
                            ) : null}

                            <div className="flex items-center justify-end gap-3 pt-2">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => navigate(`/events/${event?.slug || id}/details`)}
                                >
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting}>
                                    {submitting ? (
                                        <>
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            {isPaidEvent ? "Starting checkout…" : "Registering…"}
                                        </>
                                    ) : isPaidEvent ? (
                                        `Continue to checkout — ${formatPrice(
                                            Number(event?.price || 0) * attendees.length,
                                            event?.currency || "USD",
                                        )}`
                                    ) : attendees.length > 1 ? (
                                        `Register ${attendees.length} attendees`
                                    ) : (
                                        "Register"
                                    )}
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

export default EventRegistration;
