import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import DashboardPage from "./pages/DashboardPage";
import NewAnalysisPage from "./pages/NewAnalysisPage";
import AnalysisHistoryPage from "./pages/AnalysisHistoryPage";
import AnalysisDetailPage from "./pages/AnalysisDetailPage";

function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/analyze" element={<NewAnalysisPage />} />
          <Route path="/analyses" element={<AnalysisHistoryPage />} />
          <Route path="/analyses/:id" element={<AnalysisDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
