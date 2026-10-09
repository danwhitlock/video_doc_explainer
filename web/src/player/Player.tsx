import { useEffect, useReducer } from "react";
import { SceneVisual } from "../scenes/SceneVisual";
import type { Scene } from "../types";
import { initialPlayerState, playerReducer, SPEEDS } from "./playerState";

/** One scene at a time, with play/pause, previous/next, speed and a chapter list. */
export function Player({ scenes }: { scenes: Scene[] }) {
  const [state, dispatch] = useReducer(playerReducer, scenes.length, initialPlayerState);
  const scene = scenes[state.index];
  const isFirst = state.index === 0;
  const isLast = state.index === scenes.length - 1;

  // While playing, end the scene after its estimated duration (faster at higher
  // speeds). The clean-up cancels the timer whenever the scene, speed or play
  // state changes, so only one is ever running. Narration takes over in 5.10.
  useEffect(() => {
    if (!state.playing) return;
    const timer = setTimeout(() => dispatch({ type: "sceneEnded" }), (scene.duration_seconds * 1000) / state.speed);
    return () => clearTimeout(timer);
  }, [state.playing, state.index, state.speed, scene.duration_seconds]);

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
