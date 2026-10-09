// The player's rules, as one pure function: (state, action) -> new state.
// No React, timers or sound here, so every rule can be tested on its own.
// Buttons, the sentence timer and narration (5.10b) all just send actions.

export const SPEEDS = [0.75, 1, 1.25, 1.5] as const;
export type Speed = (typeof SPEEDS)[number];

export interface PlayerState {
  sentenceCounts: number[]; // how many sentences each scene has
  index: number; // current scene, 0-based
  sentence: number; // current sentence within the scene, 0-based
  playing: boolean;
  finished: boolean; // true after the last sentence of the last scene; Play then starts again
  speed: Speed;
}

export type PlayerAction =
  | { type: "play" }
  | { type: "pause" }
  | { type: "next" }
  | { type: "previous" }
  | { type: "goTo"; index: number }
  | { type: "sentenceEnded" }
  | { type: "setSpeed"; speed: number };

/** Paused on the first sentence of the first scene: no autoplay. */
export function initialPlayerState(sentenceCounts: number[]): PlayerState {
  return { sentenceCounts, index: 0, sentence: 0, playing: false, finished: false, speed: 1 };
}

export function playerReducer(state: PlayerState, action: PlayerAction): PlayerState {
  const last = state.sentenceCounts.length - 1;

  switch (action.type) {
    case "play":
      // After the end, Play starts again from the beginning, like a video player.
      return state.finished
        ? { ...state, index: 0, sentence: 0, playing: true, finished: false }
        : { ...state, playing: true };

    case "pause":
      // Keeps the sentence, so Play continues from here.
      return { ...state, playing: false };

    case "next":
      // Stops at the ends rather than wrapping round. A new scene starts at its first sentence.
      return state.index < last ? { ...state, index: state.index + 1, sentence: 0, finished: false } : state;

    case "previous":
      return state.index > 0 ? { ...state, index: state.index - 1, sentence: 0, finished: false } : state;

    case "goTo":
      // From the chapter list: keeps playing (or paused) as it was.
      if (!Number.isInteger(action.index) || action.index < 0 || action.index > last) return state;
      return { ...state, index: action.index, sentence: 0, finished: false };

    case "sentenceEnded": {
      // Next sentence; after the scene's last sentence, the next scene;
      // after the very last sentence, pause at the end instead of looping.
      if (state.sentence < state.sentenceCounts[state.index] - 1) {
        return { ...state, sentence: state.sentence + 1 };
      }
      return state.index < last
        ? { ...state, index: state.index + 1, sentence: 0 }
        : { ...state, playing: false, finished: true };
    }

    case "setSpeed":
      return isSpeed(action.speed) ? { ...state, speed: action.speed } : state;
  }
}

function isSpeed(value: number): value is Speed {
  return (SPEEDS as readonly number[]).includes(value);
}
