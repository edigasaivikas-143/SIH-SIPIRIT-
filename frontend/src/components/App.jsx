import MapViewer from './components/MapViewer'
import NLQueryBox from './components/NLQueryBox'

export default function App() {
  return (
    <div className="app-container">
      <NLQueryBox />
      <MapViewer />
    </div>
  )
}
