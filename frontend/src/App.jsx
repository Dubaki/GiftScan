import { BrowserRouter, Routes, Route } from "react-router-dom";
import WebApp from "@twa-dev/sdk";
import { useEffect } from "react";

import TabBar from "./components/TabBar";
import DashboardPage from "./pages/DashboardPage";
import EscrowPage from "./pages/EscrowPage";
import ProfilePage from "./pages/ProfilePage";

export default function App() {
  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/escrow" element={<EscrowPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
        <TabBar />
      </div>
    </BrowserRouter>
  );
}
