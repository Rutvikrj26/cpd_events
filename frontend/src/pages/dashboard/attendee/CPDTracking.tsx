import React, { useState, useEffect } from "react";
import {
   Target,
   Download,
   Calendar,
   Plus,
   ChevronDown,
   Loader2,
   Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import {
   DropdownMenu,
   DropdownMenuContent,
   DropdownMenuItem,
   DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
   Dialog,
   DialogContent,
   DialogDescription,
   DialogFooter,
   DialogHeader,
   DialogTitle,
   DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
   Select,
   SelectContent,
   SelectItem,
   SelectTrigger,
   SelectValue,
} from "@/components/ui/select";
import { getCPDProgress, downloadCPDReport, createCPDRequirement, deleteCPDRequirement } from "@/api/cpd";
import { CPDProgress, CPDRequirement, CPDRequirementCreate } from "@/api/cpd/types";
import { toast } from "sonner";

export function CPDTracking() {
   const [progress, setProgress] = useState<CPDProgress | null>(null);
   const [loading, setLoading] = useState(true);
   const [exporting, setExporting] = useState(false);
   const [dialogOpen, setDialogOpen] = useState(false);
   const [saving, setSaving] = useState(false);

   // Form state
   const [formData, setFormData] = useState<CPDRequirementCreate>({
      cpd_type: "general",
      cpd_type_display: "General CPD",
      annual_requirement: 50,
      period_type: "calendar_year",
   });

   useEffect(() => {
      loadProgress();
   }, []);

   const loadProgress = async () => {
      try {
         const data = await getCPDProgress();
         setProgress(data);
      } catch (error) {
         console.error("Failed to load CPD progress:", error);
      } finally {
         setLoading(false);
      }
   };

   const handleExport = async (format: "json" | "csv" | "txt") => {
      setExporting(true);
      try {
         await downloadCPDReport({ export_format: format });
         toast.success("Report downloaded successfully");
      } catch (error) {
         console.error("Failed to export report:", error);
         toast.error("Failed to export report");
      } finally {
         setExporting(false);
      }
   };

   const handleAddRequirement = async () => {
      setSaving(true);
      try {
         await createCPDRequirement(formData);
         toast.success("Requirement added successfully");
         setDialogOpen(false);
         setFormData({
            cpd_type: "general",
            cpd_type_display: "General CPD",
            annual_requirement: 50,
            period_type: "calendar_year",
         });
         loadProgress();
      } catch (error) {
         console.error("Failed to add requirement:", error);
         toast.error("Failed to add requirement");
      } finally {
         setSaving(false);
      }
   };

   const handleDeleteRequirement = async (uuid: string) => {
      if (!confirm("Are you sure you want to delete this requirement?")) return;
      try {
         await deleteCPDRequirement(uuid);
         toast.success("Requirement deleted");
         loadProgress();
      } catch (error) {
         console.error("Failed to delete requirement:", error);
         toast.error("Failed to delete requirement");
      }
   };

   if (loading) {
      return (
         <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
         </div>
      );
   }

   const requirements = progress?.requirements || [];
   const totalCredits = progress?.total_credits_earned || 0;
   const totalRequired = requirements.reduce((sum, r) => sum + r.annual_requirement, 0);
   const overallProgress = totalRequired > 0 ? Math.min((totalCredits / totalRequired) * 100, 100) : 0;

   return (
      <div className="space-y-8">
         <PageHeader
            title="CPD Tracking"
            description="Monitor your professional development progress."
            actions={
               <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                     <Button variant="outline" disabled={exporting}>
                        {exporting ? (
                           <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                           <Download className="mr-2 h-4 w-4" />
                        )}
                        Export Report
                        <ChevronDown className="ml-2 h-4 w-4" />
                     </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                     <DropdownMenuItem onClick={() => handleExport("txt")}>
                        Plain Text (.txt)
                     </DropdownMenuItem>
                     <DropdownMenuItem onClick={() => handleExport("csv")}>
                        Spreadsheet (.csv)
                     </DropdownMenuItem>
                     <DropdownMenuItem onClick={() => handleExport("json")}>
                        JSON (.json)
                     </DropdownMenuItem>
                  </DropdownMenuContent>
               </DropdownMenu>
            }
         />

         {/* Hero Stats */}
         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="bg-gradient-to-br from-blue-600 to-blue-700 text-white border-none shadow-lg">
               <CardHeader className="pb-2">
                  <CardTitle className="text-blue-100 text-sm font-medium">
                     Total Credits Earned
                  </CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-4xl font-bold">{totalCredits}</div>
                  <p className="text-blue-200 text-xs mt-1">This period</p>
               </CardContent>
            </Card>

            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-muted-foreground text-sm font-medium">
                     Overall Progress
                  </CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="flex justify-between items-end mb-2">
                     <div className="text-4xl font-bold text-foreground">
                        {Math.round(overallProgress)}%
                     </div>
                     <div className="text-sm text-muted-foreground mb-1">
                        {totalCredits} / {totalRequired} Credits
                     </div>
                  </div>
                  <Progress value={overallProgress} className="h-2" />
               </CardContent>
            </Card>

            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-muted-foreground text-sm font-medium">
                     Requirements
                  </CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-4xl font-bold text-foreground">
                     {progress?.completed_requirements || 0}/{progress?.total_requirements || 0}
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">Completed</p>
               </CardContent>
            </Card>
         </div>

         <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Requirements Progress */}
            <div className="lg:col-span-2 space-y-6">
               <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                     <div>
                        <CardTitle>Credit Requirements</CardTitle>
                        <CardDescription>Progress toward each requirement</CardDescription>
                     </div>
                     <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                        <DialogTrigger asChild>
                           <Button size="sm">
                              <Plus className="mr-2 h-4 w-4" />
                              Add Requirement
                           </Button>
                        </DialogTrigger>
                        <DialogContent>
                           <DialogHeader>
                              <DialogTitle>Add CPD Requirement</DialogTitle>
                              <DialogDescription>
                                 Set up a new professional development requirement to track.
                              </DialogDescription>
                           </DialogHeader>
                           <div className="space-y-4 py-4">
                              <div className="space-y-2">
                                 <Label htmlFor="cpd_type_display">Requirement Name</Label>
                                 <Input
                                    id="cpd_type_display"
                                    placeholder="e.g., General CPD, Ethics, Clinical"
                                    value={formData.cpd_type_display || ""}
                                    onChange={(e) =>
                                       setFormData({
                                          ...formData,
                                          cpd_type_display: e.target.value,
                                          cpd_type: e.target.value.toLowerCase().replace(/\s+/g, "_"),
                                       })
                                    }
                                 />
                              </div>
                              <div className="space-y-2">
                                 <Label htmlFor="annual_requirement">Annual Credits Required</Label>
                                 <Input
                                    id="annual_requirement"
                                    type="number"
                                    min="1"
                                    placeholder="50"
                                    value={formData.annual_requirement}
                                    onChange={(e) =>
                                       setFormData({
                                          ...formData,
                                          annual_requirement: parseFloat(e.target.value) || 0,
                                       })
                                    }
                                 />
                              </div>
                              <div className="space-y-2">
                                 <Label htmlFor="period_type">Reporting Period</Label>
                                 <Select
                                    value={formData.period_type}
                                    onValueChange={(value: "calendar_year" | "fiscal_year" | "rolling_12") =>
                                       setFormData({ ...formData, period_type: value })
                                    }
                                 >
                                    <SelectTrigger>
                                       <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                       <SelectItem value="calendar_year">Calendar Year (Jan-Dec)</SelectItem>
                                       <SelectItem value="fiscal_year">Fiscal Year</SelectItem>
                                       <SelectItem value="rolling_12">Rolling 12 Months</SelectItem>
                                    </SelectContent>
                                 </Select>
                              </div>
                              <div className="space-y-2">
                                 <Label htmlFor="licensing_body">Licensing Body (Optional)</Label>
                                 <Input
                                    id="licensing_body"
                                    placeholder="e.g., State Medical Board"
                                    value={formData.licensing_body || ""}
                                    onChange={(e) =>
                                       setFormData({ ...formData, licensing_body: e.target.value })
                                    }
                                 />
                              </div>
                              <div className="space-y-2">
                                 <Label htmlFor="license_number">License Number (Optional)</Label>
                                 <Input
                                    id="license_number"
                                    placeholder="Your license number"
                                    value={formData.license_number || ""}
                                    onChange={(e) =>
                                       setFormData({ ...formData, license_number: e.target.value })
                                    }
                                 />
                              </div>
                           </div>
                           <DialogFooter>
                              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                                 Cancel
                              </Button>
                              <Button onClick={handleAddRequirement} disabled={saving}>
                                 {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                 Add Requirement
                              </Button>
                           </DialogFooter>
                        </DialogContent>
                     </Dialog>
                  </CardHeader>
                  <CardContent>
                     <div className="space-y-6">
                        {requirements.length === 0 ? (
                           <div className="py-8 text-center text-muted-foreground">
                              <Target className="h-12 w-12 mx-auto mb-3 opacity-50" />
                              <p>No CPD requirements set up yet.</p>
                              <p className="text-sm mt-1">
                                 Click "Add Requirement" to start tracking your professional development.
                              </p>
                           </div>
                        ) : (
                           requirements.map((req) => (
                              <RequirementCard
                                 key={req.uuid}
                                 requirement={req}
                                 onDelete={() => handleDeleteRequirement(req.uuid)}
                              />
                           ))
                        )}
                     </div>
                  </CardContent>
               </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
               {requirements.length > 0 && requirements[0].period_bounds && (
                  <Card>
                     <CardHeader>
                        <CardTitle className="text-base">Reporting Period</CardTitle>
                     </CardHeader>
                     <CardContent>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                           <Calendar className="h-4 w-4" />
                           <span>
                              {new Date(requirements[0].period_bounds.start).toLocaleDateString()} —{" "}
                              <strong>
                                 {new Date(requirements[0].period_bounds.end).toLocaleDateString()}
                              </strong>
                           </span>
                        </div>
                     </CardContent>
                  </Card>
               )}
            </div>
         </div>
      </div>
   );
}

function RequirementCard({
   requirement,
   onDelete,
}: {
   requirement: CPDRequirement;
   onDelete: () => void;
}) {
   const earned = parseFloat(requirement.earned_credits);
   const required = requirement.annual_requirement;
   const percent = requirement.completion_percent;
   const isComplete = percent >= 100;

   return (
      <div className="p-4 rounded-lg border bg-card">
         <div className="flex items-start justify-between mb-3">
            <div>
               <h4 className="font-medium text-foreground">
                  {requirement.cpd_type_display || requirement.cpd_type}
               </h4>
               {requirement.licensing_body && (
                  <p className="text-xs text-muted-foreground">
                     {requirement.licensing_body}
                     {requirement.license_number && ` • ${requirement.license_number}`}
                  </p>
               )}
            </div>
            <div className="flex items-center gap-3">
               <div className="text-right">
                  <div className="text-lg font-semibold">
                     {earned} / {required}
                  </div>
                  <div className="text-xs text-muted-foreground">credits</div>
               </div>
               <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={onDelete}
               >
                  <Trash2 className="h-4 w-4" />
               </Button>
            </div>
         </div>
         <Progress
            value={percent}
            className={`h-2 ${isComplete ? "[&>div]:bg-green-500" : ""}`}
         />
         <div className="flex justify-between mt-2 text-xs text-muted-foreground">
            <span>{percent}% complete</span>
            {!isComplete && <span>{requirement.credits_remaining} remaining</span>}
            {isComplete && <span className="text-green-600 font-medium">Complete ✓</span>}
         </div>
      </div>
   );
}
