import { Routes, Route } from 'react-router-dom'
import AppShell from '@/components/layout/AppShell'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />} />
    </Routes>
  )
}
