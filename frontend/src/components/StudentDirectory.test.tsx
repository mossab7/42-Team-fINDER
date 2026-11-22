import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { StudentDirectory } from './StudentDirectory'

const student={id:1,login:'ada',display_name:'Ada Lovelace',campus:'Paris',promotion:'Cursus 2024',level:6.42,project_status:'searching_a_group',team_status:'searching_group' as const,profile_url:'https://profile.intra.42.fr/users/ada',classification_reason:'API status confirms search.',available_data:{}}
describe('StudentDirectory',()=>{it('renders, searches, and opens details',()=>{const setSearch=vi.fn();render(<StudentDirectory data={{items:[student],total:1,page:1,page_size:10}} loading={false} search="" setSearch={setSearch} status="" setStatus={vi.fn()} sort="login" setSort={vi.fn()} page={1} setPage={vi.fn()} exportUrl={()=>'/export'}/>);expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();fireEvent.change(screen.getByLabelText('Search students'),{target:{value:'ada'}});expect(setSearch).toHaveBeenCalledWith('ada');fireEvent.click(screen.getByText('Ada Lovelace'));expect(screen.getByText('API status confirms search.')).toBeInTheDocument()})})

it('renders a dedicated solo-project directory',()=>{
 const solo={...student,project_status:'in_progress',team_status:'working_solo' as const}
 render(<StudentDirectory mode="solo" data={{items:[solo],total:1,page:1,page_size:10}} loading={false} search="" setSearch={vi.fn()} status="" setStatus={vi.fn()} sort="login" setSort={vi.fn()} page={1} setPage={vi.fn()} exportUrl={()=>'/export'}/>)
 expect(screen.getByText('Students working on this project')).toBeInTheDocument()
 expect(screen.getAllByText('Working on project')).toHaveLength(2)
 expect(screen.getByText('Work status')).toBeInTheDocument()
})
