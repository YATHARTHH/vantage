import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { PlatformOverview } from './pages/PlatformOverview';
import { ProjectsPage } from './pages/ProjectsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { AlertsPage } from './pages/AlertsPage';
import { TelemetryPage } from './pages/TelemetryPage';
import VectorDriftExplorer from './pages/VectorDriftExplorer';
import DAGExplorer from './pages/DAGExplorer';
import EnterpriseSettingsPage from './pages/EnterpriseSettingsPage';

export const App: React.FC = () => {
  return (
    <Router>
      <div style={{ minHeight: '100vh', width: '100%', maxWidth: '100vw', overflowX: 'hidden', display: 'flex', flexDirection: 'column', background: '#0a0d14' }}>
        <Navbar />
        <main style={{ flex: 1, width: '100%', maxWidth: '100vw', overflowX: 'hidden' }}>
          <Routes>
            <Route path="/" element={<PlatformOverview />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/telemetry" element={<TelemetryPage />} />
            <Route path="/vector-explorer" element={<VectorDriftExplorer />} />
            <Route path="/dag-explorer" element={<DAGExplorer />} />
            <Route path="/enterprise" element={<EnterpriseSettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};
