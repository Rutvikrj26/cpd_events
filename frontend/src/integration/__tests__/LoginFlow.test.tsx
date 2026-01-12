import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "@/App";
import * as accountsApi from "@/api/accounts";
import * as manifestApi from "@/api/auth/manifest";
import * as billingApi from "@/api/billing";
import * as organizationsApi from "@/api/organizations";
import * as registrationsApi from "@/api/registrations";

// Mock API modules
vi.mock("@/api/accounts");
vi.mock("@/api/auth/manifest");
vi.mock("@/api/billing");
vi.mock("@/api/organizations");
vi.mock("@/api/registrations");

// Mock scroll to top to avoid errors in JSDOM
vi.mock("@/components/layout/ScrollToTop", () => ({
    default: () => null,
}));

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

describe("Integration: Login Flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.pushState({}, "Home", "/");

        // Default mocks
        (manifestApi.getManifest as any).mockResolvedValue({
            routes: ["dashboard", "events", "profile"],
            features: {},
        });

        (billingApi.getSubscription as any).mockResolvedValue(null);
        (organizationsApi.getMyInvitations as any).mockResolvedValue([]);
        (registrationsApi.getMyRegistrations as any).mockResolvedValue([]);
    });

    it("completes full login flow", async () => {
        // 1. Mock api responses
        (accountsApi.login as any).mockResolvedValue({
            access: "fake-access-token",
            refresh: "fake-refresh-token",
        });

        (accountsApi.getCurrentUser as any).mockResolvedValue({
            uuid: "test-user-id",
            email: "test@example.com",
            account_type: "attendee",
            first_name: "Test",
            last_name: "User",
            display_name: "Test User"
        });

        render(<App />);

        // 2. Initial state: Landing Page
        expect(screen.getByText(/host events/i)).toBeInTheDocument();

        // 3. Navigate to Login
        const loginLink = screen.getByRole("link", { name: /log in/i });
        fireEvent.click(loginLink);

        // Wait for login page
        await waitFor(() => {
            // Use getByText with selector to avoid accessibility name issues
            expect(screen.getByText("Sign in", { selector: "button" })).toBeInTheDocument();
        });

        // 4. Fill credentials
        fireEvent.change(screen.getByLabelText(/email address/i), {
            target: { value: "test@example.com" },
        });
        fireEvent.change(screen.getByLabelText(/password/i), {
            target: { value: "password123" },
        });

        // 5. Submit
        fireEvent.click(screen.getByText("Sign in", { selector: "button" }));

        // 6. Verify Dashboard Redirect
        // Helper to log current URL if needed: console.log(window.location.pathname)
        await waitFor(() => {
            expect(screen.getByText("Dashboard")).toBeInTheDocument();
        }, { timeout: 3000 });

        expect(screen.getByText("Attendee Portal")).toBeInTheDocument();
    });
});
