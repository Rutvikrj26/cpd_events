import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Home, Search } from "lucide-react";

export function NotFoundPage() {
    return (
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-background relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-gradient-to-bl from-primary/5 to-transparent rounded-full blur-3xl -z-10" />
            <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-gradient-to-tr from-accent/5 to-transparent rounded-full blur-3xl -z-10" />

            <div className="text-center max-w-lg mx-auto">
                {/* 404 Number Display */}
                <div className="relative mb-8">
                    <div className="text-[150px] md:text-[200px] font-extrabold text-primary/10 leading-none select-none animate-in fade-in duration-700">
                        404
                    </div>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="h-20 w-20 rounded-2xl bg-primary/10 flex items-center justify-center animate-in zoom-in duration-500 delay-200">
                            <Search className="h-10 w-10 text-primary" />
                        </div>
                    </div>
                </div>

                <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground mb-4 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-300">
                    Page Not Found
                </h1>
                <p className="text-lg text-muted-foreground mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-400">
                    Sorry, we couldn't find the page you're looking for. It might have been moved or doesn't exist.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-500">
                    <Button variant="outline" size="lg" onClick={() => window.history.back()}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
                    </Button>
                    <Button size="lg" className="glow-primary" asChild>
                        <Link to="/">
                            <Home className="mr-2 h-4 w-4" /> Go Home
                        </Link>
                    </Button>
                </div>

                {/* Helpful links */}
                <div className="mt-12 pt-8 border-t border-border">
                    <p className="text-sm text-muted-foreground mb-4">
                        Here are some helpful links:
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
                        <Link to="/features" className="text-primary hover:underline">
                            Features
                        </Link>
                        <span className="text-border">•</span>
                        <Link to="/pricing" className="text-primary hover:underline">
                            Pricing
                        </Link>
                        <span className="text-border">•</span>
                        <Link to="/faq" className="text-primary hover:underline">
                            FAQ
                        </Link>
                        <span className="text-border">•</span>
                        <Link to="/contact" className="text-primary hover:underline">
                            Contact
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
