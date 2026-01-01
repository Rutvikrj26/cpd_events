import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { ForgotPasswordPage } from "../ForgotPasswordPage";

// Mock sonner toast
vi.mock("sonner", () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const renderForgotPasswordPage = () => {
    return render(
        <BrowserRouter>
            <ForgotPasswordPage />
        </BrowserRouter>
    );
};

describe("ForgotPasswordPage", () => {
    it("renders forgot password form", () => {
        renderForgotPasswordPage();

        expect(screen.getByText("Forgot Password?")).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/name@example.com/i)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
    });

    it("shows description text", () => {
        renderForgotPasswordPage();
        expect(screen.getByText(/enter your email address/i)).toBeInTheDocument();
    });

    it("has link back to login page", () => {
        renderForgotPasswordPage();

        const backToLoginLink = screen.getByRole("link", { name: /back to login/i });
        expect(backToLoginLink).toHaveAttribute("href", "/login");
    });
});
