import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Dashboard from './pages/Dashboard'
import Create from './pages/Create'
import MediaLibrary from './pages/MediaLibrary'
import EvidenceReview from './pages/EvidenceReview'
import CaptionStudio from './pages/CaptionStudio'
import History from './pages/History'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/create" element={<Create />} />
        <Route path="/media" element={<MediaLibrary />} />
        <Route path="/evidence/:collectionId" element={<EvidenceReview />} />
        <Route path="/studio/:collectionId" element={<CaptionStudio />} />
        <Route path="/history" element={<History />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
