import { useDarkMode } from '@/hooks/useDarkMode'
import Sidebar from './Sidebar'
import MainArea from './MainArea'

export default function AppShell() {
  const { isDark, toggle } = useDarkMode()

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar isDark={isDark} onToggleDark={toggle} />
      <MainArea />
    </div>
  )
}
