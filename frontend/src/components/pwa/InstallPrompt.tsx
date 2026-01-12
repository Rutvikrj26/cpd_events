import { useEffect, useState } from "react";
import { X, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const wasDismissedRecently = () => {
    if (typeof window === "undefined") return false;
    const dismissed = localStorage.getItem("installPromptDismissed");
    if (!dismissed) return false;
    const dismissedTime = parseInt(dismissed, 10);
    if (Number.isNaN(dismissedTime)) return false;
    const sevenDays = 7 * 24 * 60 * 60 * 1000;
    return Date.now() - dismissedTime < sevenDays;
};

export function InstallPrompt() {
    const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [showPrompt, setShowPrompt] = useState(false);
    const isDev = import.meta.env.DEV;

    useEffect(() => {
        const handler = (e: Event) => {
            // Prevent the mini-infobar from appearing on mobile
            e.preventDefault();
            // Stash the event so it can be triggered later
            setDeferredPrompt(e as BeforeInstallPromptEvent);
            // Show our custom install prompt
            if (!wasDismissedRecently()) {
                setShowPrompt(true);
            }
        };

        window.addEventListener("beforeinstallprompt", handler);

        return () => window.removeEventListener("beforeinstallprompt", handler);
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) return;

        // Show the install prompt
        await deferredPrompt.prompt();

        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;

        if (isDev) {
            console.log(`Install prompt ${outcome === "accepted" ? "accepted" : "dismissed"}`);
        }

        // Clear the deferredPrompt
        setDeferredPrompt(null);
        setShowPrompt(false);
    };

    const handleDismiss = () => {
        setShowPrompt(false);
        // Store dismissal in localStorage to not show again for a while
        localStorage.setItem("installPromptDismissed", Date.now().toString());
    };

    if (!showPrompt || !deferredPrompt) return null;

    return (
        <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:right-4 md:w-96">
            <Card className="p-4 shadow-lg border-2 border-primary/20 bg-card/95 backdrop-blur-sm">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Download className="h-5 w-5 text-primary" />
                        </div>
                    </div>

                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm mb-1">Install CPD Events</h3>
                        <p className="text-sm text-muted-foreground mb-3">
                            Install our app for quick access and offline functionality
                        </p>

                        <div className="flex gap-2">
                            <Button
                                onClick={handleInstall}
                                size="sm"
                                className="flex-1"
                            >
                                Install
                            </Button>
                            <Button
                                onClick={handleDismiss}
                                size="sm"
                                variant="outline"
                            >
                                Not now
                            </Button>
                        </div>
                    </div>

                    <button
                        onClick={handleDismiss}
                        className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                        aria-label="Dismiss install prompt"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
            </Card>
        </div>
    );
}
