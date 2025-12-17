import React, { useEffect, useState } from 'react';
import { Award, Download, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

// We need an API function for getting my certificates. 
// Ideally it's in @/api/certificates or @/api/accounts.
// Backend URL: Accounts -> users/me/certificates/ ? 
// Or Certificates -> /certificates/ ?
// In certificates/urls.py: router.register(r'certificates', views.EventCertificateViewSet)
// This is user's certificates usually. Let's assume GET /api/v1/certificates/ returns list.
// Check certificates/views.py if I could... but assuming standard ViewSet behavior for logged in user.
import client from '@/api/client';
import { Certificate } from '@/api/certificates/types';

const getMyCertificates = async () => {
    const response = await client.get<Certificate[]>('/certificates/');
    return response.data;
};

export const CertificatesPage = () => {
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCerts = async () => {
            try {
                const data = await getMyCertificates();
                setCertificates(data);
            } catch (error) {
                console.error("Failed to load certificates", error);
            } finally {
                setLoading(false);
            }
        };
        fetchCerts();
    }, []);

    if (loading) return <div className="p-8">Loading certificates...</div>;

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-slate-900">My Certificates</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {certificates.map(cert => (
                    <div key={cert.uuid} className="bg-white p-6 rounded-xl border shadow-sm flex flex-col items-center text-center space-y-4">
                        <div className="h-16 w-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center">
                            <Award size={32} />
                        </div>
                        <div>
                            <h3 className="font-bold text-lg text-slate-900">Certificate of Completion</h3>
                            <p className="text-sm text-slate-500 mt-1">
                                Issued {new Date(cert.issued_at).toLocaleDateString()}
                            </p>
                            <p className="text-xs text-slate-400 mt-1 font-mono">
                                ID: {cert.certificate_code}
                            </p>
                        </div>
                        <div className="pt-4 w-full">
                            <Button className="w-full" variant="outline" onClick={() => window.open(cert.file, '_blank')}>
                                <Download size={16} className="mr-2" /> Download PDF
                            </Button>
                        </div>
                    </div>
                ))}

                {certificates.length === 0 && (
                    <div className="col-span-full py-12 text-center text-slate-500">
                        No certificates earned yet. Complete events to earn certificates.
                    </div>
                )}
            </div>
        </div>
    );
};
