import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Button } from "../button";

describe("Button", () => {
    it("renders with default variant", () => {
        render(<Button>Click me</Button>);
        const button = screen.getByRole("button", { name: /click me/i });
        expect(button).toBeInTheDocument();
    });

    it("renders with outline variant", () => {
        render(<Button variant="outline">Outline</Button>);
        const button = screen.getByRole("button", { name: /outline/i });
        expect(button).toBeInTheDocument();
        expect(button).toHaveClass("border");
    });

    it("renders with ghost variant", () => {
        render(<Button variant="ghost">Ghost</Button>);
        const button = screen.getByRole("button", { name: /ghost/i });
        expect(button).toBeInTheDocument();
    });

    it("handles click events", async () => {
        const user = userEvent.setup();
        const handleClick = vi.fn();
        render(<Button onClick={handleClick}>Click me</Button>);

        const button = screen.getByRole("button", { name: /click me/i });
        await user.click(button);

        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("does not fire click when disabled", async () => {
        const user = userEvent.setup();
        const handleClick = vi.fn();
        render(
            <Button onClick={handleClick} disabled>
                Disabled
            </Button>
        );

        const button = screen.getByRole("button", { name: /disabled/i });
        expect(button).toBeDisabled();

        await user.click(button);
        expect(handleClick).not.toHaveBeenCalled();
    });

    it("renders with different sizes", () => {
        const { rerender } = render(<Button size="sm">Small</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-10");

        rerender(<Button size="lg">Large</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-12");

        rerender(<Button size="icon">Icon</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-11", "w-11");
    });

    it("renders children correctly", () => {
        render(
            <Button>
                <span data-testid="icon">🔥</span>
                With Icon
            </Button>
        );
        expect(screen.getByTestId("icon")).toBeInTheDocument();
        expect(screen.getByText("With Icon")).toBeInTheDocument();
    });
});
