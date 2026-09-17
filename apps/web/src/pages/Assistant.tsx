import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChatAttachment, ChatMessage } from "../api/types";
import { MicButton } from "../components/MicButton";

// `content` is either a plain string (what the user typed) or a list of
// Anthropic content blocks (assistant replies, tool_result messages this
// chat sends itself mid-turn, or an image/document block alongside the
// user's text). Only text is shown — everything else is plumbing or
// rendered separately (see attachmentLabel).
function visibleText(content: ChatMessage["content"]): string | null {
  if (typeof content === "string") return content;
  const text = content
    .filter((block) => block.type === "text")
    .map((block) => String(block.text ?? ""))
    .join("");
  return text || null;
}

function attachmentLabel(content: ChatMessage["content"]): string | null {
  if (typeof content === "string") return null;
  const block = content.find((b) => b.type === "image" || b.type === "document");
  if (!block) return null;
  return block.type === "image" ? "📎 Image attached" : "📎 PDF attached";
}

const ALLOWED_ATTACHMENT_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"];

function readFileAsAttachment(file: File): Promise<ChatAttachment> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      resolve({ media_type: file.type, data: base64, filename: file.name });
    };
    reader.onerror = () => reject(new Error("Couldn't read that file"));
    reader.readAsDataURL(file);
  });
}

export function Assistant() {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [attachment, setAttachment] = useState<ChatAttachment | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file later
    if (!file) return;
    if (!ALLOWED_ATTACHMENT_TYPES.includes(file.type)) {
      setError("Only images (PNG/JPEG/GIF/WebP) and PDFs are supported — video isn't yet.");
      return;
    }
    try {
      setAttachment(await readFileAsAttachment(file));
      setError(null);
    } catch {
      setError("Couldn't read that file — try another.");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if ((!message && !attachment) || sending) return;

    setInput("");
    const sentAttachment = attachment;
    setAttachment(null);
    setSending(true);
    setError(null);
    // Optimistic: show the user's turn immediately, replace with the
    // server's full history (incl. any tool calls it made) once it returns.
    const optimisticContent = sentAttachment
      ? [
          { type: sentAttachment.media_type.startsWith("image/") ? "image" : "document" },
          { type: "text", text: message },
        ]
      : message;
    setHistory((prev) => [...prev, { role: "user", content: optimisticContent }]);
    try {
      const response = await api.sendChatMessage(message, history, sentAttachment ?? undefined);
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
          Ask it to create a video, check on one, tweak a scene, or approve a storyboard. Signed in
          as admin, it can also research anything, help with code, and look at an image or PDF you
          attach.
        </p>
      </div>

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-lg border border-white/10 bg-black/20 p-4">
        {history.length === 0 && (
          <p className="text-sm text-white/40">
            Try: "What videos do I have in progress?", "Explain how OAuth works", or attach a
            screenshot and ask about it.
          </p>
        )}
        {history.map((message, i) => {
          const text = visibleText(message.content);
          const label = attachmentLabel(message.content);
          if (!text && !label) return null;
          const isUser = message.role === "user";
          return (
            <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                  isUser ? "bg-accent-500/20 text-white" : "bg-white/5 text-white/90"
                }`}
              >
                {label && <div className="mb-1 text-xs text-white/50">{label}</div>}
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

      {attachment && (
        <div className="mt-2 flex items-center gap-2 text-xs text-white/60">
          📎 {attachment.filename || "attachment"}
          <button
            type="button"
            onClick={() => setAttachment(null)}
            className="text-white/40 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_ATTACHMENT_TYPES.join(",")}
          onChange={handleFileSelect}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={sending}
          title="Attach an image or PDF"
          className="flex shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/60 hover:text-white"
        >
          📎
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the assistant… or tap 🎙 to dictate"
          disabled={sending}
          className="flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-accent-500 focus:outline-none"
        />
        <MicButton value={input} onChange={setInput} />
        <button
          type="submit"
          disabled={sending || (!input.trim() && !attachment)}
          className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
