import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertCircle, Calendar, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { getPublicEvent } from "@/api/events";
import { registerForEvent, startRegistrationCheckout } from "@/api/registrations";
import { Event } from "@/api/events/types";
import { RegistrationCreateRequest } from "@/api/registrations/types";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { CustomFieldsForm } from "@/components/registration/CustomFieldInput";
import { splitFullName } from "@/lib/initials";

type Step = "form" | "success";

export function EventRegistration() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [event, setEvent] = useState<Event | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [step, setStep] = useState<Step>("form");

    const [formData, setFormData] = useState({
        email: user?.email || "",
        firstName: "",
        lastName: "",
        professionalTitle: "",
        organizationName: "",
        allowPublicVerification: true,
    });

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
                    setFormData((prev) => ({
                        ...prev,
                        email: user.email,
                        firstName: first,
                        lastName: last,
                    }));
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
            const payload: RegistrationCreateRequest = {
                email: formData.email,
                full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                professional_title: formData.professionalTitle || undefined,
                organization_name: formData.organizationName || undefined,
                allow_public_verification: formData.allowPublicVerification,
                custom_field_responses: customFieldValues,
            };
            const response = await registerForEvent(event.uuid, payload);

            if (response.requires_payment && response.checkout_url) {
                toast.info("Redirecting to secure checkout…");
                window.location.href = response.checkout_url;
                return;
            }
            if (response.status === "waitlisted") {
                toast.info("You've been added to the waitlist.");
            } else {
                toast.success("Registration successful!");
            }
            setStep("success");
        } catch (err: any) {
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
                                ? `After you submit we'll take you to secure checkout (${formatPrice(event?.price, event?.currency || "USD")}). Promo codes are entered there.`
                                : "Fill in your details to complete free registration."}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="firstName">First name</Label>
                                    <Input
                                        id="firstName"
                                        required
                                        value={formData.firstName}
                                        onChange={(e) =>
                                            setFormData((p) => ({ ...p, firstName: e.target.value }))
                                        }
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="lastName">Last name</Label>
                                    <Input
                                        id="lastName"
                                        required
                                        value={formData.lastName}
                                        onChange={(e) =>
                                            setFormData((p) => ({ ...p, lastName: e.target.value }))
                                        }
                                    />
                                </div>
                            </div>
                            <div>
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    required
                                    value={formData.email}
                                    onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                                    disabled={Boolean(user)}
                                />
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="professionalTitle">Professional title</Label>
                                    <Input
                                        id="professionalTitle"
                                        value={formData.professionalTitle}
                                        onChange={(e) =>
                                            setFormData((p) => ({ ...p, professionalTitle: e.target.value }))
                                        }
                                        placeholder="MD, PhD, etc."
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="organizationName">Organization</Label>
                                    <Input
                                        id="organizationName"
                                        value={formData.organizationName}
                                        onChange={(e) =>
                                            setFormData((p) => ({ ...p, organizationName: e.target.value }))
                                        }
                                    />
                                </div>
                            </div>

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

                            <Separator className="my-4" />
                            <div className="flex items-start gap-2">
                                <Checkbox
                                    id="verify"
                                    checked={formData.allowPublicVerification}
                                    onCheckedChange={(checked) =>
                                        setFormData((p) => ({
                                            ...p,
                                            allowPublicVerification: Boolean(checked),
                                        }))
                                    }
                                />
                                <div className="text-sm">
                                    <Label htmlFor="verify" className="cursor-pointer">
                                        Allow public certificate verification
                                    </Label>
                                    <p className="text-muted-foreground">
                                        Your certificate can be looked up by its public code.
                                    </p>
                                </div>
                            </div>

                            {error && (
                                <div className="flex items-start gap-2 text-sm text-destructive">
                                    <AlertCircle className="h-4 w-4 mt-0.5" />
                                    <span>{error}</span>
                                </div>
                            )}

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
                                        `Continue to checkout — ${formatPrice(event?.price, event?.currency || "USD")}`
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
