import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev-local-key',
  },
});

export interface Project {
  id: string;
  display_name: string;
  project_type: 'ai_llm' | 'software';
  owner_team: string;
  owner_email: string;
  description?: string;
  log_prompts: boolean;
  active: boolean;
  created_at: string;
}

export interface SourceMapping {
  id: string;
  project_id: string;
  source_tool: string;
  source_identifier: string;
  display_label?: string;
}

export interface Experiment {
  id: string;
  title: string;
  slug: string;
  project_id?: string;
  status: 'planned' | 'active' | 'completed' | 'archived';
  hypothesis: string;
  objective: string;
  owner_name: string;
  owner_team: string;
  owner_email: string;
  start_date: string;
  expected_end: string;
  actual_end?: string;
  result?: {
    outcome: 'success' | 'failure' | 'inconclusive';
    summary: string;
    metrics: Record<string, number>;
    learnings: string;
    recommendations?: string;
  };
}

export interface AlertRecord {
  id: string;
  project_id: string;
  detector_type: string;
  metric_name: string;
  incident_key: string;
  title: string;
  severity: string;
  observed_value: number;
  threshold_value: number;
  triggered_at: string;
  resolved_at?: string;
}

export interface AgentRunCost {
  trace_id: string;
  agent_name: string;
  started_at: string;
  total_cost_usd: number;
  llm_call_count: number;
  tokens_input: number;
  tokens_output: number;
  status: string;
}

export const VantageAPI = {
  // Projects
  getProjects: async (): Promise<Project[]> => {
    const res = await api.get('/projects');
    return res.data;
  },
  createProject: async (data: Partial<Project>): Promise<Project> => {
    const res = await api.post('/projects', data);
    return res.data;
  },

  // Experiments
  getExperiments: async (): Promise<Experiment[]> => {
    const res = await api.get('/experiments');
    return res.data;
  },
  createExperiment: async (data: Partial<Experiment>): Promise<Experiment> => {
    const res = await api.post('/experiments', data);
    return res.data;
  },

  // Alerts
  getAlerts: async (unresolvedOnly = false): Promise<AlertRecord[]> => {
    const res = await api.get(`/alerts?unresolved_only=${unresolvedOnly}`);
    return res.data;
  },
  resolveAlert: async (alertId: string): Promise<{ resolved: boolean }> => {
    const res = await api.patch(`/alerts/${alertId}/resolve`);
    return res.data;
  },

  // Telemetry & Agent Cost
  getAgentCost: async (projectId: string): Promise<AgentRunCost[]> => {
    const res = await api.get(`/query/agent-cost?project_id=${projectId}`);
    return res.data;
  },
};
