import { useRef } from "react";
import { useSpeechToText } from "../hooks/useSpeechToText";

type MicButtonProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
};

/** A microphone toggle that dictates into whatever text field `value`/
 * `onChange` belong to — live, word by word, before the user hits send.
 * Appends to what was already typed rather than replacing it. Renders
 * nothing if the browser doesn't support speech recognition (Firefox). */
export function MicButton({ value, onChange, className = "" }: MicButtonProps) {
  const baseTextRef = useRef("");

  const { isSupported, isListening, start, stop } = useSpeechToText((sessionText) => {
    const base = baseTextRef.current;
    const joined = base && sessionText ? `${base} ${sessionText}` : base + sessionText;
    onChange(joined);
  });

  if (!isSupported) return null;

  function handleClick() {
    if (isListening) {
      stop();
    } else {
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
