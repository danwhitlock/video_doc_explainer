import { describe, expect, test } from "vitest";
import { initialPlayerState, playerReducer, type PlayerAction, type PlayerState } from "./playerState";

/** Run a sequence of actions from the start, like a user clicking through. */
function run(sceneCount: number, ...actions: PlayerAction[]): PlayerState {
  return actions.reduce(playerReducer, initialPlayerState(sceneCount));
}

describe("playerReducer", () => {
  test("starts paused on the first scene at normal speed (no autoplay)", () => {
    expect(initialPlayerState(9)).toEqual({ sceneCount: 9, index: 0, playing: false, finished: false, speed: 1 });
  });

  test("play and pause", () => {
    expect(run(3, { type: "play" }).playing).toBe(true);
    expect(run(3, { type: "play" }, { type: "pause" }).playing).toBe(false);
  });

  test("next and previous move one scene", () => {
    expect(run(3, { type: "next" }).index).toBe(1);
    expect(run(3, { type: "next" }, { type: "next" }, { type: "previous" }).index).toBe(1);
  });

  test("next and previous stop at the ends instead of wrapping", () => {
    expect(run(3, { type: "previous" }).index).toBe(0);
    expect(run(3, { type: "next" }, { type: "next" }, { type: "next" }).index).toBe(2);
  });

  test("a scene ending moves to the next, and keeps playing", () => {
    const state = run(3, { type: "play" }, { type: "sceneEnded" });
    expect(state.index).toBe(1);
    expect(state.playing).toBe(true);
  });

  test("the last scene ending pauses at the end instead of looping", () => {
    const state = run(2, { type: "play" }, { type: "sceneEnded" }, { type: "sceneEnded" });
    expect(state).toMatchObject({ index: 1, playing: false, finished: true });
  });

  test("play after the end starts again from the first scene", () => {
    const state = run(2, { type: "play" }, { type: "sceneEnded" }, { type: "sceneEnded" }, { type: "play" });
    expect(state).toMatchObject({ index: 0, playing: true, finished: false });
  });

  test("goTo jumps to a chapter and keeps playing or paused as it was", () => {
    expect(run(9, { type: "goTo", index: 4 })).toMatchObject({ index: 4, playing: false });
    expect(run(9, { type: "play" }, { type: "goTo", index: 4 })).toMatchObject({ index: 4, playing: true });
  });

  test.each([-1, 9, 2.5, Number.NaN])("goTo ignores an index of %s", (index) => {
    expect(run(9, { type: "goTo", index }).index).toBe(0);
  });

  test("going back after the end clears 'finished', so Play continues from there", () => {
    const state = run(2, { type: "play" }, { type: "sceneEnded" }, { type: "sceneEnded" }, { type: "previous" }, { type: "play" });
    expect(state).toMatchObject({ index: 0, playing: true, finished: false });
  });

  test("setSpeed accepts only the offered speeds", () => {
    expect(run(3, { type: "setSpeed", speed: 1.5 }).speed).toBe(1.5);
    expect(run(3, { type: "setSpeed", speed: 3 }).speed).toBe(1);
  });

  test("never changes the state it was given", () => {
    const before = initialPlayerState(3);
    const snapshot = structuredClone(before);
    playerReducer(before, { type: "next" });
    playerReducer(before, { type: "play" });
    expect(before).toEqual(snapshot);
  });
});
