import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const isDev = import.meta.env.DEV;

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorInfo: null,
        };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // Log errors in development for debugging
        if (isDev) {
            console.error("Uncaught error:", error, errorInfo);
        }

        // In production, you might want to send to error tracking service
        // Example: errorTrackingService.logError(error, errorInfo);

        this.setState({
            error,
            errorInfo,
        });
    }

    private handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });
    };

    private handleReload = () => {
        window.location.reload();
    };

    private handleGoHome = () => {
        window.location.href = "/";
    };

    public render() {
        if (this.state.hasError) {
            // Custom fallback if provided
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default error UI
            return (
                <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
                    <Card className="max-w-2xl w-full p-8">
                        <div className="flex flex-col items-center text-center space-y-6">
                            <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
                                <AlertCircle className="h-8 w-8 text-destructive" />
                            </div>

                            <div className="space-y-2">
                                <h1 className="text-2xl font-bold text-foreground">
                                    Something went wrong
                                </h1>
                                <p className="text-muted-foreground">
                                    We're sorry, but something unexpected happened. The error has been logged and we'll look into it.
                                </p>
                            </div>

                            {isDev && this.state.error && (
                                <details className="w-full text-left">
                                    <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground mb-2">
                                        Error Details (Development Only)
                                    </summary>
                                    <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                                        <p className="text-xs font-mono text-destructive mb-2">
                                            {this.state.error.toString()}
                                        </p>
                                        {this.state.errorInfo && (
                                            <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                                                {this.state.errorInfo.componentStack}
                                            </pre>
                                        )}
                                    </div>
                                </details>
                            )}

                            <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                                <Button
                                    onClick={this.handleReset}
                                    variant="default"
                                    className="flex items-center gap-2"
                                >
                                    <RefreshCw className="h-4 w-4" />
                                    Try Again
                                </Button>
                                <Button
                                    onClick={this.handleReload}
                                    variant="outline"
                                    className="flex items-center gap-2"
                                >
                                    <RefreshCw className="h-4 w-4" />
                                    Reload Page
                                </Button>
                                <Button
                                    onClick={this.handleGoHome}
                                    variant="outline"
                                    className="flex items-center gap-2"
                                >
                                    <Home className="h-4 w-4" />
                                    Go Home
                                </Button>
                            </div>
                        </div>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}
