import { Bell, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Project, SourceVideo, Video } from "../api/types";
import { isAwaitingApproval, isBlocked, isSourceVideoBlocked } from "../lib/videoStatus";

type Hit = { label: string; sublabel: string; to: string };

/** A real, working search over this account's own projects and videos —
 * fetched once and filtered client-side. Not an AI query (no endpoint for
 * that exists) — a plain, honest text search, same data the Projects and
 * Video Library pages already show. */
function useSearchIndex() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
  }, []);

  return useMemo<Hit[]>(
    () => [
      ...projects.map((p) => ({ label: p.name, sublabel: "Project", to: `/projects/${p.id}` })),
      ...videos.map((v) => ({ label: v.topic, sublabel: "Video", to: `/videos/${v.id}` })),
    ],
    [projects, videos],
  );
}

function SearchBox() {
  const index = useSearchIndex();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return index.filter((h) => h.label.toLowerCase().includes(q)).slice(0, 8);
  }, [index, query]);

  function go(hit: Hit) {
    setQuery("");
    setOpen(false);
    navigate(hit.to);
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <Search
        size={16}
        className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-white/40"
      />
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && results[0]) go(results[0]);
          if (e.key === "Escape") setOpen(false);
        }}
        placeholder="Search your projects and videos…"
        aria-label="Search your projects and videos"
        className="w-full rounded-full border border-white/10 bg-white/5 py-2 pr-3 pl-9 text-sm text-white placeholder:text-white/30 focus:border-accent-500"
      />
      {open && query.trim() && (
        <div className="absolute top-full left-0 z-20 mt-2 w-full rounded-lg border border-panel-border bg-panel p-1.5 shadow-xl">
          {results.length === 0 ? (
            <p className="px-3 py-2 text-sm text-white/40">No matches.</p>
          ) : (
            results.map((hit) => (
              <button
                key={hit.to}
                onClick={() => go(hit)}
                className="flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm text-white/80 hover:bg-white/5 hover:text-white"
              >
                <span className="truncate">{hit.label}</span>
                <span className="shrink-0 text-xs text-white/30">{hit.sublabel}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/** A real notification: "needs attention" means a video or clip-source
 * actually failed, or a storyboard is actually waiting on this person's
 * own approval — all computed live from real records, never a stored/
 * invented notifications feed. */
function NotificationBell() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[]>([]);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
    api.listSourceVideos().then(setSourceVideos).catch(() => setSourceVideos([]));
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const items = useMemo(() => {
    const blockedVideos = videos
      .filter(isBlocked)
      .map((v) => ({ label: `Needs attention: ${v.topic}`, to: `/videos/${v.id}` }));
    const awaitingApproval = videos
      .filter(isAwaitingApproval)
      .map((v) => ({ label: `Awaiting your approval: ${v.topic}`, to: `/videos/${v.id}` }));
    const blockedClips = sourceVideos
      .filter(isSourceVideoBlocked)
      .map((s) => ({ label: `Clipping needs attention: ${s.original_filename}`, to: "/clips" }));
    return [...awaitingApproval, ...blockedVideos, ...blockedClips];
  }, [videos, sourceVideos]);

  return (
    <div ref={boxRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications${items.length > 0 ? ` — ${items.length} need attention` : ""}`}
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/70 hover:text-white"
      >
        <Bell size={16} />
        {items.length > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
            {items.length > 9 ? "9+" : items.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute top-full right-0 z-20 mt-2 w-72 rounded-lg border border-panel-border bg-panel p-1.5 shadow-xl">
          {items.length === 0 ? (
            <p className="px-3 py-2 text-sm text-white/40">Nothing needs your attention.</p>
          ) : (
            items.map((item) => (
              <button
                key={item.to + item.label}
                onClick={() => {
                  setOpen(false);
                  navigate(item.to);
                }}
                className="block w-full truncate rounded-md px-3 py-2 text-left text-sm text-white/80 hover:bg-white/5 hover:text-white"
              >
                {item.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function TopBar() {
  return (
    <div className="hidden items-center gap-4 border-b border-white/10 bg-black/20 px-6 py-3 md:flex">
      <SearchBox />
      <div className="ml-auto">
        <NotificationBell />
      </div>
    </div>
  );
}
