import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Avatar } from './Avatar'

describe('Avatar', () => {
  it('loads official 42 images through the same-origin proxy', () => {
    render(<Avatar imageUrl="https://cdn.intra.42.fr/users/ada.jpg" login="ada" displayName="Ada Lovelace"/>)
    const image = screen.getByAltText('Ada Lovelace avatar')
    expect(image.getAttribute('src')).toBe('/api/avatars?url=https%3A%2F%2Fcdn.intra.42.fr%2Fusers%2Fada.jpg')
  })

  it('falls back to initials when the image request fails', () => {
    render(<Avatar imageUrl="https://cdn.intra.42.fr/users/ada.jpg" login="ada" displayName="Ada Lovelace"/>)
    fireEvent.error(screen.getByAltText('Ada Lovelace avatar'))
    expect(screen.getByTestId('avatar-fallback-ada')).toHaveTextContent('AD')
  })
})
