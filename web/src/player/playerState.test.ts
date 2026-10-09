import { describe, expect, test } from "vitest";
import { initialPlayerState, playerReducer, type PlayerAction, type PlayerState } from "./playerState";

/** Run a sequence of actions from the start, like a user clicking through. */
function run(sentenceCounts: number[], ...actions: PlayerAction[]): PlayerState {
  return actions.reduce(playerReducer, initialPlayerState(sentenceCounts));
}

const play: PlayerAction = { type: "play" };
const ended: PlayerAction = { type: "sentenceEnded" };
const ONE_EACH = [1, 1, 1]; // three scenes of one sentence each

describe("playerReducer", () => {
  test("starts paused on the first sentence of the first scene (no autoplay)", () => {
    expect(initialPlayerState([2, 3])).toEqual({
      sentenceCounts: [2, 3],
      index: 0,
      sentence: 0,
      playing: false,
      finished: false,
      speed: 1,
    });
  });

  test("play and pause", () => {
    expect(run(ONE_EACH, play).playing).toBe(true);
    expect(run(ONE_EACH, play, { type: "pause" }).playing).toBe(false);
  });

  test("next and previous move one scene", () => {
    expect(run(ONE_EACH, { type: "next" }).index).toBe(1);
    expect(run(ONE_EACH, { type: "next" }, { type: "next" }, { type: "previous" }).index).toBe(1);
  });

  test("next and previous stop at the ends instead of wrapping", () => {
    expect(run(ONE_EACH, { type: "previous" }).index).toBe(0);
    expect(run(ONE_EACH, { type: "next" }, { type: "next" }, { type: "next" }).index).toBe(2);
  });

  test("a sentence ending moves to the next sentence in the same scene", () => {
    expect(run([3, 1], play, ended)).toMatchObject({ index: 0, sentence: 1, playing: true });
  });

  test("the scene's last sentence ending moves to the next scene, first sentence", () => {
    expect(run([2, 2], play, ended, ended)).toMatchObject({ index: 1, sentence: 0, playing: true });
  });

  test("the very last sentence ending pauses at the end instead of looping", () => {
    expect(run([1, 2], play, ended, ended, ended)).toMatchObject({ index: 1, sentence: 1, playing: false, finished: true });
  });

  test("play after the end starts again from the first scene and sentence", () => {
    expect(run([1, 1], play, ended, ended, play)).toMatchObject({ index: 0, sentence: 0, playing: true, finished: false });
  });

  test("pause keeps the sentence, so play continues from it", () => {
    expect(run([3], play, ended, { type: "pause" }, play)).toMatchObject({ index: 0, sentence: 1, playing: true });
  });

  test("next, previous and goTo start the new scene at its first sentence", () => {
    expect(run([3, 3, 3], ended, ended, { type: "next" }).sentence).toBe(0);
    expect(run([3, 3, 3], { type: "next" }, ended, { type: "previous" }).sentence).toBe(0);
    expect(run([3, 3, 3], ended, { type: "goTo", index: 2 })).toMatchObject({ index: 2, sentence: 0 });
  });

  test("goTo jumps to a chapter and keeps playing or paused as it was", () => {
    expect(run(Array(9).fill(1), { type: "goTo", index: 4 })).toMatchObject({ index: 4, playing: false });
    expect(run(Array(9).fill(1), play, { type: "goTo", index: 4 })).toMatchObject({ index: 4, playing: true });
  });

  test.each([-1, 9, 2.5, Number.NaN])("goTo ignores an index of %s", (index) => {
    expect(run(Array(9).fill(1), { type: "goTo", index }).index).toBe(0);
  });

  test("going back after the end clears 'finished', so Play continues from there", () => {
    expect(run([1, 1], play, ended, ended, { type: "previous" }, play)).toMatchObject({
      index: 0,
      playing: true,
      finished: false,
    });
  });

  test("setSpeed accepts only the offered speeds", () => {
    expect(run(ONE_EACH, { type: "setSpeed", speed: 1.5 }).speed).toBe(1.5);
    expect(run(ONE_EACH, { type: "setSpeed", speed: 3 }).speed).toBe(1);
  });

  test("never changes the state it was given", () => {
    const before = initialPlayerState([2, 2]);
    const snapshot = structuredClone(before);
    playerReducer(before, { type: "next" });
    playerReducer(before, play);
    playerReducer(before, ended);
    expect(before).toEqual(snapshot);
  });
});
