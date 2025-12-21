import React from "react";
import { Link } from "react-router-dom";
import { 
  BarChart3, 
  Award, 
  TrendingUp, 
  Target,
  Download,
  Calendar
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { mockCertificates } from "@/lib/mock-data";

export function CPDTracking() {
  // Mock calculations
  const totalCredits = mockCertificates.reduce((sum, c) => sum + c.credits, 0);
  const targetCredits = 50; // Annual target
  const progress = Math.min((totalCredits / targetCredits) * 100, 100);

  const creditsByType = mockCertificates.reduce((acc, c) => {
    acc[c.creditType] = (acc[c.creditType] || 0) + c.credits;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-8">
      <PageHeader 
        title="CPD Tracking" 
        description="Monitor your professional development progress."
        actions={
           <Button variant="outline">
              <Download className="mr-2 h-4 w-4" /> Export Report
           </Button>
        }
      />

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <Card className="bg-gradient-to-br from-blue-600 to-blue-700 text-white border-none shadow-lg">
            <CardHeader className="pb-2">
               <CardTitle className="text-blue-100 text-sm font-medium">Total Credits Earned</CardTitle>
            </CardHeader>
            <CardContent>
               <div className="text-4xl font-bold">{totalCredits}</div>
               <p className="text-blue-200 text-xs mt-1">This calendar year</p>
            </CardContent>
         </Card>

         <Card>
            <CardHeader className="pb-2">
               <CardTitle className="text-muted-foreground text-sm font-medium">Annual Goal</CardTitle>
            </CardHeader>
            <CardContent>
               <div className="flex justify-between items-end mb-2">
                  <div className="text-4xl font-bold text-foreground">{Math.round(progress)}%</div>
                  <div className="text-sm text-muted-foreground mb-1">{totalCredits} / {targetCredits} Credits</div>
               </div>
               <Progress value={progress} className="h-2" />
            </CardContent>
         </Card>

         <Card>
            <CardHeader className="pb-2">
               <CardTitle className="text-muted-foreground text-sm font-medium">Events Attended</CardTitle>
            </CardHeader>
            <CardContent>
               <div className="text-4xl font-bold text-foreground">{mockCertificates.length}</div>
               <p className="text-muted-foreground text-xs mt-1">Completion rate: 100%</p>
            </CardContent>
         </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
         {/* Breakdown Chart (Visual Mock) */}
         <div className="lg:col-span-2 space-y-6">
            <Card>
               <CardHeader>
                  <CardTitle>Credit Breakdown</CardTitle>
                  <CardDescription>Distribution of credits by category</CardDescription>
               </CardHeader>
               <CardContent>
                  <div className="space-y-4">
                     {Object.entries(creditsByType).map(([type, value]) => (
                        <div key={type} className="space-y-1">
                           <div className="flex justify-between text-sm">
                              <span className="font-medium">{type}</span>
                              <span className="text-muted-foreground">{value} Credits</span>
                           </div>
                           <Progress value={(value / totalCredits) * 100} className="h-2 bg-muted" />
                        </div>
                     ))}
                     {Object.keys(creditsByType).length === 0 && (
                        <div className="py-8 text-center text-muted-foreground">No credits recorded yet.</div>
                     )}
                  </div>
               </CardContent>
            </Card>

            <Card>
               <CardHeader>
                  <CardTitle>Recent Activity</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="space-y-4">
                     {mockCertificates.map((cert) => (
                        <div key={cert.id} className="flex items-start gap-4 pb-4 border-b border-gray-100 last:border-0 last:pb-0">
                           <div className="bg-blue-50 p-2 rounded text-blue-600 shrink-0">
                              <Award className="h-4 w-4" />
                           </div>
                           <div>
                              <p className="text-sm font-medium text-foreground">{cert.eventTitle}</p>
                              <div className="flex gap-2 text-xs text-muted-foreground mt-0.5">
                                 <span>{new Date(cert.issueDate).toLocaleDateString()}</span>
                                 <span>•</span>
                                 <span>{cert.credits} {cert.creditType}</span>
                              </div>
                           </div>
                        </div>
                     ))}
                  </div>
               </CardContent>
            </Card>
         </div>

         {/* Sidebar Goals */}
         <div className="space-y-6">
            <Card className="bg-gray-50 border-border">
               <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                     <Target className="h-4 w-4" /> Requirements
                  </CardTitle>
               </CardHeader>
               <CardContent className="space-y-4">
                  <div className="flex gap-3">
                     <div className="h-2 w-2 rounded-full bg-green-500 mt-1.5 shrink-0" />
                     <div className="text-sm">
                        <p className="font-medium text-foreground">Minimum 20 CME Credits</p>
                        <p className="text-muted-foreground">You have 15.5 CME credits.</p>
                     </div>
                  </div>
                  <div className="flex gap-3">
                     <div className="h-2 w-2 rounded-full bg-yellow-500 mt-1.5 shrink-0" />
                     <div className="text-sm">
                        <p className="font-medium text-foreground">Minimum 5 Ethics Credits</p>
                        <p className="text-muted-foreground">You have 2.0 Ethics credits.</p>
                     </div>
                  </div>
               </CardContent>
            </Card>
            
            <Card>
               <CardHeader>
                  <CardTitle className="text-base">Upcoming Deadline</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="flex items-center gap-3 text-sm text-gray-600">
                     <Calendar className="h-4 w-4" />
                     <span>Reporting Period ends <strong>Dec 31, 2024</strong></span>
                  </div>
               </CardContent>
            </Card>
         </div>
      </div>
    </div>
  );
}
