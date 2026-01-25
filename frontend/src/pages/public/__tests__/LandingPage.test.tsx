import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { LandingPage } from "../LandingPage";

const renderLandingPage = () => {
    return render(
        <BrowserRouter>
            <LandingPage />
        </BrowserRouter>
    );
};

describe("LandingPage", () => {
    it("renders hero section with main headline", () => {
        renderLandingPage();

        // New hero text
        expect(screen.getByText(/professional development/i)).toBeInTheDocument();
        expect(screen.getByText(/unified/i)).toBeInTheDocument();
    });

    it("has Get Started CTA button for learners linking to signup", () => {
        renderLandingPage();

        const ctaButtons = screen.getAllByRole("link", { name: /get started/i });
        // Should have at least one "Get Started" button (for learners)
        expect(ctaButtons.length).toBeGreaterThan(0);
        expect(ctaButtons[0]).toHaveAttribute("href", "/signup?role=attendee");
    });

    it("has Start Creating button for providers", () => {
        renderLandingPage();

        const providerButton = screen.getByRole("link", { name: /start creating/i });
        expect(providerButton).toHaveAttribute("href", "/pricing");
    });

    it("renders For Learners section", () => {
        renderLandingPage();

        expect(screen.getByText("For Learners")).toBeInTheDocument();
        expect(screen.getByText(/manage your professional development/i)).toBeInTheDocument();
    });

    it("renders For Providers section", () => {
        renderLandingPage();

        expect(screen.getByText("For Providers")).toBeInTheDocument();
        expect(screen.getByText(/deliver professional development at scale/i)).toBeInTheDocument();
    });

    it("renders platform tagline", () => {
        renderLandingPage();

        expect(screen.getByText(/the accredit platform/i)).toBeInTheDocument();
    });
});
