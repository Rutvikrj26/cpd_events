import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
    CheckCircle,
    Award,
    Shield,
    FileText,
    TrendingUp,
    Loader2,
    AlertCircle,
    Calendar
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getPublicEvent } from "@/api/events";
import { registerForEvent } from "@/api/registrations";
import { signup } from "@/api/accounts";
import { Event } from "@/api/events/types";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

export function EventRegistration() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [event, setEvent] = useState<Event | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        email: user?.email || "",
        firstName: "",
        lastName: "",
        professionalTitle: "",
        organizationName: "",
        createAccount: false,
        password: "",
    });

    useEffect(() => {
        async function fetchEvent() {
            if (!id) return;
            try {
                const data = await getPublicEvent(id);
                setEvent(data);
                // Parse full name into first/last for form
                if (user) {
                    const nameParts = (user.full_name || "").split(" ");
                    setFormData(prev => ({
                        ...prev,
                        email: user.email,
                        firstName: nameParts[0] || "",
                        lastName: nameParts.slice(1).join(" ") || "",
                    }));
                }
            } catch (e: any) {
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
            // 1. Register for the event (use UUID, not slug)
            await registerForEvent(event.uuid, {
                email: formData.email,
                full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                professional_title: formData.professionalTitle,
                organization_name: formData.organizationName,
                allow_public_verification: true,
            });

            // 2. Create account if checkbox is checked
            if (formData.createAccount && formData.password) {
                try {
                    await signup({
                        email: formData.email,
                        full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                        password: formData.password,
                        confirm_password: formData.password,
                        account_type: "attendee",
                    });
                    toast.success("Account created! Check your email for verification.");
                } catch (signupError: any) {
                    // Still show success for registration, but note the account issue
                    toast.warning("Registered successfully, but account creation failed. You can create an account later.");
                }
            }

            setSuccess(true);
            toast.success("Successfully registered for the event!");
        } catch (err: any) {
            const message = err?.response?.data?.error?.message || err?.response?.data?.detail || "Registration failed. Please try again.";
            setError(message);
            toast.error(message);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        );
    }

    if (error && !event) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-gray-900">{error}</h2>
                    <Link to="/events/browse">
                        <Button className="mt-4">Browse Events</Button>
                    </Link>
                </div>
            </div>
        );
    }

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Card className="max-w-md w-full mx-4">
                    <CardContent className="pt-6 text-center">
                        <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <CheckCircle className="h-8 w-8 text-green-600" />
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">You're Registered!</h2>
                        <p className="text-gray-600 mb-6">
                            Check your email for confirmation details and event information.
                        </p>
                        <div className="space-y-3">
                            <Link to={`/events/${event?.slug || id}`}>
                                <Button className="w-full">View Event Details</Button>
                            </Link>
                            <Link to="/events/browse">
                                <Button variant="outline" className="w-full">Browse More Events</Button>
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4">
            <div className="max-w-4xl mx-auto">
                {/* Event Summary */}
                <Card className="mb-6">
                    <CardContent className="py-4">
                        <div className="flex items-start gap-4">
                            <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                                <Calendar className="h-6 w-6 text-blue-600" />
                            </div>
                            <div className="flex-1">
                                <h1 className="text-xl font-bold text-gray-900">{event?.title}</h1>
                                <p className="text-sm text-gray-500 mt-1">
                                    {event?.starts_at && new Date(event.starts_at).toLocaleDateString(undefined, {
                                        weekday: 'long',
                                        month: 'long',
                                        day: 'numeric',
                                        year: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
                                </p>
                                {event?.cpd_credits && Number(event.cpd_credits) > 0 && (
                                    <div className="flex items-center gap-1 mt-2 text-amber-600">
                                        <Award className="h-4 w-4" />
                                        <span className="text-sm font-medium">{event.cpd_credits} CPD Credits</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Registration Form */}
                    <div className="lg:col-span-2">
                        <Card>
                            <CardHeader>
                                <CardTitle>Register for this Event</CardTitle>
                                <CardDescription>Fill in your details to secure your spot.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSubmit} className="space-y-6">
                                    {error && (
                                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                            {error}
                                        </div>
                                    )}

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="firstName">First Name *</Label>
                                            <Input
                                                id="firstName"
                                                value={formData.firstName}
                                                onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                                                required
                                                disabled={!!user}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="lastName">Last Name *</Label>
                                            <Input
                                                id="lastName"
                                                value={formData.lastName}
                                                onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                                                required
                                                disabled={!!user}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="email">Email Address *</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            required
                                            disabled={!!user}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="professionalTitle">Professional Title</Label>
                                            <Input
                                                id="professionalTitle"
                                                placeholder="e.g., Senior Nurse"
                                                value={formData.professionalTitle}
                                                onChange={(e) => setFormData({ ...formData, professionalTitle: e.target.value })}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="organizationName">Organization</Label>
                                            <Input
                                                id="organizationName"
                                                placeholder="e.g., City Hospital"
                                                value={formData.organizationName}
                                                onChange={(e) => setFormData({ ...formData, organizationName: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    {!user && (
                                        <>
                                            <Separator />

                                            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                                                <div className="flex items-start space-x-3">
                                                    <Checkbox
                                                        id="createAccount"
                                                        checked={formData.createAccount}
                                                        onCheckedChange={(checked) =>
                                                            setFormData({ ...formData, createAccount: checked as boolean })
                                                        }
                                                    />
                                                    <div className="flex-1">
                                                        <Label htmlFor="createAccount" className="font-medium cursor-pointer">
                                                            Create an account to track my CPD credits
                                                        </Label>
                                                        <p className="text-sm text-gray-600 mt-1">
                                                            Get access to your CPD dashboard, certificates, and event history.
                                                        </p>
                                                    </div>
                                                </div>

                                                {formData.createAccount && (
                                                    <div className="mt-4 space-y-2">
                                                        <Label htmlFor="password">Create Password *</Label>
                                                        <Input
                                                            id="password"
                                                            type="password"
                                                            placeholder="At least 8 characters"
                                                            value={formData.password}
                                                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                                            required={formData.createAccount}
                                                            minLength={8}
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    )}

                                    <Button
                                        type="submit"
                                        className="w-full bg-blue-600 hover:bg-blue-700 py-6 text-lg"
                                        disabled={submitting}
                                    >
                                        {submitting ? (
                                            <>
                                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                                Registering...
                                            </>
                                        ) : (
                                            "Complete Registration"
                                        )}
                                    </Button>
                                </form>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Benefits Sidebar */}
                    <div className="space-y-6">
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base">Why Create an Account?</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-amber-100 rounded-lg flex items-center justify-center shrink-0">
                                        <Award className="h-4 w-4 text-amber-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-gray-900 text-sm">Track CPD Credits</h4>
                                        <p className="text-xs text-gray-600">Automatically log your professional development hours.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-green-100 rounded-lg flex items-center justify-center shrink-0">
                                        <FileText className="h-4 w-4 text-green-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-gray-900 text-sm">Digital Certificates</h4>
                                        <p className="text-xs text-gray-600">Access and share your certificates anytime.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
                                        <TrendingUp className="h-4 w-4 text-blue-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-gray-900 text-sm">Progress Dashboard</h4>
                                        <p className="text-xs text-gray-600">See your learning journey at a glance.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-purple-100 rounded-lg flex items-center justify-center shrink-0">
                                        <Shield className="h-4 w-4 text-purple-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-gray-900 text-sm">Verified Records</h4>
                                        <p className="text-xs text-gray-600">Employer-verifiable attendance and completion records.</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {event?.spots_remaining !== undefined && event.spots_remaining !== null && (
                            <Card className="border-amber-200 bg-amber-50">
                                <CardContent className="py-4 text-center">
                                    <p className="text-2xl font-bold text-amber-700">{event.spots_remaining}</p>
                                    <p className="text-sm text-amber-600">spots remaining</p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
