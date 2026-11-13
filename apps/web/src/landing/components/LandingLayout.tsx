import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Footer } from "./Footer";
import { NavBar } from "./NavBar";

// React Router doesn't scroll for you on navigation (that's only a real
// browser's default for full page loads) — this restores it: top of page
// on a plain route change, or down to the #hash target when one of the
// nav's anchor links (e.g. the "For You" dropdown's /features#creators)
// is followed.
function ScrollManager() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) {
      // Wait a tick for the target page's content to mount before
      // measuring its position.
      const id = requestAnimationFrame(() => {
        document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      return () => cancelAnimationFrame(id);
    }
    window.scrollTo({ top: 0 });
  }, [pathname, hash]);

  return null;
}

export function LandingLayout() {
  return (
    <div className="landing-root flex min-h-screen flex-col overflow-x-clip">
      <ScrollManager />
      <NavBar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
