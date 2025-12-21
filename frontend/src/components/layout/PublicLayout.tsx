import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "../ui/button";
import { Menu, X, Layout, User, LogOut } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function PublicLayout({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen flex flex-col bg-background font-sans anti-aliased">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <Link to="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                  <Layout className="h-5 w-5" />
                </div>
                <span className="text-xl font-bold tracking-tight text-foreground">CPD Events</span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-6">
              <Link
                to="/events/browse"
                className={`text-sm font-medium transition-colors hover:text-blue-600 ${isActive('/events/browse') ? 'text-blue-600' : 'text-gray-600'}`}
              >
                Browse Events
              </Link>
              <Link
                to="/pricing"
                className={`text-sm font-medium transition-colors hover:text-blue-600 ${isActive('/pricing') ? 'text-blue-600' : 'text-gray-600'}`}
              >
                Pricing
              </Link>

              {/* Auth-aware buttons */}
              <div className="flex items-center gap-2 ml-4">
                {isAuthenticated ? (
                  <>
                    <Link to="/dashboard">
                      <Button variant="ghost" size="sm" className="text-gray-600 hover:text-foreground">
                        Dashboard
                      </Button>
                    </Link>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm" className="flex items-center gap-2">
                          <User className="h-4 w-4" />
                          <span className="max-w-[100px] truncate">{user?.full_name || user?.email || 'Account'}</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuLabel>My Account</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                          <Link to="/profile">Profile</Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link to="/settings">Settings</Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={logout} className="text-red-600">
                          <LogOut className="h-4 w-4 mr-2" />
                          Sign out
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </>
                ) : (
                  <>
                    <Link to="/login">
                      <Button variant="ghost" size="sm" className="text-gray-600 hover:text-foreground">
                        Log in
                      </Button>
                    </Link>
                    <Link to="/signup">
                      <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                        Sign up
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </nav>

            {/* Mobile Menu Button */}
            <button
              className="flex items-center justify-center p-2 rounded-md text-gray-600 md:hidden hover:bg-muted"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-border bg-card px-4 py-4 shadow-lg">
            <nav className="flex flex-col gap-4">
              <Link to="/events/browse" className="text-base font-medium text-gray-600 hover:text-blue-600">
                Browse Events
              </Link>
              <Link to="/pricing" className="text-base font-medium text-gray-600 hover:text-blue-600">
                Pricing
              </Link>
              <div className="flex flex-col gap-2 pt-4 border-t border-gray-100">
                {isAuthenticated ? (
                  <>
                    <Link to="/dashboard" className="w-full">
                      <Button variant="outline" className="w-full justify-center">Dashboard</Button>
                    </Link>
                    <Button variant="ghost" className="w-full justify-center text-red-600" onClick={logout}>
                      Sign out
                    </Button>
                  </>
                ) : (
                  <>
                    <Link to="/login" className="w-full">
                      <Button variant="outline" className="w-full justify-center">Log in</Button>
                    </Link>
                    <Link to="/signup" className="w-full">
                      <Button className="w-full justify-center bg-blue-600 hover:bg-blue-700">Sign up</Button>
                    </Link>
                  </>
                )}
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-gray-50">
        <div className="container mx-auto px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Platform</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="/events/browse" className="text-sm text-gray-600 hover:text-foreground">Browse Events</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-foreground">For Organizers</Link></li>
                <li><Link to="/pricing" className="text-sm text-gray-600 hover:text-foreground">Pricing</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Support</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="#" className="text-sm text-gray-600 hover:text-foreground">Help Center</Link></li>
                <li><Link to="/contact" className="text-sm text-gray-600 hover:text-foreground">Contact Us</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-foreground">Status</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Legal</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="#" className="text-sm text-gray-600 hover:text-foreground">Privacy Policy</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-foreground">Terms of Service</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-12 border-t border-border pt-8">
            <p className="text-sm text-muted-foreground">&copy; 2024 CPD Events Management. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

