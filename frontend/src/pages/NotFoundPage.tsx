import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Home, MapPinOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export const NotFoundPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { isAuthenticated } = useAuth();
    const homePath = isAuthenticated ? '/dashboard' : '/login';

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <div className="max-w-md w-full text-center space-y-6">
                <div className="h-16 w-16 mx-auto rounded-full bg-muted flex items-center justify-center text-muted-foreground">
                    <MapPinOff className="h-8 w-8" />
                </div>
                <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground tracking-wide uppercase">Error 404</p>
                    <h1 className="text-3xl font-bold text-foreground">Page not found</h1>
                    <p className="text-muted-foreground">
                        We couldn't find <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{location.pathname}</code>.
                        It may have moved, or the link is broken.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center">
                    <Button variant="outline" onClick={() => navigate(-1)}>
                        <ArrowLeft className="h-4 w-4 mr-2" /> Go back
                    </Button>
                    <Button asChild>
                        <Link to={homePath}>
                            <Home className="h-4 w-4 mr-2" /> {isAuthenticated ? 'Dashboard' : 'Sign in'}
                        </Link>
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default NotFoundPage;
