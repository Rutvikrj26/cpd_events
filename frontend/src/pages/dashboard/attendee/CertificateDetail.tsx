import React from "react";
import { useParams, Link } from "react-router-dom";
import { 
  Download, 
  Share2, 
  Linkedin, 
  CheckCircle, 
  ShieldCheck,
  Calendar,
  User
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { mockCertificates } from "@/lib/mock-data";

export function CertificateDetail() {
  const { id } = useParams<{ id: string }>();
  // In a real app, fetch by ID. For demo, just grab first or find.
  const cert = mockCertificates.find(c => c.id === id) || mockCertificates[0];

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <PageHeader 
        title="Certificate Details" 
        description="View and manage your earned credential."
        actions={
          <Link to="/certificates">
            <Button variant="outline">Back to Certificates</Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Column - Preview */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="overflow-hidden border-2 border-border shadow-lg">
            <div className="aspect-[1.414/1] bg-card relative p-8 md:p-12 flex flex-col items-center justify-center text-center border-b border-border">
               {/* Certificate Frame Decor */}
               <div className="absolute inset-4 border-4 border-double border-border pointer-events-none"></div>
               
               {/* Certificate Content Mockup */}
               <div className="relative z-10 space-y-6 max-w-lg">
                  <div className="h-16 w-16 mx-auto bg-info-subtle rounded-full flex items-center justify-center text-info mb-4">
                     <ShieldCheck className="h-10 w-10" />
                  </div>
                  
                  <h1 className="text-3xl font-serif text-foreground">Certificate of Completion</h1>
                  
                  <p className="text-muted-foreground italic">This certifies that</p>
                  
                  <h2 className="text-2xl font-bold text-foreground border-b border-border pb-2 inline-block min-w-[200px]">
                    Jane Doe
                  </h2>
                  
                  <p className="text-muted-foreground">has successfully completed the course</p>
                  
                  <h3 className="text-xl font-bold text-info">
                    {cert.eventTitle}
                  </h3>
                  
                  <div className="text-sm text-muted-foreground pt-4">
                    <p>Awarded on {new Date(cert.issueDate).toLocaleDateString()}</p>
                    <p>{cert.credits} {cert.creditType} Credits</p>
                  </div>
                  
                  <div className="pt-8 flex justify-between items-end w-full gap-8 text-xs text-muted-foreground font-serif">
                     <div className="text-center">
                        <div className="w-32 border-t border-border pt-1">Signature</div>
                     </div>
                     <div className="text-center">
                        <div className="w-32 border-t border-border pt-1">{cert.organizer}</div>
                     </div>
                  </div>
               </div>
            </div>
          </Card>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg">
              <Download className="mr-2 h-4 w-4" /> Download PDF
            </Button>
            <Button size="lg" variant="outline">
              <Share2 className="mr-2 h-4 w-4" /> Share Link
            </Button>
            <Button size="lg" variant="outline" className="text-info border-info bg-info-subtle hover:bg-info-subtle/80">
              <Linkedin className="mr-2 h-4 w-4" /> Add to LinkedIn
            </Button>
          </div>
        </div>

        {/* Sidebar - Meta & Verification */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Credential Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-success shrink-0 mt-0.5" />
                <div>
                   <p className="font-medium text-foreground">Valid Certificate</p>
                   <p className="text-sm text-muted-foreground">Issued by {cert.organizer}</p>
                </div>
              </div>
              
              <div className="border-t border-border my-2"></div>
              
              <div className="space-y-3 text-sm">
                 <div className="flex justify-between">
                    <span className="text-muted-foreground">Issue Date</span>
                    <span className="font-medium text-foreground">{new Date(cert.issueDate).toLocaleDateString()}</span>
                 </div>
                 <div className="flex justify-between">
                    <span className="text-muted-foreground">Credential ID</span>
                    <span className="font-medium text-foreground font-mono text-xs">{cert.id.toUpperCase()}</span>
                 </div>
                 <div className="flex justify-between">
                    <span className="text-muted-foreground">Credits</span>
                    <span className="font-medium text-foreground">{cert.credits} {cert.creditType}</span>
                 </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">About the Event</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
               <h4 className="font-medium text-foreground">{cert.eventTitle}</h4>
               <Link to={`/events/${cert.eventId}`}>
                 <Button variant="link" className="p-0 h-auto text-info">View Event Details</Button>
               </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
