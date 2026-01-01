import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldX, Calendar, Award, Building, User, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { verifyCertificate } from '@/api/certificates';

interface CertificateVerificationData {
    status: 'active' | 'issued' | 'revoked';
    is_valid: boolean;
    event: {
        title: string;
        date: string;
        cpd_credits?: string;
        cpd_type?: string;
    };
    registrant: {
        full_name: string;
    };
    organizer: {
        display_name: string;
    };
    certificate_data: Record<string, unknown>;
    created_at: string;
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
        // Navigate to the verification URL with the code
        navigate(`/verify/${inputCode.trim()}`);
    };

    // Show manual input form when no code is provided
    if (!code) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
                    <div className="text-center mb-8">
                        <div className="h-20 w-20 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                            <ShieldCheck className="h-10 w-10" />
                        </div>
                        <h1 className="text-2xl font-bold text-foreground mb-2">Verify Certificate</h1>
                        <p className="text-muted-foreground">Enter the verification code to check certificate authenticity</p>
                    </div>

                    <form onSubmit={handleVerify} className="space-y-4">
                        <div>
                            <label htmlFor="code" className="block text-sm font-medium text-foreground mb-2">
                                Verification Code
                            </label>
                            <Input
                                id="code"
                                type="text"
                                placeholder="Enter 8-character code or full verification code"
                                value={inputCode}
                                onChange={(e) => {
                                    setInputCode(e.target.value.toUpperCase());
                                    setError(null);
                                }}
                                className="text-center font-mono tracking-wider"
                                maxLength={50}
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                                Find the code on your certificate (e.g., ABC12345 or full verification string)
                            </p>
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                {error}
                            </div>
                        )}

                        <Button type="submit" className="w-full" size="lg">
                            <Search className="h-5 w-5 mr-2" />
                            Verify Certificate
                        </Button>
                    </form>

                    <div className="mt-6 text-center">
                        <Link to="/">
                            <Button variant="ghost" size="sm">Return to Home</Button>
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
                <div className="text-center">
                    <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
                    <p className="text-muted-foreground">Verifying certificate...</p>
                </div>
            </div>
        );
    }

    if (error || !certificate) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
                    <div className="h-20 w-20 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
                        <ShieldX className="h-10 w-10" />
                    </div>
                    <h1 className="text-2xl font-bold text-foreground mb-2">Verification Failed</h1>
                    <p className="text-muted-foreground mb-6">{error || 'Certificate not found'}</p>
                    <Link to="/">
                        <Button variant="outline">Return Home</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const isValid = certificate.is_valid && certificate.status !== 'revoked';

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl p-8 max-w-lg w-full">
                {/* Status Header */}
                <div className="text-center mb-8">
                    <div className={`h-20 w-20 rounded-full flex items-center justify-center mx-auto mb-4 ${isValid ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                        }`}>
                        {isValid ? <ShieldCheck className="h-10 w-10" /> : <ShieldX className="h-10 w-10" />}
                    </div>
                    <h1 className={`text-2xl font-bold mb-1 ${isValid ? 'text-green-700' : 'text-red-700'}`}>
                        {isValid ? 'Certificate Verified' : 'Certificate Invalid'}
                    </h1>
                    <p className="text-muted-foreground text-sm">
                        {isValid
                            ? 'This certificate is authentic and valid.'
                            : certificate.status === 'revoked'
                                ? 'This certificate has been revoked.'
                                : 'This certificate could not be verified.'
                        }
                    </p>
                </div>

                {/* Certificate Details */}
                <div className="space-y-4 border-t pt-6">
                    {/* Recipient */}
                    <div className="flex items-start gap-3">
                        <div className="h-10 w-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center shrink-0">
                            <User className="h-5 w-5" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Issued To</p>
                            <p className="font-medium text-foreground">{certificate.registrant.full_name}</p>
                        </div>
                    </div>

                    {/* Event */}
                    <div className="flex items-start gap-3">
                        <div className="h-10 w-10 bg-purple-50 text-purple-600 rounded-lg flex items-center justify-center shrink-0">
                            <Calendar className="h-5 w-5" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Event</p>
                            <p className="font-medium text-foreground">{certificate.event.title}</p>
                            {certificate.event.date && (
                                <p className="text-sm text-muted-foreground">{certificate.event.date}</p>
                            )}
                        </div>
                    </div>

                    {/* CPD Credits */}
                    {certificate.event.cpd_credits && (
                        <div className="flex items-start gap-3">
                            <div className="h-10 w-10 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center shrink-0">
                                <Award className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">CPD Credits</p>
                                <p className="font-medium text-foreground">
                                    {certificate.event.cpd_credits} {certificate.event.cpd_type || 'credits'}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Organizer */}
                    <div className="flex items-start gap-3">
                        <div className="h-10 w-10 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center shrink-0">
                            <Building className="h-5 w-5" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Issued By</p>
                            <p className="font-medium text-foreground">{certificate.organizer.display_name}</p>
                        </div>
                    </div>
                </div>

                {/* Verification Code */}
                <div className="mt-6 pt-6 border-t text-center">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Verification Code</p>
                    <p className="font-mono text-lg font-bold text-foreground tracking-widest">{code}</p>
                </div>

                {/* Footer */}
                <div className="mt-8 text-center">
                    <Link to="/">
                        <Button variant="outline" size="sm">Return to Home</Button>
                    </Link>
                </div>
            </div>
        </div>
    );
};
