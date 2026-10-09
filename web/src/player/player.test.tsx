import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Scene } from "../types";
import { Player } from "./Player";

function scene(id: string, title: string, narration: string): Scene {
  return {
    id,
    title,
    visual: { type: "checklist", items: [`${title} item`] },
    narration,
    speech: narration,
    start_seconds: 0,
    duration_seconds: 0, // not used: timing comes from each sentence's words
  };
}

// At 1 word per second, each sentence lasts as many seconds as it has words.
const WPS = 1;
const scenes = [
  scene("a", "Welcome", "Hello there friend. Welcome."), // 3 s, then 1 s
  scene("b", "Your loan", "You borrow money."), // 3 s
  scene("c", "Contact", "Call us."), // 2 s
];

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
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    expect(currentTitle()).toBe("Welcome");
    expect(button(/^Play$/)).toBeTruthy();
    wait(10_000);
    expect(currentTitle()).toBe("Welcome");
  });

  test("playing moves on sentence by sentence, then to the next scene", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.click(button(/^Play$/));

    wait(3_000); // "Hello there friend."
    expect(currentTitle()).toBe("Welcome");
    wait(999); // most of "Welcome."
    expect(currentTitle()).toBe("Welcome");
    wait(1);
    expect(currentTitle()).toBe("Your loan");
  });

  test("at 1.5x speed each sentence is shorter", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.change(screen.getByLabelText("Speed"), { target: { value: "1.5" } });
    fireEvent.click(button(/^Play$/));

    wait(2_000); // 3 s / 1.5
    wait(667); // 1 s / 1.5
    expect(currentTitle()).toBe("Your loan");
  });

  test("pause stops it moving on", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.click(button(/^Play$/));
    fireEvent.click(button(/^Pause$/));
    wait(10_000);
    expect(currentTitle()).toBe("Welcome");
  });

  test("resume continues from the current sentence, not the start of the scene", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.click(button(/^Play$/));
    wait(3_000); // now on "Welcome."
    fireEvent.click(button(/^Pause$/));
    fireEvent.click(button(/^Play$/));

    wait(1_000); // only the 1-word sentence is left, not the whole 4 s scene
    expect(currentTitle()).toBe("Your loan");
  });

  test("pauses after the last scene, then offers Play again from the start", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.click(button(/^Play$/));
    wait(3_000);
    wait(1_000);
    wait(3_000);
    wait(2_000);
    expect(currentTitle()).toBe("Contact");
    fireEvent.click(button(/Play again/));
    expect(currentTitle()).toBe("Welcome");
  });

  test("next, previous and the chapter list move between scenes", () => {
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
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
    render(<Player scenes={scenes} wordsPerSecond={WPS} />);
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
    const { container } = render(<Player scenes={scenes} wordsPerSecond={WPS} />);
    fireEvent.click(button(/Next/));
    const live = container.querySelector('[aria-live="polite"]');
    expect(live?.textContent).toBe("Scene 2 of 3: Your loan");
  });
});
