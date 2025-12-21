import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Home } from "lucide-react";
import notFoundImage from "@/assets/images/404-illustration.png";

export function NotFoundPage() {
    return (
        <div className="min-h-[80vh] flex items-center justify-center p-4">
            <div className="text-center max-w-md mx-auto">
                <div className="relative w-64 h-64 mx-auto mb-8 animate-in fade-in zoom-in duration-700">
                    <div className="absolute inset-0 bg-blue-100 rounded-full blur-3xl opacity-20 animate-pulse"></div>
                    <img
                        src={notFoundImage}
                        alt="404 Not Found"
                        className="w-full h-full object-contain relative z-10 drop-shadow-2xl"
                    />
                </div>

                <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl mb-4">
                    Page Not Found
                </h1>
                <p className="text-lg text-slate-600 mb-8">
                    Sorry, we couldn't find the page you're looking for. It might have been moved or doesn't exist.
                </p>

                <div className="flex items-center justify-center gap-4">
                    <Button variant="outline" onClick={() => window.history.back()}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
                    </Button>
                    <Button asChild>
                        <Link to="/">
                            <Home className="mr-2 h-4 w-4" /> Go Home
                        </Link>
                    </Button>
                </div>
            </div>
        </div>
    );
}
