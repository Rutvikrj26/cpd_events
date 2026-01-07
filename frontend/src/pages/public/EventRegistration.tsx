import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link, useSearchParams } from "react-router-dom";
import {
    CheckCircle,
    Award,
    Shield,
    FileText,
    TrendingUp,
    Loader2,
    AlertCircle,
    Calendar,
    CreditCard,
    Tag,
    X,
    Check,
    Building2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { getPublicEvent } from "@/api/events";
import { confirmRegistrationPayment, getRegistrationPaymentIntent, registerForEvent } from "@/api/registrations";
import { signup } from "@/api/accounts";
import { validatePromoCode } from "@/api/promo-codes";
import { Event } from "@/api/events/types";
import { RegistrationCreateRequest, RegistrationResponse } from "@/api/registrations/types";
import { PromoCodeValidationResult } from "@/api/promo-codes/types";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { PaymentForm } from "@/components/payment/PaymentForm";
import { CustomFieldsForm } from "@/components/registration/CustomFieldInput";

type RegistrationStep = 'form' | 'payment' | 'success';

export function EventRegistration() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user } = useAuth();

    const [event, setEvent] = useState<Event | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [resumingPayment, setResumingPayment] = useState(false);
    const [paymentIntentLoading, setPaymentIntentLoading] = useState(false);

    // Multi-step state
    const [step, setStep] = useState<RegistrationStep>('form');
    const [registrationData, setRegistrationData] = useState<RegistrationResponse | null>(null);

    // Form state
    const [formData, setFormData] = useState({
        email: user?.email || "",
        firstName: "",
        lastName: "",
        professionalTitle: "",
        organizationName: "",
        billingCountry: "",
        billingState: "",
        billingPostalCode: "",
        billingCity: "",
        createAccount: false,
        password: "",
    });

    // Custom fields state
    const [customFieldValues, setCustomFieldValues] = useState<Record<string, any>>({});

    // Promo code state
    const [promoCode, setPromoCode] = useState("");
    const [promoCodeLoading, setPromoCodeLoading] = useState(false);
    const [appliedPromo, setAppliedPromo] = useState<PromoCodeValidationResult | null>(null);
    const [promoError, setPromoError] = useState<string | null>(null);

    // Determine if event is paid
    const isPaidEvent = event && !event.is_free && event.price && Number(event.price) > 0;

    // Calculate display price (with discount if applicable)
    const displayPrice = appliedPromo?.valid
        ? Number(appliedPromo.final_price)
        : event?.price ? Number(event.price) : 0;

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
                setFormData(prev => ({
                    ...prev,
                    billingCountry: prev.billingCountry || (data.currency?.toUpperCase() === 'USD' ? 'US' : 'CA'),
                }));
            } catch (e: any) {
                setError("Event not found or registration is closed.");
            } finally {
                setLoading(false);
            }
        }
        fetchEvent();
    }, [id, user]);

    useEffect(() => {
        const resumeRegistrationUuid = searchParams.get('resume');
        if (!resumeRegistrationUuid || !event?.uuid) {
            return;
        }

        async function resumePayment() {
            setResumingPayment(true);
            setError(null);
            try {
                const result = await getRegistrationPaymentIntent(resumeRegistrationUuid!);
                setRegistrationData(result);
                setStep('payment');
                toast.info("Complete payment to confirm your registration.");
            } catch (err: any) {
                const message = err?.response?.data?.error?.message || "Unable to resume payment.";
                const code = err?.response?.data?.error?.code;
                if (code === 'BILLING_REQUIRED') {
                    setRegistrationData({ uuid: resumeRegistrationUuid } as RegistrationResponse);
                    setStep('payment');
                    setError(message);
                    toast.info(message);
                    return;
                }
                setError(message);
                toast.error(message);
            } finally {
                setResumingPayment(false);
            }
        }

        resumePayment();
    }, [event?.uuid, searchParams]);

    const handleApplyPromoCode = async () => {
        if (!promoCode.trim() || !event?.uuid || !formData.email) {
            if (!formData.email) {
                setPromoError("Please enter your email first");
            }
            return;
        }

        setPromoCodeLoading(true);
        setPromoError(null);

        try {
            const result = await validatePromoCode({
                code: promoCode.trim(),
                event_uuid: event.uuid,
                email: formData.email,
            });

            if (result.valid) {
                setAppliedPromo(result);
                toast.success(`Promo code applied! ${result.discount_display}`);
            } else {
                setPromoError(result.error || "Invalid promo code");
                setAppliedPromo(null);
            }
        } catch (err: any) {
            const errorMessage = err?.response?.data?.error || "Failed to validate promo code";
            setPromoError(errorMessage);
            setAppliedPromo(null);
        } finally {
            setPromoCodeLoading(false);
        }
    };

    const handleRemovePromoCode = () => {
        setAppliedPromo(null);
        setPromoCode("");
        setPromoError(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!event?.uuid) return;

        setSubmitting(true);
        setError(null);

        try {
            const payload: RegistrationCreateRequest = {
                email: formData.email,
                full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                professional_title: formData.professionalTitle,
                organization_name: formData.organizationName,
                allow_public_verification: true,
                custom_field_responses: customFieldValues,
                promo_code: appliedPromo?.valid ? appliedPromo.code : undefined,
            };

            // 1. Register for the event (use UUID, not slug)
            const response = await registerForEvent(event.uuid, payload);

            setRegistrationData(response);

            // 2. Check if payment is required
            if (response.requires_payment) {
                setStep('payment');
                toast.info("Add billing details to calculate taxes, then complete payment.");
            } else {
                // Free event - registration complete
                await handleAccountCreation();
                setStep('success');
                toast.success("Successfully registered for the event!");
            }
        } catch (err: any) {
            const message = err?.response?.data?.error?.message || err?.response?.data?.detail || "Registration failed. Please try again.";
            setError(message);
            toast.error(message);
        } finally {
            setSubmitting(false);
        }
    };

    const handleCreatePaymentIntent = async () => {
        const registrationUuid = registrationData?.registration_uuid || registrationData?.uuid;
        if (!registrationUuid) {
            setError("Registration reference missing for payment.");
            return;
        }

        const billingCountry = formData.billingCountry.trim().toUpperCase();
        const billingPostalCode = formData.billingPostalCode.trim();

        if (!billingCountry || !billingPostalCode) {
            setError("Billing country and postal code are required for payment.");
            return;
        }

        setPaymentIntentLoading(true);
        setError(null);

        try {
            const paymentIntent = await getRegistrationPaymentIntent(registrationUuid, {
                billing_country: billingCountry,
                billing_state: formData.billingState.trim(),
                billing_postal_code: billingPostalCode,
                billing_city: formData.billingCity.trim(),
            });
            setRegistrationData(paymentIntent);
        } catch (err: any) {
            const message = err?.response?.data?.error?.message || "Unable to calculate taxes.";
            setError(message);
            toast.error(message);
        } finally {
            setPaymentIntentLoading(false);
        }
    };

    const handleAccountCreation = async () => {
        if (formData.createAccount && formData.password) {
            try {
                await signup({
                    email: formData.email,
                    full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                    password: formData.password,
                    password_confirm: formData.password,
                    account_type: "attendee",
                });
                toast.success("Account created! Check your email for verification.");
            } catch (signupError: any) {
                toast.warning("Registered successfully, but account creation failed. You can create an account later.");
            }
        }
    };

    const handlePaymentSuccess = async () => {
        const registrationUuid = registrationData?.registration_uuid || registrationData?.uuid;
        if (!registrationUuid) {
            toast.error("Registration not found for payment confirmation.");
            return;
        }

        try {
            const result = await confirmRegistrationPayment(registrationUuid);
            if (result.status === 'paid') {
                await handleAccountCreation();
                setStep('success');
                toast.success("Payment successful! You're registered.");
            } else if (result.status === 'processing') {
                toast.info("Payment is still processing. We'll update your registration shortly.");
            } else if (result.status === 'event_full') {
                toast.error("This event is fully booked. Your payment was refunded.");
            } else {
                toast.error(result.message || "Payment confirmation failed.");
            }
        } catch (err: any) {
            const message = err?.response?.data?.error?.message || "Payment confirmation failed.";
            toast.error(message);
        }
    };

    const handlePaymentError = (error: string) => {
        toast.error(error);
    };

    // Format price for display
    const formatPrice = (price: number | string | undefined, currency: string = 'USD') => {
        if (!price) return 'Free';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency.toUpperCase(),
        }).format(Number(price));
    };

    if (loading || resumingPayment) {
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
                    <h2 className="text-xl font-semibold text-foreground">{error}</h2>
                    <Link to="/events/browse">
                        <Button className="mt-4">Browse Events</Button>
                    </Link>
                </div>
            </div>
        );
    }

    // Success state
    if (step === 'success') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Card className="max-w-md w-full mx-4">
                    <CardContent className="pt-6 text-center">
                        <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <CheckCircle className="h-8 w-8 text-green-600" />
                        </div>
                        <h2 className="text-2xl font-bold text-foreground mb-2">You're Registered!</h2>
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

    // Payment step
    if (step === 'payment') {
        const showPaymentForm = Boolean(registrationData?.client_secret);

        return (
            <div className="min-h-screen bg-gray-50 py-8 px-4">
                <div className="max-w-lg mx-auto">
                    {/* Event Summary */}
                    <Card className="mb-6">
                        <CardContent className="py-4">
                            <div className="flex items-start gap-4">
                                <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                                    <Calendar className="h-6 w-6 text-blue-600" />
                                </div>
                                <div className="flex-1">
                                    <h1 className="text-xl font-bold text-foreground">{event?.title}</h1>
                                    <p className="text-sm text-muted-foreground mt-1">
                                        Complete payment to confirm your registration
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Payment Form */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <CreditCard className="h-5 w-5" />
                                Complete Payment
                            </CardTitle>
                            <CardDescription>
                                Your spot is reserved. Complete payment to confirm.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {error && (
                                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                    {error}
                                </div>
                            )}

                            {!showPaymentForm && (
                                <div className="space-y-4">
                                    <p className="text-sm text-muted-foreground">
                                        Enter a billing address to calculate taxes and fees.
                                    </p>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="billingCountry">Country *</Label>
                                            <Input
                                                id="billingCountry"
                                                placeholder="CA or US"
                                                value={formData.billingCountry}
                                                onChange={(e) => setFormData({ ...formData, billingCountry: e.target.value.toUpperCase() })}
                                                required
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="billingState">Province/State</Label>
                                            <Input
                                                id="billingState"
                                                placeholder="e.g., ON"
                                                value={formData.billingState}
                                                onChange={(e) => setFormData({ ...formData, billingState: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="billingPostalCode">Postal/ZIP Code *</Label>
                                            <Input
                                                id="billingPostalCode"
                                                placeholder="e.g., M5V 2T6"
                                                value={formData.billingPostalCode}
                                                onChange={(e) => setFormData({ ...formData, billingPostalCode: e.target.value })}
                                                required
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="billingCity">City</Label>
                                            <Input
                                                id="billingCity"
                                                placeholder="e.g., Toronto"
                                                value={formData.billingCity}
                                                onChange={(e) => setFormData({ ...formData, billingCity: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                    <Button
                                        type="button"
                                        onClick={handleCreatePaymentIntent}
                                        disabled={paymentIntentLoading}
                                        className="w-full"
                                    >
                                        {paymentIntentLoading ? (
                                            <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                Calculating total...
                                            </>
                                        ) : (
                                            "Continue to payment"
                                        )}
                                    </Button>
                                </div>
                            )}

                            {showPaymentForm && registrationData && (
                                <>
                                    <div className="mb-4 rounded-lg border bg-muted/30 p-4 text-sm">
                                        <div className="flex items-center justify-between">
                                            <span>Ticket</span>
                                            <span>{formatPrice(registrationData.ticket_price || 0, registrationData.currency || event?.currency)}</span>
                                        </div>
                                        {typeof registrationData.service_fee === 'number' && (
                                            <div className="flex items-center justify-between mt-2">
                                                <span>Service fee</span>
                                                <span>{formatPrice(registrationData.service_fee, registrationData.currency || event?.currency)}</span>
                                            </div>
                                        )}
                                        {typeof registrationData.processing_fee === 'number' && (
                                            <div className="flex items-center justify-between mt-2">
                                                <span>Processing fee</span>
                                                <span>{formatPrice(registrationData.processing_fee, registrationData.currency || event?.currency)}</span>
                                            </div>
                                        )}
                                        {typeof registrationData.tax_amount === 'number' && (
                                            <div className="flex items-center justify-between mt-2">
                                                <span>Tax</span>
                                                <span>{formatPrice(registrationData.tax_amount, registrationData.currency || event?.currency)}</span>
                                            </div>
                                        )}
                                        <Separator className="my-3" />
                                        <div className="flex items-center justify-between font-medium">
                                            <span>Total</span>
                                            <span>{formatPrice(registrationData.total_amount || registrationData.amount || 0, registrationData.currency || event?.currency)}</span>
                                        </div>
                                    </div>
                                    <PaymentForm
                                        clientSecret={registrationData.client_secret!}
                                        amount={registrationData.total_amount || registrationData.amount || Number(event?.price) || 0}
                                        currency={registrationData.currency || event?.currency || 'USD'}
                                        onSuccess={handlePaymentSuccess}
                                        onError={handlePaymentError}
                                    />
                                </>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    // Registration form step
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
                                <div className="flex items-center gap-2">
                                    <h1 className="text-xl font-bold text-foreground">{event?.title}</h1>
                                    {isPaidEvent && (
                                        <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                                            {formatPrice(event?.price, event?.currency)}
                                        </Badge>
                                    )}
                                </div>
                                {event?.organization_info && (
                                    <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                                        <Building2 className="h-4 w-4" />
                                        <span>by {event.organization_info.name}</span>
                                    </div>
                                )}
                                <p className="text-sm text-muted-foreground mt-1">
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
                                <CardDescription>
                                    {isPaidEvent
                                        ? "Fill in your details, then proceed to payment."
                                        : "Fill in your details to secure your spot."
                                    }
                                </CardDescription>
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

                                    {/* Promo Code (for paid events only) */}
                                    {isPaidEvent && (
                                        <div className="space-y-3">
                                            <Label className="flex items-center gap-2">
                                                <Tag className="h-4 w-4" />
                                                Have a promo code?
                                            </Label>

                                            {appliedPromo?.valid ? (
                                                <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <Check className="h-5 w-5 text-green-600" />
                                                        <div>
                                                            <span className="font-medium text-green-800">{appliedPromo.code}</span>
                                                            <span className="text-green-600 ml-2">
                                                                {appliedPromo.discount_display}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={handleRemovePromoCode}
                                                        className="text-green-700 hover:text-green-800 hover:bg-green-100"
                                                    >
                                                        <X className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="flex gap-2">
                                                    <Input
                                                        placeholder="Enter promo code"
                                                        value={promoCode}
                                                        onChange={(e) => {
                                                            setPromoCode(e.target.value.toUpperCase());
                                                            setPromoError(null);
                                                        }}
                                                        className="flex-1"
                                                    />
                                                    <Button
                                                        type="button"
                                                        variant="outline"
                                                        onClick={handleApplyPromoCode}
                                                        disabled={promoCodeLoading || !promoCode.trim()}
                                                    >
                                                        {promoCodeLoading ? (
                                                            <Loader2 className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            "Apply"
                                                        )}
                                                    </Button>
                                                </div>
                                            )}

                                            {promoError && (
                                                <p className="text-sm text-red-600">{promoError}</p>
                                            )}
                                        </div>
                                    )}

                                    {/* Custom Fields */}
                                    {event?.custom_fields && event.custom_fields.length > 0 && (
                                        <>
                                            <Separator />
                                            <CustomFieldsForm
                                                fields={event.custom_fields}
                                                values={customFieldValues}
                                                onChange={(fieldUuid, value) =>
                                                    setCustomFieldValues(prev => ({ ...prev, [fieldUuid]: value }))
                                                }
                                            />
                                        </>
                                    )}

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
                                                Processing...
                                            </>
                                        ) : isPaidEvent ? (
                                            <>
                                                <CreditCard className="mr-2 h-5 w-5" />
                                                Continue to Payment
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
                        {/* Price Card (for paid events) */}
                        {isPaidEvent && (
                            <Card className={`border-primary/20 ${appliedPromo?.valid ? 'bg-green-50 border-green-200' : 'bg-primary/5'}`}>
                                <CardContent className="py-4 text-center">
                                    <p className="text-sm font-medium text-muted-foreground">
                                        {appliedPromo?.valid ? 'Your Price' : 'Event Price'}
                                    </p>

                                    {appliedPromo?.valid ? (
                                        <>
                                            <p className="text-3xl font-bold text-green-700 mt-1">
                                                {displayPrice === 0 ? 'FREE' : formatPrice(displayPrice, event?.currency)}
                                            </p>
                                            <p className="text-sm text-muted-foreground mt-1">
                                                <span className="line-through">{formatPrice(event?.price, event?.currency)}</span>
                                                <span className="text-green-600 ml-2">
                                                    Save {formatPrice(appliedPromo.discount_amount, event?.currency)}
                                                </span>
                                            </p>
                                        </>
                                    ) : (
                                        <p className="text-3xl font-bold text-foreground mt-1">
                                            {formatPrice(event?.price, event?.currency)}
                                        </p>
                                    )}
                                </CardContent>
                            </Card>
                        )}

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
                                        <h4 className="font-medium text-foreground text-sm">Track CPD Credits</h4>
                                        <p className="text-xs text-gray-600">Automatically log your professional development hours.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-green-100 rounded-lg flex items-center justify-center shrink-0">
                                        <FileText className="h-4 w-4 text-green-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-foreground text-sm">Digital Certificates</h4>
                                        <p className="text-xs text-gray-600">Access and share your certificates anytime.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
                                        <TrendingUp className="h-4 w-4 text-blue-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-foreground text-sm">Progress Dashboard</h4>
                                        <p className="text-xs text-gray-600">See your learning journey at a glance.</p>
                                    </div>
                                </div>

                                <div className="flex items-start gap-3">
                                    <div className="h-8 w-8 bg-purple-100 rounded-lg flex items-center justify-center shrink-0">
                                        <Shield className="h-4 w-4 text-purple-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-foreground text-sm">Verified Records</h4>
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
