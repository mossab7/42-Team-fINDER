import type { Campus, Project, ScanConfig } from '../types/api'

export function reconcileMetadataIds(config:ScanConfig,campuses?:Campus[],projects?:Project[]):ScanConfig {
 const campus=campuses?.find(item=>item.name===config.campus_name);const project=projects?.find(item=>item.name===config.project_name)
 const campus_id=campus?.id??config.campus_id;const project_id=project?.id??config.project_id
 return campus_id===config.campus_id&&project_id===config.project_id?config:{...config,campus_id,project_id}
}
