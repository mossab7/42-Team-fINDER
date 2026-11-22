import { describe, expect, it } from 'vitest'
import type { ScanConfig } from '../types/api'
import { reconcileMetadataIds } from '../services/reconcileMetadata'

describe('reconcileMetadataIds',()=>{
 it('replaces stale demo identifiers with live metadata identifiers',()=>{
  const config:ScanConfig={campus_id:21,campus_name:'Benguerir',project_id:101,project_name:'ft_transcendence',promotion:{type:'cursus_year',year:2024},max_team_size:4,include_unavailable:false,force_refresh:false}
  const result=reconcileMetadataIds(config,[{id:21,name:'Benguerir'}],[{id:1337,name:'ft_transcendence'}])
  expect(result.project_id).toBe(1337)
  expect(result.campus_id).toBe(21)
 })
})
