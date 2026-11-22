import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SearchForm } from './SearchForm'
import type { ScanConfig } from '../types/api'

const config:ScanConfig={campus_id:1,campus_name:'Paris',project_id:101,project_name:'ft_transcendence',promotion:{type:'cursus_year',year:2024},max_team_size:5,include_unavailable:false,force_refresh:false}
describe('SearchForm',()=>{it('renders selections and submits',()=>{const submit=vi.fn();render(<SearchForm config={config} setConfig={vi.fn()} campuses={[{id:1,name:'Paris'}]} projects={[{id:101,name:'ft_transcendence'}]} years={[2024]} loading={false} onSubmit={submit} scanning={false}/>);expect(screen.getByDisplayValue('Paris')).toBeInTheDocument();expect(screen.getByDisplayValue('ft_transcendence')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:/find teammates/i}));expect(submit).toHaveBeenCalled()})})

it('opens searchable campus and project menus and applies selections',()=>{
 const setConfig=vi.fn()
 render(<SearchForm config={config} setConfig={setConfig} campuses={[{id:1,name:'Paris'},{id:3,name:'Berlin',city:'Berlin'}]} projects={[{id:101,name:'ft_transcendence'},{id:104,name:'Libft'}]} years={[2024]} loading={false} onSubmit={vi.fn()} scanning={false}/>)
 fireEvent.change(screen.getByRole('combobox',{name:'Campus'}),{target:{value:'Berl'}})
 expect(screen.queryByRole('option',{name:'Paris'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('option',{name:/Berlin/}))
 expect(setConfig).toHaveBeenCalledWith(expect.objectContaining({campus_id:3,campus_name:'Berlin'}))
 fireEvent.change(screen.getByRole('combobox',{name:'Project'}),{target:{value:'Lib'}})
 expect(screen.queryByRole('option',{name:'ft_transcendence'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('option',{name:'Libft'}))
 expect(setConfig).toHaveBeenCalledWith(expect.objectContaining({project_id:104,project_name:'Libft'}))
})

it('shows the API team range and solo-project action',()=>{
 const {rerender}=render(<SearchForm config={config} setConfig={vi.fn()} campuses={[{id:1,name:'Paris'}]} projects={[{id:101,name:'ft_transcendence'}]} years={[2024]} projectConfiguration={{project_id:101,campus_id:1,project_session_id:10,session_campus_id:1,solo:false,min_team_size:4,max_team_size:5,maximum_source:'group_rule',fetched_at:'2026-01-01',source:'live'}} loading={false} onSubmit={vi.fn()} scanning={false}/>)
 expect(screen.getByText(/42 team range: 4–5/)).toBeInTheDocument()
 expect(within(screen.getByLabelText('Maximum team size')).getAllByRole('option').map(option=>option.textContent)).toEqual(['4','5'])
 rerender(<SearchForm config={{...config,max_team_size:1,project_solo:true}} setConfig={vi.fn()} campuses={[{id:1,name:'Paris'}]} projects={[{id:104,name:'Libft'}]} years={[2024]} projectConfiguration={{project_id:104,campus_id:1,project_session_id:11,session_campus_id:1,solo:true,min_team_size:1,max_team_size:1,maximum_source:'solo',fetched_at:'2026-01-01',source:'live'}} loading={false} onSubmit={vi.fn()} scanning={false}/>)
 expect(screen.getByRole('button',{name:/find active students/i})).toBeInTheDocument()
 expect(screen.getByLabelText('Maximum team size')).toBeDisabled()
})
