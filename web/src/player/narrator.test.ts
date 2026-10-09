import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { pickVoice, timerNarrator, webSpeechNarrator } from "./narrator";

function voice(name: string, lang: string) {
  return { name, lang } as SpeechSynthesisVoice;
}

describe("pickVoice", () => {
  const voices = [voice("Alex", "en-US"), voice("Kate", "en-GB"), voice("Daniel (English (United Kingdom))", "en-GB"), voice("Amélie", "fr-CA")];

  test("prefers a named voice, including Chrome's longer names", () => {
    expect(pickVoice(voices, ["Daniel", "Kate"], "en-GB")?.name).toBe("Daniel (English (United Kingdom))");
  });

  test("then a voice for the exact language", () => {
    expect(pickVoice(voices, ["Serena"], "en-GB")?.name).toBe("Kate");
  });

  test("matches Android-style language codes", () => {
    expect(pickVoice([voice("Local", "en_GB")], [], "en-GB")?.name).toBe("Local");
  });

  test("then any voice in the same language", () => {
    expect(pickVoice([voice("Alex", "en-US"), voice("Amélie", "fr-CA")], [], "en-GB")?.name).toBe("Alex");
  });

  test("else null, meaning the browser's default", () => {
    expect(pickVoice([voice("Amélie", "fr-CA")], [], "en-GB")).toBeNull();
  });
});

// A stand-in for the browser's speech API, recording what it was asked to say.
class FakeUtterance {
  lang = "";
  pitch = 1;
  rate = 1;
  voice: SpeechSynthesisVoice | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public text: string) {}
}

function fakeSynth(voices: SpeechSynthesisVoice[] = []) {
  return {
    spoken: [] as FakeUtterance[],
    getVoices: () => voices,
    speak(utterance: FakeUtterance) {
      this.spoken.push(utterance);
    },
    cancel: vi.fn(),
  };
}

const settings = { lang: "en-GB", rate: 1, pitch: 1.1, preferred_voices: ["Daniel"] };

function narratorWith(synth: ReturnType<typeof fakeSynth>) {
  return webSpeechNarrator(settings, 1, {
    synth: synth as unknown as SpeechSynthesis,
    Utterance: FakeUtterance as unknown as typeof SpeechSynthesisUtterance,
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("webSpeechNarrator", () => {
  test("speaks the text with the theme's language, pitch, voice and the given rate", () => {
    const daniel = voice("Daniel", "en-GB");
    const synth = fakeSynth([daniel]);
    narratorWith(synth).speak("Hello Priya.", 1.2, () => {});

    const [utterance] = synth.spoken;
    expect(utterance).toMatchObject({ text: "Hello Priya.", lang: "en-GB", pitch: 1.1, rate: 1.2, voice: daniel });
  });

  test("reports done once when speech ends", () => {
    const synth = fakeSynth();
    const onDone = vi.fn();
    narratorWith(synth).speak("Hello.", 1, onDone);

    synth.spoken[0].onend!();
    synth.spoken[0].onend?.();
    vi.advanceTimersByTime(60_000); // the watchdog must not fire a second time
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  test("events fired by cancelling are ignored, so no sentence is skipped", () => {
    const synth = fakeSynth();
    const onDone = vi.fn();
    const cancel = narratorWith(synth).speak("Hello.", 1, onDone);
    const endHandler = synth.spoken[0].onend!; // the browser holds on to this

    cancel();
    endHandler(); // some browsers fire "end" for a cancelled sentence
    vi.advanceTimersByTime(60_000);

    expect(synth.cancel).toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
  });

  test("if speech fails, carries on after the estimated time", () => {
    const synth = fakeSynth();
    const onDone = vi.fn();
    narratorWith(synth).speak("Three words here.", 1, onDone); // 3 s at 1 word/s

    synth.spoken[0].onerror!();
    vi.advanceTimersByTime(2_999);
    expect(onDone).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  test("if 'end' never comes, the watchdog moves on", () => {
    const synth = fakeSynth();
    const onDone = vi.fn();
    narratorWith(synth).speak("Three words here.", 1, onDone);

    vi.advanceTimersByTime(3 * 3_000 + 3_000 - 1);
    expect(onDone).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});

describe("timerNarrator", () => {
  test("is done after the estimated time divided by the rate, unless cancelled", () => {
    const onDone = vi.fn();
    timerNarrator(1).speak("Four words in here.", 2, onDone); // 4 s / 2
    vi.advanceTimersByTime(2_000);
    expect(onDone).toHaveBeenCalledTimes(1);

    const cancelled = vi.fn();
    timerNarrator(1).speak("Four words in here.", 2, cancelled)();
    vi.advanceTimersByTime(10_000);
    expect(cancelled).not.toHaveBeenCalled();
  });
});
