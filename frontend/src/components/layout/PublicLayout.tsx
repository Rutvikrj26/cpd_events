import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "../ui/button";
import { Menu, X, Layout } from "lucide-react";

export function PublicLayout({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <Link to="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                  <Layout className="h-5 w-5" />
                </div>
                <span className="text-xl font-bold tracking-tight text-gray-900">CPD Events</span>
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
              <div className="flex items-center gap-2 ml-4">
                <Link to="/login">
                  <Button variant="ghost" size="sm" className="text-gray-600 hover:text-gray-900">
                    Log in
                  </Button>
                </Link>
                <Link to="/signup">
                  <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                    Sign up
                  </Button>
                </Link>
              </div>
            </nav>

            {/* Mobile Menu Button */}
            <button
              className="flex items-center justify-center p-2 rounded-md text-gray-600 md:hidden hover:bg-gray-100"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white px-4 py-4 shadow-lg">
            <nav className="flex flex-col gap-4">
              <Link to="/events/browse" className="text-base font-medium text-gray-600 hover:text-blue-600">
                Browse Events
              </Link>
              <Link to="/pricing" className="text-base font-medium text-gray-600 hover:text-blue-600">
                Pricing
              </Link>
              <div className="flex flex-col gap-2 pt-4 border-t border-gray-100">
                <Link to="/login" className="w-full">
                  <Button variant="outline" className="w-full justify-center">Log in</Button>
                </Link>
                <Link to="/signup" className="w-full">
                  <Button className="w-full justify-center bg-blue-600 hover:bg-blue-700">Sign up</Button>
                </Link>
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
      <footer className="border-t border-gray-200 bg-gray-50">
        <div className="container mx-auto px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Platform</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="/events/browse" className="text-sm text-gray-600 hover:text-gray-900">Browse Events</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">For Organizers</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Support</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Help Center</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Contact Us</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Status</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Legal</h3>
              <ul className="mt-4 space-y-3">
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Privacy Policy</Link></li>
                <li><Link to="#" className="text-sm text-gray-600 hover:text-gray-900">Terms of Service</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-12 border-t border-gray-200 pt-8">
            <p className="text-sm text-gray-500">&copy; 2024 CPD Events Management. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
