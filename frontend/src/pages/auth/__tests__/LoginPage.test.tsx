import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { LoginPage } from "../LoginPage";

// Mock useAuth hook
vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        login: vi.fn(),
    }),
}));

// Mock sonner toast
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
        // Use getByText for labels since FormLabel/FormControl structure may not use proper label association
        expect(screen.getByText(/email address/i)).toBeInTheDocument();
        expect(screen.getByText(/^password$/i)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /sign in$/i })).toBeInTheDocument();
    });

    it("has link to signup page", () => {
        renderLoginPage();

        const signupLink = screen.getByRole("link", { name: /create a new account/i });
        expect(signupLink).toHaveAttribute("href", "/signup");
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
