import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Download, ExternalLink, ShieldCheck, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { getMyCertificates } from "@/api/certificates";
import { Certificate } from "@/api/certificates/types";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";

export function CertificatesList() {
  const [searchTerm, setSearchTerm] = useState("");
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getMyCertificates();
        setCertificates(data);
      } catch (error) {
        toast.error("Failed to load certificates");
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const filteredCerts = certificates.filter(c =>
    c.event?.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="p-8">Loading certificates...</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Certificates"
        description="Access and manage your professional credentials."
      />

      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by event or course..."
            className="pl-9"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" className="w-full sm:w-auto">
            <Filter className="mr-2 h-4 w-4" /> Filter Year
          </Button>
          <Button variant="outline" className="w-full sm:w-auto">
            <Download className="mr-2 h-4 w-4" /> Export All
          </Button>
        </div>
      </div>

      {filteredCerts.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCerts.map((cert) => (
            <CertificateCard key={cert.uuid} cert={cert} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-lg border border-dashed border-border">
          <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-1">No certificates found</h3>
          <p className="text-muted-foreground text-center max-w-sm">
            Complete events or courses to earn certificates. They will appear here once issued.
          </p>
        </div>
      )}
    </div>
  );
}

function CertificateCard({ cert }: { cert: Certificate }) {
  const eventLink = cert.event?.event_type === 'course'
    ? `/courses/${cert.event?.uuid}` // We might want slug here but UUID is guaranteed
    : `/events/${cert.event?.uuid}`;

  return (
    <Card className="flex flex-col h-full hover:shadow-md transition-shadow group">
      <div className="relative aspect-[1.414/1] bg-card border-b border-border/50 p-6 flex flex-col items-center justify-center text-center overflow-hidden">
        {/* Mini Certificate Preview */}
        <div className="absolute inset-0 bg-muted/30 opacity-0 group-hover:opacity-10 transition-opacity"></div>
        <div className="border-4 border-double border-border/50 absolute inset-3 pointer-events-none"></div>

        <ShieldCheck className="h-8 w-8 text-primary mb-2 opacity-80" />
        <h3 className="font-serif font-bold text-foreground text-sm line-clamp-2 px-2 leading-tight mb-1">
          {cert.event?.title || 'Certificate'}
        </h3>
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Certificate of Completion</p>
        <div className="mt-3 text-xs font-bold text-muted-foreground font-mono">
          {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString() : 'Pending'}
        </div>
      </div>

      <CardContent className="pt-4 pb-2 flex-grow">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Credits</span>
            <span className="font-medium">
              {cert.event?.cpd_credits && Number(cert.event.cpd_credits) > 0 ? (
                <>
                  {Number(cert.event.cpd_credits)} <Badge variant="outline" className="text-[10px] h-5 ml-1">{cert.event.cpd_type}</Badge>
                </>
              ) : (
                <span className="text-xs text-muted-foreground">No credits</span>
              )}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Type</span>
            <span className="font-medium truncate max-w-[140px] capitalize">{cert.event?.event_type || 'Event'}</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-2 gap-2">
        <Link to={eventLink} className="w-full">
          <Button variant="outline" className="w-full h-8 text-xs">View {cert.event?.event_type === 'course' ? 'Course' : 'Event'}</Button>
        </Link>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          disabled={!cert.download_url}
          onClick={() => cert.download_url && window.open(cert.download_url, '_blank')}
        >
          <Download className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
