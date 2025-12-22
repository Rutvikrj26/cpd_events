import React, { useEffect, useState } from 'react';
import { Award, Download, Eye, Share2, Check, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { getMyCertificates } from '@/api/certificates';
import { Certificate } from '@/api/certificates/types';
import { toast } from 'sonner';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

export const CertificatesPage = () => {
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [loading, setLoading] = useState(true);
    const [copiedId, setCopiedId] = useState<string | null>(null);

    useEffect(() => {
        const fetchCerts = async () => {
            try {
                const data = await getMyCertificates();
                setCertificates(data);
            } catch (error) {
                console.error("Failed to load certificates", error);
                toast.error("Failed to load certificates");
            } finally {
                setLoading(false);
            }
        };
        fetchCerts();
    }, []);

    const handleCopyLink = async (cert: Certificate) => {
        const verifyUrl = cert.verification_url || cert.share_url || `${window.location.origin}/verify/${cert.short_code}`;
        try {
            await navigator.clipboard.writeText(verifyUrl);
            setCopiedId(cert.uuid);
            toast.success("Verification link copied!");
            setTimeout(() => setCopiedId(null), 2000);
        } catch {
            toast.error("Failed to copy link");
        }
    };

    const handleDownload = (cert: Certificate) => {
        if (cert.download_url) {
            window.open(cert.download_url, '_blank');
        } else {
            toast.error("PDF not available for this certificate");
        }
    };

    const handleView = (cert: Certificate) => {
        window.open(`/verify/${cert.short_code}`, '_blank');
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <div className="animate-pulse text-muted-foreground">Loading certificates...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground">My Certificates</h1>
                    <p className="text-muted-foreground mt-1">Your earned certificates and credentials</p>
                </div>
                {certificates.length > 0 && (
                    <Badge variant="secondary" className="text-sm">
                        {certificates.length} certificate{certificates.length !== 1 ? 's' : ''}
                    </Badge>
                )}
            </div>

            {certificates.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/50">
                                <TableHead className="w-[300px]">Event</TableHead>
                                <TableHead>Certificate ID</TableHead>
                                <TableHead>Issued</TableHead>
                                <TableHead>CPD Credits</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {certificates.map(cert => (
                                <TableRow key={cert.uuid} className="hover:bg-muted/30">
                                    <TableCell>
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center shrink-0">
                                                <Award size={20} />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="font-medium text-foreground truncate">
                                                    {cert.event?.title || cert.certificate_data?.event_title || 'Certificate'}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    Certificate of Completion
                                                </p>
                                            </div>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <code className="text-sm bg-muted px-2 py-1 rounded font-mono">
                                            {cert.short_code}
                                        </code>
                                    </TableCell>
                                    <TableCell>
                                        <span className="text-sm">
                                            {new Date(cert.issued_at || cert.created_at).toLocaleDateString('en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                                year: 'numeric'
                                            })}
                                        </span>
                                    </TableCell>
                                    <TableCell>
                                        {(cert.event?.cpd_credits || cert.certificate_data?.cpd_credits) ? (
                                            <Badge variant="outline" className="font-medium">
                                                {cert.event?.cpd_credits || cert.certificate_data?.cpd_credits} {cert.event?.cpd_type || cert.certificate_data?.cpd_type || 'credits'}
                                            </Badge>
                                        ) : (
                                            <span className="text-muted-foreground text-sm">—</span>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        {cert.is_valid !== false && cert.status !== 'revoked' ? (
                                            <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                                                <ShieldCheck size={12} className="mr-1" />
                                                Valid
                                            </Badge>
                                        ) : (
                                            <Badge variant="destructive">Revoked</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center justify-end gap-1">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 px-2"
                                                onClick={() => handleView(cert)}
                                            >
                                                <Eye size={16} className="mr-1" />
                                                View
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 px-2"
                                                onClick={() => handleCopyLink(cert)}
                                            >
                                                {copiedId === cert.uuid ? (
                                                    <Check size={16} className="mr-1 text-green-600" />
                                                ) : (
                                                    <Share2 size={16} className="mr-1" />
                                                )}
                                                Share
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 px-2"
                                                onClick={() => handleDownload(cert)}
                                                disabled={!cert.download_url}
                                            >
                                                <Download size={16} className="mr-1" />
                                                PDF
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-lg border border-dashed">
                    <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                        <Award size={32} />
                    </div>
                    <h3 className="text-lg font-medium text-foreground mb-1">No certificates yet</h3>
                    <p className="text-muted-foreground text-center max-w-sm">
                        Complete events to earn certificates. They will appear here once issued by the organizer.
                    </p>
                    <Link to="/events/browse" className="mt-4">
                        <Button variant="outline">Browse Events</Button>
                    </Link>
                </div>
            )}
        </div>
    );
};
