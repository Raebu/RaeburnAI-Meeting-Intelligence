export interface Principal {
  workspace_id: string;
  role: string;
  subject: string;
}

export interface IntegrationCommand {
  id: string;
  system: string;
  operation: string;
  payload: Record<string, unknown>;
  approval_status: string;
}

export interface MeetingIntelligenceResult {
  meeting_id: string;
  decisions: unknown[];
  action_items: unknown[];
  integration_commands: IntegrationCommand[];
  audit_events: string[];
}

interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

function getApiConfig(): ApiConfig | null {
  const apiKey = process.env.RAEBURN_DASHBOARD_API_KEY ?? process.env.RAEBURN_API_KEY;
  if (!apiKey) return null;
  return {
    apiKey,
    baseUrl: (process.env.RAEBURN_API_BASE_URL ?? 'http://localhost:8080').replace(/\/$/, ''),
  };
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const config = getApiConfig();
  if (!config) throw new Error('dashboard-api-key-not-configured');

  const response = await fetch(`${config.baseUrl}${path}`, {
    ...init,
    cache: 'no-store',
    headers: {
      'content-type': 'application/json',
      'x-api-key': config.apiKey,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`meeting-api-${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function dashboardConfigured(): boolean {
  return getApiConfig() !== null;
}

export async function currentPrincipal(): Promise<Principal> {
  return apiRequest<Principal>('/v1/auth/me');
}

export async function pendingApprovals(): Promise<MeetingIntelligenceResult[]> {
  return apiRequest<MeetingIntelligenceResult[]>('/v1/approvals');
}

export async function decideCommands(
  meetingId: string,
  commandIds: string[],
  decision: 'approve' | 'reject',
): Promise<MeetingIntelligenceResult> {
  const safeMeetingId = encodeURIComponent(meetingId);
  return apiRequest<MeetingIntelligenceResult>(
    `/v1/approvals/${safeMeetingId}/${decision}`,
    {
      method: 'POST',
      body: JSON.stringify({
        command_ids: commandIds,
        approved_by: 'raeburnai-dashboard',
      }),
    },
  );
}
