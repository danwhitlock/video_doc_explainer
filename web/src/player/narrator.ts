import type { Theme } from "../types";
import { estimateSeconds } from "./sentences";

/**
 * Something that can "say" a sentence and report when it's finished.
 * Returns a function that stops it. The Player only knows this interface,
 * so tests (and browsers without speech) can use a different narrator:
 * the same idea as the pipeline's providers.
 */
export interface Narrator {
  speak(text: string, rate: number, onDone: () => void): () => void;
}

type VoiceSettings = Theme["voice"];

/** Silent: waits the sentence's estimated time. Used where speech isn't available. */
export function timerNarrator(wordsPerSecond: number): Narrator {
  return {
    speak(text, rate, onDone) {
      const timer = setTimeout(onDone, (estimateSeconds(text, wordsPerSecond) * 1000) / rate);
      return () => clearTimeout(timer);
    },
  };
}

function normaliseLang(lang: string): string {
  return lang.toLowerCase().replace("_", "-"); // Android reports "en_GB"
}

/**
 * The best installed voice: a preferred name first (Chrome adds detail, e.g.
 * "Daniel (English (United Kingdom))"), then the exact language, then any
 * voice in the same language, else null (the browser's default).
 */
export function pickVoice(
  voices: SpeechSynthesisVoice[],
  preferred: string[],
  lang: string,
): SpeechSynthesisVoice | null {
  for (const name of preferred) {
    const match = voices.find((voice) => voice.name === name || voice.name.startsWith(`${name} `));
    if (match) return match;
  }
  const wanted = normaliseLang(lang);
  const sameLang = voices.find((voice) => normaliseLang(voice.lang) === wanted);
  if (sameLang) return sameLang;
  const family = wanted.split("-")[0];
  return voices.find((voice) => normaliseLang(voice.lang).split("-")[0] === family) ?? null;
}

interface SpeechDeps {
  synth: SpeechSynthesis;
  Utterance: typeof SpeechSynthesisUtterance;
}

/** Speaks with the browser's Web Speech API, with fallbacks for its quirks. */
export function webSpeechNarrator(settings: VoiceSettings, wordsPerSecond: number, deps: SpeechDeps): Narrator {
  const { synth, Utterance } = deps;
  return {
    speak(text, rate, onDone) {
      const estimateMs = (estimateSeconds(text, wordsPerSecond) * 1000) / rate;
      let finished = false;
      let fallback: ReturnType<typeof setTimeout> | undefined;

      const finish = () => {
        if (finished) return;
        finished = true;
        clearTimeout(watchdog);
        clearTimeout(fallback);
        onDone();
      };

      const utterance = new Utterance(text);
      utterance.lang = settings.lang;
      utterance.pitch = settings.pitch;
      utterance.rate = rate;
      // Picked now, not at page load: browsers fill the voice list late.
      utterance.voice = pickVoice(synth.getVoices(), settings.preferred_voices, settings.lang);
      utterance.onend = finish;
      // If speech fails, carry on at the estimated pace rather than stopping.
      utterance.onerror = () => {
        if (!finished) fallback = setTimeout(finish, estimateMs);
      };
      // Some browsers occasionally never fire "end" (a known Chrome bug); don't get stuck.
      const watchdog = setTimeout(finish, estimateMs * 3 + 3000);

      synth.speak(utterance);

      return () => {
        // cancel() can itself fire "end" or "error" for this sentence; marking
        // it finished first means those events are ignored, so nothing is skipped.
        finished = true;
        clearTimeout(watchdog);
        clearTimeout(fallback);
        utterance.onend = null;
        utterance.onerror = null;
        synth.cancel();
      };
    },
  };
}

/** Web Speech if this browser has it, otherwise the silent timer. */
export function defaultNarrator(settings: VoiceSettings, wordsPerSecond: number): Narrator {
  if (typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window) {
    return webSpeechNarrator(settings, wordsPerSecond, {
      synth: window.speechSynthesis,
      Utterance: window.SpeechSynthesisUtterance,
    });
  }
  return timerNarrator(wordsPerSecond);
}
