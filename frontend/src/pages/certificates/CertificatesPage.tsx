import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Award, Check, Download, Eye, Search, Share2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Badge } from '@/shared/ui/badge';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/shared/ui/table';
import { EmptyState } from '@/shared/ui/empty-state';
import { useAuth } from '@/features/auth';
import { useMyCertificates } from '@/features/certificates';
import { downloadCertificate } from '@/api/certificates';
import { getRoleFlags } from '@/lib/role-utils';
import type { Certificate } from '@/api/certificates/types';

export const CertificatesPage = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const { isOrganizer, isInstructor, isAdmin } = getRoleFlags(user);
    const isStaffView = isOrganizer || isInstructor || isAdmin;

    const { data: certificates = [], isLoading } = useMyCertificates();

    const [searchTerm, setSearchTerm] = useState('');
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [downloadingId, setDownloadingId] = useState<string | null>(null);

    const filteredCertificates = useMemo(() => {
        const q = searchTerm.toLowerCase();
        return certificates.filter((cert) => {
            const title = (
                cert.event?.title ||
                cert.certificate_data?.event_title ||
                ''
            ).toLowerCase();
            const code = (cert.short_code || '').toLowerCase();
            return title.includes(q) || code.includes(q);
        });
    }, [certificates, searchTerm]);

    const handleCopyLink = async (cert: Certificate) => {
        const verifyUrl =
            cert.verification_url ||
            cert.share_url ||
            `${window.location.origin}/verify/${cert.short_code}`;
        try {
            await navigator.clipboard.writeText(verifyUrl);
            setCopiedId(cert.uuid);
            toast.success('Verification link copied!');
            setTimeout(() => setCopiedId(null), 2000);
        } catch {
            toast.error('Failed to copy link');
        }
    };

    const handleDownload = async (cert: Certificate) => {
        setDownloadingId(cert.uuid);
        try {
            const { download_url } = await downloadCertificate(cert.uuid);
            if (download_url) {
                window.open(download_url, '_blank');
                toast.success('Certificate downloaded!');
            } else {
                toast.error('PDF not available for this certificate');
            }
        } catch (error: any) {
            if (error?.response?.data?.error?.code === 'FEEDBACK_REQUIRED') {
                toast.error(
                    error?.response?.data?.error?.message ||
                        'Please submit feedback before downloading',
                    {
                        action: {
                            label: 'Give Feedback',
                            onClick: () => navigate('/registrations'),
                        },
                    }
                );
            } else {
                toast.error('Failed to download certificate');
            }
        } finally {
            setDownloadingId(null);
        }
    };

    const handleView = (cert: Certificate) => {
        window.open(`/verify/${cert.short_code}`, '_blank');
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-block">
                <div className="animate-pulse text-muted-foreground">Loading certificates...</div>
            </div>
        );
    }

    return (
        <div className="space-y-card">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-h1 text-foreground">
                        {isStaffView ? 'Certificates' : 'My certificates'}
                    </h1>
                    <p className="mt-1 text-body text-muted-foreground">
                        {isStaffView
                            ? 'Certificates you have earned personally. For all certificates across the platform, see each event or course.'
                            : 'Your earned certificates and credentials.'}
                    </p>
                </div>
                {certificates.length > 0 && (
                    <Badge variant="secondary" className="text-body">
                        {certificates.length} certificate
                        {certificates.length !== 1 ? 's' : ''}
                    </Badge>
                )}
            </div>

            <div className="relative">
                <Search className="pointer-events-none absolute inset-y-0 left-0 my-auto ml-3 h-4 w-4 text-muted-foreground" />
                <Input
                    placeholder="Search certificates by event, course, or code..."
                    className="max-w-sm pl-10"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            {filteredCertificates.length > 0 ? (
                <div className="overflow-hidden rounded-lg border">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/50">
                                <TableHead className="w-[300px]">Event/Course</TableHead>
                                <TableHead>Certificate ID</TableHead>
                                <TableHead>Issued</TableHead>
                                <TableHead>CPD credits</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredCertificates.map((cert) => (
                                <CertificateRow
                                    key={cert.uuid}
                                    cert={cert}
                                    copied={copiedId === cert.uuid}
                                    downloading={downloadingId === cert.uuid}
                                    onView={handleView}
                                    onCopy={handleCopyLink}
                                    onDownload={handleDownload}
                                />
                            ))}
                        </TableBody>
                    </Table>
                </div>
            ) : (
                <EmptyState
                    tone="dashed"
                    icon={Award}
                    title={searchTerm ? 'No matching certificates' : 'No certificates yet'}
                    description={
                        searchTerm
                            ? "Try adjusting your search terms to find what you're looking for."
                            : isStaffView
                              ? "You haven't earned any certificates yourself yet. To review certificates issued to learners, open the specific event or course and check its Certificates tab."
                              : 'Complete events or courses to earn certificates. They will appear here once issued.'
                    }
                    action={
                        !searchTerm && isStaffView ? (
                            <div className="flex flex-wrap justify-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => navigate('/events')}
                                >
                                    Go to events
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => navigate('/courses/manage')}
                                >
                                    Go to courses
                                </Button>
                            </div>
                        ) : undefined
                    }
                />
            )}
        </div>
    );
};

