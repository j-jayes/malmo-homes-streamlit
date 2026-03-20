import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App' // Assuming App.tsx exists at the root of src/

describe('App', () => {
  it('renders without crashing', () => {
    // This is a basic skeleton test to verify Vitest works
    render(<App />)
    expect(document.body).toBeInTheDocument()
  })
})
