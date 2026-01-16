import React, { useEffect, useState } from 'react';
import { Award, Download, Eye, Share2, Check, ShieldCheck, Search, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Link, useNavigate } from 'react-router-dom';
import { getMyCertificates, downloadCertificate } from '@/api/certificates';
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
    const navigate = useNavigate();
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [loading, setLoading] = useState(true);
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [downloadingId, setDownloadingId] = useState<string | null>(null);

    useEffect(() => {
        const fetchCerts = async () => {
            try {
                const data = await getMyCertificates();
                setCertificates(data.results);
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

    const handleDownload = async (cert: Certificate) => {
        setDownloadingId(cert.uuid);
        try {
            const { download_url } = await downloadCertificate(cert.uuid);
            if (download_url) {
                window.open(download_url, '_blank');
                toast.success("Certificate downloaded!");
            } else {
                toast.error("PDF not available for this certificate");
            }
        } catch (error: any) {
            // Check if it's a feedback required error
            if (error?.response?.data?.error?.code === 'FEEDBACK_REQUIRED') {
                toast.error(
                    error?.response?.data?.error?.message || 'Please submit feedback before downloading',
                    {
                        action: {
                            label: 'Give Feedback',
                            onClick: () => navigate('/registrations')
                        }
                    }
                );
            } else {
                toast.error("Failed to download certificate");
            }
        } finally {
            setDownloadingId(null);
        }
    };

    const handleView = (cert: Certificate) => {
        window.open(`/verify/${cert.short_code}`, '_blank');
    };

    const filteredCertificates = certificates.filter(cert => {
        const searchLower = searchTerm.toLowerCase();
        const title = (cert.event?.title || cert.certificate_data?.event_title || '').toLowerCase();
        const code = (cert.short_code || '').toLowerCase();
        return title.includes(searchLower) || code.includes(searchLower);
    });

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

            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-muted-foreground" />
                </div>
                <Input
                    placeholder="Search certificates by event, course, or code..."
                    className="pl-10 max-w-sm"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            {
                filteredCertificates.length > 0 ? (
                    <div className="border rounded-lg overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/50">
                                    <TableHead className="w-[300px]">Event/Course</TableHead>
                                    <TableHead>Certificate ID</TableHead>
                                    <TableHead>Issued</TableHead>
                                    <TableHead>CPD Credits</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredCertificates.map(cert => (
                                    <TableRow key={cert.uuid} className="hover:bg-muted/30">
                                        <TableCell>
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 bg-primary/10 text-primary rounded-lg flex items-center justify-center shrink-0">
                                                    <Award size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-medium text-foreground truncate">
                                                        {cert.event?.title || cert.certificate_data?.event_title || 'Certificate'}
                                                    </p>
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <span>Certificate of Completion</span>
                                                        {cert.event?.event_type && (
                                                            <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                                                                {cert.event.event_type}
                                                            </Badge>
                                                        )}
                                                    </div>
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
                                                <Badge className="bg-primary/10 text-primary hover:bg-primary/20 border-0">
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
                                                    disabled={downloadingId === cert.uuid}
                                                >
                                                    <Download size={16} className="mr-1" />
                                                    {downloadingId === cert.uuid ? 'Downloading...' : 'PDF'}
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
                        <h3 className="text-lg font-medium text-foreground mb-1">
                            {searchTerm ? 'No matching certificates' : 'No certificates yet'}
                        </h3>
                        <p className="text-muted-foreground text-center max-w-sm">
                            {searchTerm
                                ? "Try adjusting your search terms to find what you're looking for."
                                : "Complete events to earn certificates. They will appear here once issued by the organizer."
                            }
                        </p>
                        {!searchTerm && (
                            <Link to="/events/browse" className="mt-4">
                                <Button variant="outline">Browse Events</Button>
                            </Link>
                        )}
                    </div>
                )
            }
        </div >
    );
};
