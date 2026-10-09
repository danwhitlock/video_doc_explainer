import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Scene } from "../types";
import { Player } from "./Player";

function scene(id: string, title: string, seconds: number): Scene {
  return {
    id,
    title,
    visual: { type: "checklist", items: [`${title} item`] },
    narration: `${title} narration.`,
    speech: `${title} narration.`,
    start_seconds: 0,
    duration_seconds: seconds,
  };
}

const scenes = [scene("a", "Welcome", 2), scene("b", "Your loan", 4), scene("c", "Contact", 3)];

function currentTitle() {
  return screen.getByRole("heading", { level: 2 }).textContent;
}

function button(name: string | RegExp) {
  return screen.getByRole("button", { name });
}

/** Move the fake clock on, letting React update. */
function wait(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Player", () => {
  test("starts paused on the first scene: no autoplay", () => {
    render(<Player scenes={scenes} />);
    expect(currentTitle()).toBe("Welcome");
    expect(button(/^Play$/)).toBeTruthy();
    wait(10_000);
    expect(currentTitle()).toBe("Welcome");
  });

  test("playing moves on after each scene's duration", () => {
    render(<Player scenes={scenes} />);
    fireEvent.click(button(/^Play$/));

    wait(1_999);
    expect(currentTitle()).toBe("Welcome");
    wait(1);
    expect(currentTitle()).toBe("Your loan");
  });

  test("at 1.5x speed each scene is shorter", () => {
    render(<Player scenes={scenes} />);
    fireEvent.change(screen.getByLabelText("Speed"), { target: { value: "1.5" } });
    fireEvent.click(button(/^Play$/));

    wait(1_334); // 2 s / 1.5
    expect(currentTitle()).toBe("Your loan");
  });

  test("pause stops it moving on", () => {
    render(<Player scenes={scenes} />);
    fireEvent.click(button(/^Play$/));
    fireEvent.click(button(/^Pause$/));
    wait(10_000);
    expect(currentTitle()).toBe("Welcome");
  });

  test("pauses after the last scene, then offers Play again from the start", () => {
    render(<Player scenes={scenes} />);
    fireEvent.click(button(/^Play$/));
    wait(2_000);
    wait(4_000);
    wait(3_000);
    expect(currentTitle()).toBe("Contact");
    fireEvent.click(button(/Play again/));
    expect(currentTitle()).toBe("Welcome");
  });

  test("next, previous and the chapter list move between scenes", () => {
    render(<Player scenes={scenes} />);
    fireEvent.click(button(/Next/));
    expect(currentTitle()).toBe("Your loan");
    fireEvent.click(button(/Previous/));
    expect(currentTitle()).toBe("Welcome");

    const chapters = screen.getByRole("navigation", { name: "Chapters" });
    fireEvent.click(within(chapters).getByRole("button", { name: /Contact/ }));
    expect(currentTitle()).toBe("Contact");
    expect(within(chapters).getByRole("button", { name: /Contact/ }).getAttribute("aria-current")).toBe("step");
    expect(within(chapters).getByRole("button", { name: /Welcome/ }).getAttribute("aria-current")).toBeNull();
  });

  test("at the ends, Previous/Next are aria-disabled but keep keyboard focus", () => {
    render(<Player scenes={scenes} />);
    expect(button(/Previous/).getAttribute("aria-disabled")).toBe("true");

    const next = button(/Next/);
    next.focus();
    fireEvent.click(next);
    fireEvent.click(next);
    fireEvent.click(next); // one more than there are scenes
    expect(currentTitle()).toBe("Contact");
    expect(next.getAttribute("aria-disabled")).toBe("true");
    expect(document.activeElement).toBe(next);
  });

  test("announces the scene position and title politely", () => {
    const { container } = render(<Player scenes={scenes} />);
    fireEvent.click(button(/Next/));
    const live = container.querySelector('[aria-live="polite"]');
    expect(live?.textContent).toBe("Scene 2 of 3: Your loan");
  });
});
