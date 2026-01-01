import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Input } from "../input";

describe("Input", () => {
    it("renders with placeholder", () => {
        render(<Input placeholder="Enter your email" />);
        const input = screen.getByPlaceholderText("Enter your email");
        expect(input).toBeInTheDocument();
    });

    it("handles typing", async () => {
        const user = userEvent.setup();
        render(<Input placeholder="Type here" />);

        const input = screen.getByPlaceholderText("Type here");
        await user.type(input, "Hello World");

        expect(input).toHaveValue("Hello World");
    });

    it("respects disabled state", async () => {
        const user = userEvent.setup();
        render(<Input placeholder="Disabled input" disabled />);

        const input = screen.getByPlaceholderText("Disabled input");
        expect(input).toBeDisabled();

        await user.type(input, "Should not work");
        expect(input).toHaveValue("");
    });

    it("renders with correct type", () => {
        render(<Input type="password" placeholder="Password" />);
        const input = screen.getByPlaceholderText("Password");
        expect(input).toHaveAttribute("type", "password");
    });

    it("calls onChange handler", async () => {
        const user = userEvent.setup();
        const handleChange = vi.fn();
        render(<Input placeholder="Test" onChange={handleChange} />);

        const input = screen.getByPlaceholderText("Test");
        await user.type(input, "a");

        expect(handleChange).toHaveBeenCalled();
    });

    it("accepts custom className", () => {
        render(<Input placeholder="Custom" className="custom-class" />);
        const input = screen.getByPlaceholderText("Custom");
        expect(input).toHaveClass("custom-class");
    });
});
