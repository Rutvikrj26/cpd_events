import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldX, Calendar, Award, Building, User, Loader2, Search, Download, Share2, Copy, Printer, ExternalLink, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
// import { Badge } from '@/components/ui/badge'; // Assuming Badge component exists or we can use standard tailwind classes
import { verifyCertificate } from '@/api/certificates';
import { toast } from 'sonner';

interface CertificateVerificationData {
    uuid: string;
    status: 'active' | 'issued' | 'revoked';
    is_valid: boolean;
    verification_code?: string;
    event: {
        title: string;
        date: string;
        cpd_credits?: string;
        cpd_type?: string;
        type?: 'event' | 'course';
    };
    registrant: {
        full_name: string;
    };
    organizer: {
        display_name: string;
    };
    certificate_data: Record<string, unknown>;
    created_at: string;
    file_url?: string | null;
}

export const CertificateVerify = () => {
    const { code } = useParams<{ code: string }>();
    const navigate = useNavigate();
    const [certificate, setCertificate] = useState<CertificateVerificationData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [inputCode, setInputCode] = useState('');

    useEffect(() => {
        if (!code) {
            return;
        }

        const verify = async () => {
            setLoading(true);
            setError(null);

            try {
                const data = await verifyCertificate(code);
                setCertificate(data as unknown as CertificateVerificationData);
            } catch (err: any) {
                if (err?.response?.status === 404) {
                    setError('Certificate not found. Please check the verification code.');
                } else {
                    setError('Unable to verify certificate. Please try again later.');
                }
            } finally {
                setLoading(false);
            }
        };

        verify();
    }, [code]);

    const handleVerify = (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputCode.trim()) {
            setError('Please enter a verification code');
            return;
        }
        navigate(`/verify/${inputCode.trim()}`);
    };

    const copyToClipboard = () => {
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            toast.success('Link copied to clipboard');
        });
    };

    const handlePrint = () => {
        window.print();
    };

    const handleDownload = () => {
        if (certificate?.file_url) {
            window.open(certificate.file_url, '_blank');
        } else {
            toast.error('Download not available');
        }
    };


    // Loading State
    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-muted-foreground">Verifying certificate...</p>
                </div>
            </div>
        );
    }

    // Default View (No Code)
    if (!code) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <div className="bg-card rounded-xl shadow-sm border border-border p-8 max-w-md w-full">
                    <div className="text-center mb-8">
                        <div className="h-16 w-16 bg-info-subtle text-info rounded-full flex items-center justify-center mx-auto mb-4">
                            <ShieldCheck className="h-8 w-8" />
                        </div>
                        <h1 className="text-2xl font-bold text-foreground mb-2">Verify Certificate</h1>
                        <p className="text-muted-foreground">Enter the verification code to check certificate authenticity</p>
                    </div>

                    <form onSubmit={handleVerify} className="space-y-4">
                        <div>
                            <Input
                                type="text"
                                placeholder="Enter Verification Code"
                                value={inputCode}
                                onChange={(e) => {
                                    setInputCode(e.target.value.toUpperCase());
                                    setError(null);
                                }}
                                className="text-center font-mono tracking-wider h-12 text-lg uppercase"
                            />
                        </div>

                        {error && (
                            <div className="bg-error-subtle border border-error text-error px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                                <ShieldX className="h-4 w-4 shrink-0" />
                                {error}
                            </div>
                        )}

                        <Button type="submit" className="w-full h-11" size="lg">
                            Verify Certificate
                        </Button>
                    </form>
                </div>
            </div>
        );
    }

    // Error View
    if (error || !certificate) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <div className="bg-card rounded-xl shadow-sm border border-border p-8 max-w-md w-full text-center">
                    <div className="h-16 w-16 bg-error-subtle text-error rounded-full flex items-center justify-center mx-auto mb-4">
                        <ShieldX className="h-8 w-8" />
                    </div>
                    <h1 className="text-2xl font-bold text-foreground mb-2">Verification Failed</h1>
                    <p className="text-muted-foreground mb-6">{error || 'Certificate not found'}</p>
                    <div className="flex gap-3 justify-center">
                        <Link to="/">
                            <Button variant="outline">Back to Home</Button>
                        </Link>
                        <Link to="/verify">
                            <Button>Try Another Code</Button>
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    // Valid Certificate View
    const isValid = certificate.is_valid && certificate.status !== 'revoked';
    const isCourse = certificate.event.type === 'course';

    return (
        <div className="min-h-screen bg-background pb-12 font-sans">
            {/* Header */}
            <header className="bg-card border-b border-border sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {/* You can replace this with your actual logo */}
                        <div className="h-8 w-8 bg-primary rounded-md flex items-center justify-center text-primary-foreground font-bold font-outfit">
                            A
                        </div>
                        <span className="font-semibold text-foreground">Certificate Verification</span>
                    </div>

                    {isValid && (
                        <div className="flex items-center gap-1.5 bg-success-subtle text-success px-3 py-1 rounded-full text-sm font-medium border border-success">
                            <CheckCircle className="h-4 w-4" />
                            <span>Verified Authentic</span>
                        </div>
                    )}
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                    {/* Left Column - Main Certificate Card */}
                    <div className="lg:col-span-8 space-y-6">

                        {/* Status Banner */}
                        <div className={`${isValid ? 'bg-emerald-600' : 'bg-red-600'} text-white rounded-t-xl p-6 shadow-sm`}>
                            <div className="flex items-center gap-4">
                                <div className="bg-white/20 p-3 rounded-full">
                                    {isValid ? <ShieldCheck className="h-8 w-8" /> : <ShieldX className="h-8 w-8" />}
                                </div>
                                <div>
                                    <h1 className="text-2xl font-bold">
                                        {isValid ? 'Certification Verified' : 'Certification Invalid'}
                                    </h1>
                                    <p className="text-white/90">
                                        {isValid
                                            ? `Awarded to ${certificate.registrant.full_name}`
                                            : 'This certificate code is not valid or has been revoked.'
                                        }
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Certificate Details Card */}
                        <div className="bg-card rounded-b-xl shadow-sm border border-border border-t-0 p-8 -mt-6">

                            <div className="flex flex-col md:flex-row gap-8 items-start mb-10">
                                {/* Digital Badge Icon (Placeholder) */}
                                <div className="shrink-0 mx-auto md:mx-0">
                                    <div className="w-32 h-32 bg-muted/50 rounded-full flex items-center justify-center border-4 border-muted/20 shadow-inner">
                                        <Award className="h-16 w-16 text-muted-foreground" />
                                    </div>
                                </div>

                                <div className="flex-1 text-center md:text-left">
                                    <p className="text-muted-foreground mb-2">This certifies that</p>
                                    <h2 className="text-3xl font-bold text-foreground mb-2">{certificate.registrant.full_name}</h2>
                                    <p className="text-muted-foreground mb-2">has successfully completed the requirements for the {isCourse ? 'course' : 'program'}</p>
                                    <h3 className="text-xl font-semibold text-primary">{certificate.event.title}</h3>
                                </div>
                            </div>

                            <Separator className="my-8" />

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-12">
                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Issue Date</h4>
                                    <p className="text-foreground font-medium">
                                        {new Date(certificate.created_at).toLocaleDateString(undefined, {
                                            year: 'numeric',
                                            month: 'long',
                                            day: 'numeric'
                                        })}
                                    </p>
                                </div>

                                {certificate.event.date && (
                                    <div>
                                        <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">
                                            {isCourse ? 'Completion Date' : 'Event Date'}
                                        </h4>
                                        <p className="text-foreground font-medium">{certificate.event.date}</p>
                                    </div>
                                )}

                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Issued By</h4>
                                    <div className="flex items-center gap-2">
                                        <Building className="h-4 w-4 text-muted-foreground" />
                                        <p className="text-foreground font-medium">{certificate.organizer.display_name}</p>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Certificate ID</h4>
                                    <p className="font-mono text-muted-foreground bg-muted/50 inline-block px-2 py-0.5 rounded text-sm">
                                        {certificate.verification_code || code}
                                    </p>
                                </div>

                                {certificate.event.cpd_credits && (
                                    <div>
                                        <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Credits Awarded</h4>
                                        <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-info-subtle text-info">
                                            {certificate.event.cpd_credits} {certificate.event.cpd_type}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Sidebar Actions */}
                    <div className="lg:col-span-4 space-y-6">

                        {/* Actions Card */}
                        <div className="bg-card rounded-xl shadow-sm border border-border p-6">
                            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                                <ExternalLink className="h-4 w-4" />
                                Certificate Actions
                            </h3>

                            <div className="space-y-3">
                                <Button
                                    className="w-full justify-start"
                                    onClick={handleDownload}
                                    variant="outline"
                                >
                                    <Download className="h-4 w-4 mr-2" />
                                    Download PDF
                                </Button>

                                <Button
                                    className="w-full justify-start"
                                    onClick={copyToClipboard}
                                    variant="outline"
                                >
                                    <Copy className="h-4 w-4 mr-2" />
                                    Copy Link
                                </Button>

                                <Button
                                    className="w-full justify-start"
                                    onClick={handlePrint}
                                    variant="outline"
                                >
                                    <Printer className="h-4 w-4 mr-2" />
                                    Print Certificate
                                </Button>

                                <Button
                                    className="w-full justify-start"
                                    variant="outline"
                                    onClick={() => window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.href)}`, '_blank')}
                                >
                                    <Share2 className="h-4 w-4 mr-2" />
                                    Share on LinkedIn
                                </Button>
                            </div>
                        </div>

                        {/* Verification Info Card */}
                        <div className="bg-muted/30 rounded-xl border border-border p-6 text-sm">
                            <h3 className="font-semibold text-foreground mb-2">About Verification</h3>
                            <p className="text-muted-foreground mb-4">
                                This page verifies that the {isCourse ? 'course' : 'program'} certificate was issued by {certificate.organizer.display_name} to the named recipient.
                            </p>

                            <div className="flex items-center gap-2 text-muted-foreground text-xs">
                                <ShieldCheck className="h-4 w-4" />
                                <span>Secured by Accredit</span>
                            </div>
                        </div>

                    </div>
                </div>
            </main>
            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center text-muted-foreground text-sm">
                <p>&copy; {new Date().getFullYear()} {certificate.organizer.display_name}. All rights reserved.</p>
            </footer>
        </div>
    );
};
