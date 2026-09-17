import { useEffect, useRef } from "react";
import { useSpeechToText } from "../hooks/useSpeechToText";

type MicButtonProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  /** Fires right before listening starts — e.g. to interrupt TTS playback
   * when the user starts talking over it ("barge-in"). */
  onStart?: () => void;
  /** Fires once listening ends (manual stop or the browser auto-ending the
   * session) with the final dictated text — used by voice mode to
   * auto-send instead of requiring a manual tap on Send. */
  onStop?: (finalValue: string) => void;
};

/** A microphone toggle that dictates into whatever text field `value`/
 * `onChange` belong to — live, word by word, before the user hits send.
 * Appends to what was already typed rather than replacing it. Renders
 * nothing if the browser doesn't support speech recognition (Firefox). */
export function MicButton({ value, onChange, className = "", onStart, onStop }: MicButtonProps) {
  const baseTextRef = useRef("");
  const valueRef = useRef(value);
  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  const { isSupported, isListening, start, stop } = useSpeechToText((sessionText) => {
    const base = baseTextRef.current;
    const joined = base && sessionText ? `${base} ${sessionText}` : base + sessionText;
    onChange(joined);
  });

  const wasListeningRef = useRef(false);
  useEffect(() => {
    if (wasListeningRef.current && !isListening) {
      onStop?.(valueRef.current);
    }
    wasListeningRef.current = isListening;
  }, [isListening, onStop]);

  if (!isSupported) return null;

  function handleClick() {
    if (isListening) {
      stop();
    } else {
      onStart?.();
      baseTextRef.current = value;
      start();
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      title={isListening ? "Stop dictating" : "Dictate with your microphone"}
      aria-pressed={isListening}
      className={`flex shrink-0 items-center justify-center rounded-md border px-3 py-2 text-sm transition-colors ${
        isListening
          ? "animate-pulse border-red-500/40 bg-red-500/20 text-red-300"
          : "border-white/10 bg-white/5 text-white/60 hover:text-white"
      } ${className}`}
    >
      {isListening ? "● Listening…" : "🎙"}
    </button>
  );
}
