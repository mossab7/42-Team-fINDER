import type { AuthStatus, Campus, MetadataResponse, Paginated, Project, ProjectConfiguration, Scan, ScanConfig, Student, Team } from '../types/api'

const API = import.meta.env.VITE_API_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`) }
  return response.status === 204 ? undefined as T : response.json()
}

export const api = {
  authStatus: () => request<AuthStatus>('/auth/me'),
  loginUrl: () => `${API}/auth/login`,
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  health: () => request<{status:string;api_mode:'demo'|'live';api_configured:boolean;timestamp:string}>('/health'),
  campuses: (force = false) => request<MetadataResponse<Campus>>(`/campuses?force_refresh=${force}`),
  projects: (force = false) => request<MetadataResponse<Project>>(`/projects?force_refresh=${force}`),
  projectConfiguration: (projectId:number,campusId:number) => request<ProjectConfiguration>(`/projects/${projectId}/configuration?campus_id=${campusId}`),
  promotions: (campusId: number) => request<{cursus_years:number[]}>(`/promotions?campus_id=${campusId}`),
  createScan: (config: ScanConfig) => request<Scan>('/scans', { method: 'POST', body: JSON.stringify(config) }),
  scan: (id: string) => request<Scan>(`/scans/${id}`),
  scans: () => request<Scan[]>('/scans'),
  students: (id: string, params: URLSearchParams) => request<Paginated<Student>>(`/scans/${id}/students?${params}`),
  teams: (id: string, params: URLSearchParams) => request<Paginated<Team>>(`/scans/${id}/teams?${params}`),
  clearCache: () => request<void>('/cache', { method: 'DELETE' }),
  savedSearches: () => request<{id:number;name:string;configuration:ScanConfig;created_at:string}[]>('/saved-searches'),
  saveSearch: (name: string, configuration: ScanConfig) => request<{id:number;name:string;configuration:ScanConfig;created_at:string}>('/saved-searches', { method: 'POST', body: JSON.stringify({name, configuration}) }),
  exportUrl: (id: string, format: 'csv'|'json') => `${API}/scans/${id}/export?format=${format}`,
  discoverProjects: () => request<{items:MatchProject[]}>('/discover/projects'),
  candidates: (projectId:number, params = new URLSearchParams()) => request<{items:StudentProfile[];scan_id:string}>(`/discover/candidates?project_id=${projectId}&${params}`),
  swipe: (target_user_id:number, project_id:number, direction:'left'|'right') => request<{matched:boolean;match_id:number|null}>('/swipes', {method:'POST',body:JSON.stringify({target_user_id,project_id,direction})}),
  myProfile: () => request<StudentProfile>('/profile/me'),
  updateProfile: (payload:Partial<StudentProfile>) => request<StudentProfile>('/profile/me',{method:'PATCH',body:JSON.stringify(payload)}),
  matches: () => request<{items:MatchItem[]}>('/matches'),
  removeMatch: (id:number) => request<void>(`/matches/${id}`,{method:'DELETE'}),
  notifications: () => request<{items:NotificationItem[]}>('/notifications'),
  readNotification: (id:number) => request(`/notifications/${id}`,{method:'PATCH'}),
  platformTeams: (projectId?:number) => request<{items:PlatformTeam[]}>(`/teams${projectId ? `?project_id=${projectId}`:''}`),
  createTeam: (match_id:number,name:string,description='') => request<PlatformTeam>('/teams',{method:'POST',body:JSON.stringify({match_id,name,description})}),
  invitations: () => request<{items:TeamInvitation[]}>('/team-invitations'),
  respondInvitation: (id:number,accept:boolean) => request(`/team-invitations/${id}/respond`,{method:'POST',body:JSON.stringify({accept})}),
  leaveTeam: (id:number) => request<void>(`/teams/${id}/members/me`,{method:'DELETE'}),
}

export type StudentProfile={user_id:number;login:string;display_name:string;image_url?:string|null;profile_url?:string|null;campus_name?:string|null;campus_id?:number|null;level?:number|null;biography:string;skills:string[];languages:string[];availability:string;working_hours:string;github_url?:string|null;visible:boolean}
export type MatchProject={id:number;name:string;slug?:string|null;maximum_team_size:number;campus_id?:number|null;subscription_status:'subscribed'|'eligible';registration_status?:string|null}
export type MatchItem={id:number;project_id:number;project_name:string;created_at:string;profile:StudentProfile}
export type NotificationItem={id:number;type:string;title:string;body:string;payload:Record<string,unknown>;read:boolean;created_at:string}
export type PlatformTeam={id:number;project_id:number;project_name:string;name:string;description:string;maximum_members:number;available_spots:number;status:string;creator_id:number;members:{role:string;profile:StudentProfile}[]}
export type TeamInvitation={id:number;status:string;team:PlatformTeam;invited_by?:StudentProfile}
