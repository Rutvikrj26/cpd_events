import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Mail, ArrowRight } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function CheckEmailPage() {
    const location = useLocation();
    // Try to get email from state if it was passed during navigation
    const email = location.state?.email || "your email address";

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="flex justify-center mb-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Mail className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold">Check your email</CardTitle>
                    <CardDescription className="text-base mt-2">
                        We've sent a verification link to <span className="font-medium text-foreground">{email}</span>.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground text-center">
                        Click the link in the email to verify your account and continue to onboarding.
                        If you don't see it, check your spam folder.
                    </p>
                </CardContent>
                <CardFooter className="flex flex-col space-y-2">
                    <Button variant="outline" className="w-full" asChild>
                        <Link to="/login">
                            Return to Login
                        </Link>
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
