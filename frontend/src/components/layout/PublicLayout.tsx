import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "../ui/button";
import {
  Menu,
  X,
  Layout,
  User,
  LogOut,
  ChevronDown,
  Video,
  Award,
  Zap,
  HelpCircle,
  Mail,
  FileText,
  Building2,
  ArrowRight
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { cn } from "@/lib/utils";

export function PublicLayout({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const [mobileSubmenu, setMobileSubmenu] = React.useState<string | null>(null);
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;
  const isActivePrefix = (prefix: string) => location.pathname.startsWith(prefix);

  return (
    <div className="min-h-screen flex flex-col bg-background font-sans antialiased">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-sm group-hover:shadow-md transition-all duration-300">
                <Layout className="h-5 w-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold tracking-tight gradient-text leading-tight">CPD Events</span>
                <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider hidden sm:block">Professional Development</span>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {/* Main Nav Links with Dropdowns */}
              <NavigationMenu>
                <NavigationMenuList>
                  {/* Features Dropdown */}
                  <NavigationMenuItem>
                    <NavigationMenuTrigger className="bg-transparent text-muted-foreground hover:text-foreground data-[state=open]:text-foreground h-9 px-3">
                      Features
                    </NavigationMenuTrigger>
                    <NavigationMenuContent>
                      <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-2">
                        <ListItem
                          href="/features"
                          title="Platform Overview"
                          icon={<Zap className="h-5 w-5" />}
                        >
                          Everything you need to manage CPD events
                        </ListItem>
                        <ListItem
                          href="/features/zoom"
                          title="Zoom Integration"
                          icon={<Video className="h-5 w-5" />}
                        >
                          Automatic attendance tracking via webhooks
                        </ListItem>
                        <ListItem
                          href="/features/certificates"
                          title="Certificates"
                          icon={<Award className="h-5 w-5" />}
                        >
                          Automated PDF generation with verification
                        </ListItem>
                        <ListItem
                          href="/features/teams"
                          title="Team Management"
                          icon={<Building2 className="h-5 w-5" />}
                        >
                          Organizations with roles and permissions
                        </ListItem>
                      </ul>
                    </NavigationMenuContent>
                  </NavigationMenuItem>

                  {/* Pricing Link */}
                  <NavigationMenuItem>
                    <Link
                      to="/pricing"
                      className={cn(
                        "group inline-flex h-9 w-max items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors hover:bg-muted hover:text-foreground focus:bg-muted focus:text-foreground focus:outline-none",
                        isActive('/pricing') ? 'text-foreground bg-muted' : 'text-muted-foreground'
                      )}
                    >
                      Pricing
                    </Link>
                  </NavigationMenuItem>

                  {/* Resources Dropdown */}
                  <NavigationMenuItem>
                    <NavigationMenuTrigger className="bg-transparent text-muted-foreground hover:text-foreground data-[state=open]:text-foreground h-9 px-3">
                      Resources
                    </NavigationMenuTrigger>
                    <NavigationMenuContent>
                      <ul className="grid w-[350px] gap-3 p-4">
                        <ListItem
                          href="/faq"
                          title="FAQ"
                          icon={<HelpCircle className="h-5 w-5" />}
                        >
                          Frequently asked questions
                        </ListItem>
                        <ListItem
                          href="/contact"
                          title="Contact Us"
                          icon={<Mail className="h-5 w-5" />}
                        >
                          Get in touch with our team
                        </ListItem>
                        <ListItem
                          href="/about"
                          title="About"
                          icon={<FileText className="h-5 w-5" />}
                        >
                          Learn more about CPD Events
                        </ListItem>
                      </ul>
                    </NavigationMenuContent>
                  </NavigationMenuItem>
                </NavigationMenuList>
              </NavigationMenu>

              {/* Divider */}
              <div className="h-6 w-px bg-border mx-3" />

              {/* Auth Section */}
              <div className="flex items-center gap-2">
                {isAuthenticated ? (
                  <>
                    <Link to="/dashboard">
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground font-medium">
                        Dashboard
                      </Button>
                    </Link>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm" className="flex items-center gap-2 border-border/60 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200">
                          <div className="h-6 w-6 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white text-xs font-medium">
                            {(user?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
                          </div>
                          <span className="max-w-[80px] truncate text-sm">{user?.full_name?.split(' ')[0] || 'Account'}</span>
                          <ChevronDown className="h-3 w-3 text-muted-foreground" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel className="font-normal">
                          <div className="flex flex-col space-y-1">
                            <p className="text-sm font-medium leading-none">{user?.full_name || 'User'}</p>
                            <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                          </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                          <Link to="/dashboard" className="cursor-pointer">
                            <Layout className="h-4 w-4 mr-2" />
                            Dashboard
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link to="/profile" className="cursor-pointer">
                            <User className="h-4 w-4 mr-2" />
                            Profile
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive cursor-pointer">
                          <LogOut className="h-4 w-4 mr-2" />
                          Sign out
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </>
                ) : (
                  <>
                    <Link to="/login">
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground font-medium">
                        Log in
                      </Button>
                    </Link>
                    <Link to="/signup">
                      <Button size="sm" className="font-medium shadow-sm hover:shadow-md transition-all duration-200 glow-primary">
                        Get Started
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </nav>

            {/* Mobile Menu Button */}
            <button
              className="flex items-center justify-center h-10 w-10 rounded-lg text-muted-foreground md:hidden hover:bg-muted hover:text-foreground transition-colors"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-border bg-card/95 backdrop-blur-xl px-4 py-6 shadow-lg animate-fade-in-down">
            <nav className="flex flex-col gap-2">
              {/* Features Accordion */}
              <div>
                <button
                  className="w-full flex items-center justify-between px-4 py-3 text-base font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
                  onClick={() => setMobileSubmenu(mobileSubmenu === 'features' ? null : 'features')}
                >
                  Features
                  <ChevronDown className={cn("h-4 w-4 transition-transform", mobileSubmenu === 'features' && "rotate-180")} />
                </button>
                {mobileSubmenu === 'features' && (
                  <div className="ml-4 mt-1 flex flex-col gap-1">
                    <Link
                      to="/features"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <Zap className="h-4 w-4" /> Platform Overview
                    </Link>
                    <Link
                      to="/features/zoom"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <Video className="h-4 w-4" /> Zoom Integration
                    </Link>
                    <Link
                      to="/features/certificates"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <Award className="h-4 w-4" /> Certificates
                    </Link>
                  </div>
                )}
              </div>

              <Link
                to="/pricing"
                className="px-4 py-3 text-base font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Pricing
              </Link>

              {/* Resources Accordion */}
              <div>
                <button
                  className="w-full flex items-center justify-between px-4 py-3 text-base font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
                  onClick={() => setMobileSubmenu(mobileSubmenu === 'resources' ? null : 'resources')}
                >
                  Resources
                  <ChevronDown className={cn("h-4 w-4 transition-transform", mobileSubmenu === 'resources' && "rotate-180")} />
                </button>
                {mobileSubmenu === 'resources' && (
                  <div className="ml-4 mt-1 flex flex-col gap-1">
                    <Link
                      to="/faq"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <HelpCircle className="h-4 w-4" /> FAQ
                    </Link>
                    <Link
                      to="/contact"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <Mail className="h-4 w-4" /> Contact Us
                    </Link>
                    <Link
                      to="/about"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <FileText className="h-4 w-4" /> About
                    </Link>
                  </div>
                )}
              </div>

              <div className="h-px bg-border my-4" />

              <div className="flex flex-col gap-3">
                {isAuthenticated ? (
                  <>
                    <Link to="/dashboard" className="w-full" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="outline" className="w-full justify-center h-11">Dashboard</Button>
                    </Link>
                    <Button variant="ghost" className="w-full justify-center h-11 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => { logout(); setIsMobileMenuOpen(false); }}>
                      <LogOut className="h-4 w-4 mr-2" />
                      Sign out
                    </Button>
                  </>
                ) : (
                  <>
                    <Link to="/login" className="w-full" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="outline" className="w-full justify-center h-11">Log in</Button>
                    </Link>
                    <Link to="/signup" className="w-full" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button className="w-full justify-center h-11">Get Started</Button>
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
      <footer className="border-t border-border bg-muted/30">
        <div className="container mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4 lg:grid-cols-5">
            {/* Brand Column */}
            <div className="col-span-2 lg:col-span-2">
              <Link to="/" className="flex items-center gap-3 mb-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white">
                  <Layout className="h-5 w-5" />
                </div>
                <span className="text-lg font-bold gradient-text">CPD Events</span>
              </Link>
              <p className="text-sm text-muted-foreground max-w-xs mb-6">
                The all-in-one platform for managing professional development events, tracking attendance, and issuing verifiable certificates.
              </p>
              {/* Social Links */}
              <div className="flex items-center gap-3">
                <Link to="#" className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors">
                  <span className="sr-only">Twitter</span>
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84"></path></svg>
                </Link>
                <Link to="#" className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors">
                  <span className="sr-only">LinkedIn</span>
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"></path></svg>
                </Link>
              </div>
            </div>

            {/* Platform Links */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-4">Platform</h3>
              <ul className="space-y-3">
                <li><Link to="/features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</Link></li>
                <li><Link to="/features/zoom" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Zoom Integration</Link></li>
                <li><Link to="/features/certificates" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Certificates</Link></li>
                <li><Link to="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Pricing</Link></li>
              </ul>
            </div>

            {/* Resources Links */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-4">Resources</h3>
              <ul className="space-y-3">
                <li><Link to="/faq" className="text-sm text-muted-foreground hover:text-foreground transition-colors">FAQ</Link></li>
                <li><Link to="/contact" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Contact Us</Link></li>
                <li><Link to="/about" className="text-sm text-muted-foreground hover:text-foreground transition-colors">About</Link></li>
                <li><Link to="/verify" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Verify Certificate</Link></li>
              </ul>
            </div>

            {/* Legal Links */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-4">Legal</h3>
              <ul className="space-y-3">
                <li><Link to="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Privacy Policy</Link></li>
                <li><Link to="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Terms of Service</Link></li>
                <li><Link to="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Cookie Policy</Link></li>
              </ul>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">&copy; {new Date().getFullYear()} CPD Events. All rights reserved.</p>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="#" className="hover:text-foreground transition-colors">Privacy</Link>
              <span>·</span>
              <Link to="#" className="hover:text-foreground transition-colors">Terms</Link>
              <span>·</span>
              <Link to="#" className="hover:text-foreground transition-colors">Cookies</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// List Item Component for Navigation Menu
const ListItem = React.forwardRef<
  React.ElementRef<"a">,
  React.ComponentPropsWithoutRef<"a"> & { icon?: React.ReactNode; title: string; href: string }
>(({ className, title, children, icon, href, ...props }, ref) => {
  return (
    <li>
      <NavigationMenuLink asChild>
        <Link
          ref={ref as any}
          to={href}
          className={cn(
            "block select-none rounded-lg p-3 leading-none no-underline outline-none transition-colors hover:bg-muted focus:bg-muted group",
            className
          )}
          {...props}
        >
          <div className="flex items-start gap-3">
            {icon && (
              <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 group-hover:bg-primary/15 transition-colors">
                {icon}
              </div>
            )}
            <div>
              <div className="text-sm font-medium leading-none text-foreground mb-1">{title}</div>
              <p className="line-clamp-2 text-sm leading-snug text-muted-foreground">
                {children}
              </p>
            </div>
          </div>
        </Link>
      </NavigationMenuLink>
    </li>
  );
});
ListItem.displayName = "ListItem";
