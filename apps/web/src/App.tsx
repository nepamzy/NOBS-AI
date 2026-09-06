import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAdmin, RequireAuth } from "./auth/RequireAuth";
import { AdminDashboard } from "./pages/AdminDashboard";
import { CreateVideo } from "./pages/CreateVideo";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ProjectDetail } from "./pages/ProjectDetail";
import { Projects } from "./pages/Projects";
import { Settings } from "./pages/Settings";
import { Signup } from "./pages/Signup";
import { VideoDetail } from "./pages/VideoDetail";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="create" element={<CreateVideo />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:projectId" element={<ProjectDetail />} />
          <Route path="videos/:videoId" element={<VideoDetail />} />
          <Route path="settings" element={<Settings />} />
          <Route element={<RequireAdmin />}>
            <Route path="admin" element={<AdminDashboard />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