function CertificateRow({
    cert,
    copied,
    downloading,
    onView,
    onCopy,
    onDownload,
}: {
    cert: Certificate;
    copied: boolean;
    downloading: boolean;
    onView: (cert: Certificate) => void;
    onCopy: (cert: Certificate) => void;
    onDownload: (cert: Certificate) => void;
}) {
    return (
        <TableRow className="hover:bg-muted/30">
            <TableCell>
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Award size={20} />
                    </div>
                    <div className="min-w-0">
                        <p className="truncate font-medium text-foreground">
                            {cert.event?.title || cert.certificate_data?.event_title || 'Certificate'}
                        </p>
                        <div className="flex items-center gap-2 text-caption text-muted-foreground">
                            <span>Certificate of Completion</span>
                            {cert.event?.event_type && (
                                <Badge
                                    variant="outline"
                                    className="text-[10px] uppercase tracking-wide"
                                >
                                    {cert.event.event_type}
                                </Badge>
                            )}
                        </div>
                    </div>
                </div>
            </TableCell>
            <TableCell>
                <code className="rounded bg-muted px-2 py-1 font-mono text-body">
                    {cert.short_code}
                </code>
            </TableCell>
            <TableCell>
                <span className="text-body">
                    {new Date(cert.issued_at || cert.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                    })}
                </span>
            </TableCell>
            <TableCell>
                {cert.event?.cpd_credits || cert.certificate_data?.cpd_credits ? (
                    <Badge variant="outline" className="font-medium">
                        {cert.event?.cpd_credits || cert.certificate_data?.cpd_credits}{' '}
                        {cert.event?.cpd_type || cert.certificate_data?.cpd_type || 'credits'}
                    </Badge>
                ) : (
                    <span className="text-body text-muted-foreground">—</span>
                )}
            </TableCell>
            <TableCell>
                {cert.is_valid !== false && cert.status !== 'revoked' ? (
                    <Badge variant="success">
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
                        onClick={() => onView(cert)}
                    >
                        <Eye size={16} className="mr-1" />
                        View
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2"
                        onClick={() => onCopy(cert)}
                    >
                        {copied ? (
                            <Check size={16} className="mr-1 text-success" />
                        ) : (
                            <Share2 size={16} className="mr-1" />
                        )}
                        Share
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2"
                        onClick={() => onDownload(cert)}
                        disabled={downloading}
                    >
                        <Download size={16} className="mr-1" />
                        {downloading ? 'Downloading...' : 'PDF'}
                    </Button>
                </div>
            </TableCell>
        </TableRow>
    );
}
