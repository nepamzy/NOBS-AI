import { Navigate, Route, Routes } from "react-router-dom";
import { LandingLayout } from "./components/LandingLayout";
import { About } from "./pages/About";
import { Contact } from "./pages/Contact";
import { FAQ } from "./pages/FAQ";
import { Features } from "./pages/Features";
import { Home } from "./pages/Home";
import { HowItWorks } from "./pages/HowItWorks";
import { Platform } from "./pages/Platform";
import { Waitlist } from "./pages/Waitlist";

// Every public page of the site. Mounted as the lowest-priority catch-all in
// the app router (../App.tsx), so the admin app's own routes always win and
// anything unknown falls back to the landing home.
export function LandingSite() {
  return (
    <Routes>
      <Route element={<LandingLayout />}>
        <Route index element={<Home />} />
        <Route path="platform" element={<Platform />} />
        <Route path="features" element={<Features />} />
        <Route path="how-it-works" element={<HowItWorks />} />
        <Route path="about" element={<About />} />
        <Route path="faq" element={<FAQ />} />
        <Route path="contact" element={<Contact />} />
        <Route path="waitlist" element={<Waitlist />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
