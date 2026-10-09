import { useEffect, useMemo, useReducer } from "react";
import { SceneVisual } from "../scenes/SceneVisual";
import { useTheme } from "../theme/ThemeProvider";
import type { Scene } from "../types";
import { defaultNarrator, type Narrator } from "./narrator";
import { initialPlayerState, playerReducer, SPEEDS } from "./playerState";
import { splitSentences } from "./sentences";

/** One scene at a time, with play/pause, previous/next, speed and a chapter list. */
interface PlayerProps {
  scenes: Scene[];
  wordsPerSecond: number;
  /** The customer's preferred speech rate (customers.json prefs.speech_rate). */
  customerRate: number;
  /** Who speaks; tests pass a fake. Defaults to Web Speech, or a silent timer without it. */
  narrator?: Narrator;
}

export function Player({ scenes, wordsPerSecond, customerRate, narrator: injected }: PlayerProps) {
  const { voice } = useTheme();
  const narrator = useMemo(() => injected ?? defaultNarrator(voice, wordsPerSecond), [injected, voice, wordsPerSecond]);

  // Each scene as sentences: narration (shown, and counted) and speech (spoken).
  // A test checks every committed scene has the same number of each.
  const narration = useMemo(() => scenes.map((scene) => splitSentences(scene.narration)), [scenes]);
  const speech = useMemo(() => scenes.map((scene) => splitSentences(scene.speech)), [scenes]);
  const [state, dispatch] = useReducer(
    playerReducer,
    narration.map((list) => list.length),
    initialPlayerState,
  );
  const scene = scenes[state.index];
  const spoken = speech[state.index][state.sentence] ?? "";
  const isFirst = state.index === 0;
  const isLast = state.index === scenes.length - 1;
  // The theme's voice rate, the customer's preference and the Speed menu combine.
  const rate = voice.rate * customerRate * state.speed;

  // While playing, say the current sentence; when it's done, move on. The
  // clean-up stops speech whenever the sentence, rate or play state changes
  // (including Pause and leaving the page), so only one sentence is ever spoken.
  useEffect(() => {
    if (!state.playing) return;
    return narrator.speak(spoken, rate, () => dispatch({ type: "sentenceEnded" }));
  }, [state.playing, state.index, state.sentence, spoken, rate, narrator]);

  const playLabel = state.playing ? "Pause" : state.finished ? "Play again" : "Play";

  return (
    <section className="player" aria-labelledby="player-scene-title">
      <div className="player__stage">
        <h2 id="player-scene-title" className="player__title">
          {scene.title}
        </h2>
        <SceneVisual visual={scene.visual} />
        {/* Temporary: captions and the transcript replace this in 5.11. */}
        <p className="player__narration">{scene.narration}</p>
      </div>

      <div className="player__controls" role="group" aria-label="Player controls">
        {/* aria-disabled, not disabled: a disabled button drops keyboard focus.
            The reducer already ignores Previous on the first scene. */}
        <button
          type="button"
          className="player__button"
          aria-disabled={isFirst}
          onClick={() => dispatch({ type: "previous" })}
        >
          <Icon name="previous" /> Previous
        </button>
        <button
          type="button"
          className="player__button player__button--primary"
          onClick={() => dispatch({ type: state.playing ? "pause" : "play" })}
        >
          <Icon name={state.playing ? "pause" : "play"} /> {playLabel}
        </button>
        <button type="button" className="player__button" aria-disabled={isLast} onClick={() => dispatch({ type: "next" })}>
          Next <Icon name="next" />
        </button>

        <p className="player__position">
          Scene {state.index + 1} of {scenes.length}
        </p>

        <label className="player__speed">
          Speed
          <select value={state.speed} onChange={(event) => dispatch({ type: "setSpeed", speed: Number(event.target.value) })}>
            {SPEEDS.map((speed) => (
              <option key={speed} value={speed}>
                {speed}×
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Announced politely when the scene changes, including during playback. */}
      <p className="visually-hidden" aria-live="polite">
        Scene {state.index + 1} of {scenes.length}: {scene.title}
      </p>

      <nav className="chapters" aria-label="Chapters">
        <ol className="chapters__list">
          {scenes.map((chapter, index) => (
            <li key={chapter.id}>
              <button
                type="button"
                className="chapters__button"
                aria-current={index === state.index ? "step" : undefined}
                onClick={() => dispatch({ type: "goTo", index })}
              >
                <span className="chapters__number" aria-hidden="true">
                  {index + 1}
                </span>
                {chapter.title}
              </button>
            </li>
          ))}
        </ol>
      </nav>
    </section>
  );
}

const ICON_PATHS = {
  play: "M8 5v14l11-7z",
  pause: "M7 5h4v14H7zM13 5h4v14h-4z",
  previous: "M6 5h2v14H6zM20 5v14L9 12z",
  next: "M16 5h2v14h-2zM4 5v14l11-7z",
};

/** Decorative: every button also has a visible text label. */
function Icon({ name }: { name: keyof typeof ICON_PATHS }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <path d={ICON_PATHS[name]} fill="currentColor" />
    </svg>
  );
}
