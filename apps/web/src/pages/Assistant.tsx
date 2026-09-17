import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChatMessage } from "../api/types";

// `content` is either a plain string (what the user typed) or a list of
// Anthropic content blocks (assistant replies, or the tool_result messages
// this chat sends itself mid-turn). Only text is shown — tool_use/
// tool_result blocks are plumbing, not something to render in the
// transcript; a message that's entirely plumbing renders nothing.
function visibleText(content: ChatMessage["content"]): string | null {
  if (typeof content === "string") return content;
  const text = content
    .filter((block) => block.type === "text")
    .map((block) => String(block.text ?? ""))
    .join("");
  return text || null;
}

export function Assistant() {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setInput("");
    setSending(true);
    setError(null);
    // Optimistic: show the user's turn immediately, replace with the
    // server's full history (incl. any tool calls it made) once it returns.
    setHistory((prev) => [...prev, { role: "user", content: message }]);
    try {
      const response = await api.sendChatMessage(message, history);
      setHistory(response.history);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] max-w-2xl flex-col">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-white">Assistant</h1>
        <p className="mt-2 text-white/60">
          Ask it to create a video, check on one, tweak a scene, or approve a storyboard — it acts
          on your account the same way the rest of the app does.
        </p>
      </div>

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-lg border border-white/10 bg-black/20 p-4">
        {history.length === 0 && (
          <p className="text-sm text-white/40">
            Try: "What videos do I have in progress?" or "Start a video about the history of
            coffee, 3 minutes."
          </p>
        )}
        {history.map((message, i) => {
          const text = visibleText(message.content);
          if (!text) return null;
          const isUser = message.role === "user";
          return (
            <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                  isUser ? "bg-accent-500/20 text-white" : "bg-white/5 text-white/90"
                }`}
              >
                {text}
              </div>
            </div>
          );
        })}
        {sending && <p className="text-sm text-white/40">Thinking…</p>}
      </div>

      {error && (
        <p className="mt-2 text-sm text-red-400">
          {error.includes("LLM_PROVIDER")
            ? "The assistant isn't set up yet — it needs the same LLM provider/key as script generation (see Settings)."
            : error}
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the assistant…"
          disabled={sending}
          className="flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-accent-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
