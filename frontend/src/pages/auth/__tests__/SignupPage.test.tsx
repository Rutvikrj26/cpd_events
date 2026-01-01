import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { SignupPage } from "../SignupPage";

// Mock useAuth hook
vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        register: vi.fn(),
    }),
}));

// Mock sonner toast
vi.mock("sonner", () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const renderSignupPage = () => {
    return render(
        <BrowserRouter>
            <SignupPage />
        </BrowserRouter>
    );
};

describe("SignupPage", () => {
    it("renders signup form with all fields", () => {
        renderSignupPage();

        expect(screen.getByText("Create your account")).toBeInTheDocument();
        expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
    });

    it("has terms checkbox", () => {
        renderSignupPage();
        expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("has link to login page", () => {
        renderSignupPage();

        const loginLink = screen.getByRole("link", { name: /sign in/i });
        expect(loginLink).toHaveAttribute("href", "/login");
    });

    it("has links to terms and privacy policy", () => {
        renderSignupPage();

        const termsLink = screen.getByRole("link", { name: /terms of service/i });
        const privacyLink = screen.getByRole("link", { name: /privacy policy/i });

        expect(termsLink).toHaveAttribute("href", "/terms");
        expect(privacyLink).toHaveAttribute("href", "/privacy");
    });
});
