export type PromotionType = 'cursus_year' | 'piscine' | 'date_range'
export interface Campus { id: number; name: string; city?: string; country?: string }
export interface Project { id: number; name: string; slug?: string }
export interface ProjectConfiguration { project_id:number; campus_id:number; project_session_id?:number; session_campus_id?:number; solo:boolean; min_team_size:number; max_team_size:number; maximum_source:'solo'|'max_people'|'group_rule'|'fallback'; fetched_at:string; source:'demo'|'live' }
export interface MetadataResponse<T> { items: T[]; fetched_at: string; source: 'demo' | 'live' }
export interface AuthStatus { auth_required: boolean; authenticated: boolean; user?: { id:number; login:string; display_name:string } | null }
export interface ScanConfig { campus_id: number; campus_name: string; project_id: number; project_name: string; promotion: { type: PromotionType; year?: number; month?: number; start_date?: string; end_date?: string }; max_team_size: number; project_solo?: boolean; include_unavailable: boolean; force_refresh: boolean }
export interface ScanSummary { total_eligible_students: number; students_without_active_teams: number; teams_below_size_limit: number; potentially_available_spots: number; confirmed_joinable_spots: number; students_working_on_project:number; excluded_blackholed_students:number }
export interface Scan { id: string; status: 'queued'|'running'|'completed'|'failed'; progress_stage: string; completed_work: number; total_work: number; configuration: ScanConfig; summary?: ScanSummary; warnings: string[]; error?: string; source: 'demo'|'live'; created_at: string; completed_at?: string; data_retrieved_at?: string }
export type StudentStatus = 'searching_group'|'registered_without_team'|'not_registered'|'uncertain'|'active_team'|'working_solo'|'completed'
export interface Student { id: number; login: string; display_name: string; image_url?: string; campus: string; promotion: string; level?: number; project_status: string; team_status: StudentStatus; profile_url: string; classification_reason: string; available_data: Record<string, unknown> }
export interface TeamMember { id: number; login: string; display_name: string; image_url?: string; profile_url: string; in_selected_promotion: boolean }
export interface Team { id: number; name: string; project: string; member_count: number; maximum_target_size: number; potential_spots: number; status: string; members: TeamMember[]; availability: 'confirmed_joinable'|'potential_capacity'|'unavailable'|'uncertain'; classification_reason: string }
export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number; data_retrieved_at?: string }
