// The player's rules, as one pure function: (state, action) -> new state.
// No React, timers or sound here, so every rule can be tested on its own.
// Buttons, the scene timer (5.9b) and narration (5.10) all just send actions.

export const SPEEDS = [0.75, 1, 1.25, 1.5] as const;
export type Speed = (typeof SPEEDS)[number];

export interface PlayerState {
  sceneCount: number;
  index: number; // current scene, 0-based
  playing: boolean;
  finished: boolean; // true after the last scene ends; Play then starts again
  speed: Speed;
}

export type PlayerAction =
  | { type: "play" }
  | { type: "pause" }
  | { type: "next" }
  | { type: "previous" }
  | { type: "goTo"; index: number }
  | { type: "sceneEnded" }
  | { type: "setSpeed"; speed: number };

/** Paused on the first scene: no autoplay. */
export function initialPlayerState(sceneCount: number): PlayerState {
  return { sceneCount, index: 0, playing: false, finished: false, speed: 1 };
}

export function playerReducer(state: PlayerState, action: PlayerAction): PlayerState {
  const last = state.sceneCount - 1;

  switch (action.type) {
    case "play":
      // After the end, Play starts again from the beginning, like a video player.
      return state.finished
        ? { ...state, index: 0, playing: true, finished: false }
        : { ...state, playing: true };

    case "pause":
      return { ...state, playing: false };

    case "next":
      // Stops at the ends rather than wrapping round.
      return state.index < last ? { ...state, index: state.index + 1, finished: false } : state;

    case "previous":
      return state.index > 0 ? { ...state, index: state.index - 1, finished: false } : state;

    case "goTo":
      // From the chapter list: keeps playing (or paused) as it was.
      if (!Number.isInteger(action.index) || action.index < 0 || action.index > last) return state;
      return { ...state, index: action.index, finished: false };

    case "sceneEnded":
      // The last scene ending pauses at the end instead of looping.
      return state.index < last
        ? { ...state, index: state.index + 1 }
        : { ...state, playing: false, finished: true };

    case "setSpeed":
      return isSpeed(action.speed) ? { ...state, speed: action.speed } : state;
  }
}

function isSpeed(value: number): value is Speed {
  return (SPEEDS as readonly number[]).includes(value);
}
