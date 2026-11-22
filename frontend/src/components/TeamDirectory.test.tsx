import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TeamDirectory } from './TeamDirectory'
describe('TeamDirectory',()=>{it('labels inferred capacity without claiming joinability',()=>{render(<TeamDirectory data={{items:[{id:1,name:'kernel-panic',project:'webserv',member_count:2,maximum_target_size:5,potential_spots:3,status:'in_progress',availability:'potential_capacity',classification_reason:'Size only.',members:[]}],total:1,page:1,page_size:20}} loading={false} status="" setStatus={vi.fn()} sort="size" setSort={vi.fn()}/>);expect(screen.getAllByText('Potential capacity')).toHaveLength(2);expect(screen.getByText('Size only.')).toBeInTheDocument()})})
