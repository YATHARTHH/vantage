import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { ProjectsPage } from './pages/ProjectsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { AlertsPage } from './pages/AlertsPage';
import { TelemetryPage } from './pages/TelemetryPage';

export const App: React.FC = () => {
  return (
    <Router>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/telemetry" element={<TelemetryPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};
