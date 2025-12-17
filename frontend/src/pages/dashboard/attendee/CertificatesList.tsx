import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Download, ExternalLink, ShieldCheck, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { mockCertificates } from "@/lib/mock-data";

export function CertificatesList() {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredCerts = mockCertificates.filter(c => 
    c.eventTitle.toLowerCase().includes(searchTerm.toLowerCase()) || 
    c.organizer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <PageHeader 
        title="My Certificates" 
        description="Access and manage your professional credentials."
      />

      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="relative w-full sm:w-96">
           <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
           <Input 
             placeholder="Search by event or organizer..." 
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
            <CertificateCard key={cert.id} cert={cert} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 bg-gray-50 rounded-lg border border-dashed border-gray-200">
           <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
              <ShieldCheck className="h-8 w-8" />
           </div>
           <h3 className="text-lg font-medium text-gray-900 mb-1">No certificates found</h3>
           <p className="text-gray-500 text-center max-w-sm">
              Complete events to earn certificates. They will appear here once issued by the organizer.
           </p>
        </div>
      )}
    </div>
  );
}

function CertificateCard({ cert }: { cert: typeof mockCertificates[0] }) {
  return (
    <Card className="flex flex-col h-full hover:shadow-md transition-shadow group">
      <div className="relative aspect-[1.414/1] bg-white border-b border-gray-100 p-6 flex flex-col items-center justify-center text-center overflow-hidden">
         {/* Mini Certificate Preview */}
         <div className="absolute inset-0 bg-gray-50 opacity-0 group-hover:opacity-10 transition-opacity"></div>
         <div className="border-4 border-double border-gray-100 absolute inset-3 pointer-events-none"></div>
         
         <ShieldCheck className="h-8 w-8 text-blue-600 mb-2 opacity-80" />
         <h3 className="font-serif font-bold text-gray-900 text-sm line-clamp-2 px-2 leading-tight mb-1">
            {cert.eventTitle}
         </h3>
         <p className="text-[10px] text-gray-500 uppercase tracking-wider">Certificate of Completion</p>
         <div className="mt-3 text-xs font-bold text-gray-400 font-mono">
            {new Date(cert.issueDate).toLocaleDateString()}
         </div>
      </div>
      
      <CardContent className="pt-4 pb-2 flex-grow">
        <div className="space-y-2">
           <div className="flex justify-between text-sm">
              <span className="text-gray-500">Credits</span>
              <span className="font-medium">{cert.credits} {cert.creditType}</span>
           </div>
           <div className="flex justify-between text-sm">
              <span className="text-gray-500">Organizer</span>
              <span className="font-medium truncate max-w-[140px]" title={cert.organizer}>{cert.organizer}</span>
           </div>
        </div>
      </CardContent>
      
      <CardFooter className="pt-2 gap-2">
        <Link to={`/certificates/${cert.id}`} className="w-full">
           <Button variant="outline" className="w-full h-8 text-xs">View Details</Button>
        </Link>
        <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
           <Download className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
