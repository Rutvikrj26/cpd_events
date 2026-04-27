import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { LoginPage } from "../LoginPage";

// Mock the auth feature.  The LoginPage now uses BOTH the imperative
// `useAuth().login` (kept for backward compat) AND the deployment query
// to gate UI on `registration_mode`. Provide both so the page renders
// the invitation-only copy expected by these tests.
vi.mock("@/features/auth", () => ({
    useAuth: () => ({
        login: vi.fn(),
        deployment: {
            mode: "single_tenant",
            registration_mode: "invite_only",
            institution_name: "Accredit",
            institution_logo_url: "",
        },
    }),
}));

vi.mock("sonner", () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const renderLoginPage = () => {
    return render(
        <BrowserRouter>
            <LoginPage />
        </BrowserRouter>
    );
};

describe("LoginPage", () => {
    it("renders login form with email and password fields", () => {
        renderLoginPage();

        expect(screen.getByText("Sign in to your account")).toBeInTheDocument();
        expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /sign in$/i })).toBeInTheDocument();
    });

    it("shows invitation-only access copy", () => {
        renderLoginPage();

        expect(
            screen.getByText(/accounts on this platform are created by invitation only/i)
        ).toBeInTheDocument();
    });

    it("has link to forgot password page", () => {
        renderLoginPage();

        const forgotLink = screen.getByRole("link", { name: /forgot password/i });
        expect(forgotLink).toHaveAttribute("href", "/forgot-password");
    });

    it("has remember me checkbox", () => {
        renderLoginPage();

        expect(screen.getByRole("checkbox")).toBeInTheDocument();
        expect(screen.getByText(/remember me/i)).toBeInTheDocument();
    });
});
