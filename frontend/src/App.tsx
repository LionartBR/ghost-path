import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { SessionPage } from "./pages/SessionPage";
import { ReportPage } from "./pages/ReportPage";

function Footer() {
  return (
    <footer className="w-full border-t border-gray-200/60 bg-white/60 backdrop-blur-sm py-5 px-6">
      <div className="max-w-7xl mx-auto flex flex-col items-center gap-1.5 text-xs text-gray-400">
        <span>A Claude Code Hackathon Project</span>
        <span>Developer: Arthur A. Martins</span>
        <a
          href="https://x.com/lionartmartins"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 hover:text-blue-500 transition-colors mt-1"
        >
          @lionartmartins
        </a>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen">
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/session/:sessionId" element={<SessionPage />} />
            <Route path="/knowledge/:sessionId" element={<ReportPage />} />
            <Route path="/report/:sessionId" element={<ReportPage />} />
          </Routes>
        </div>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
