import { Link, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import AuditProgress from './pages/AuditProgress';
import Report from './pages/Report';
import History from './pages/History';
import Compare from './pages/Compare';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-ink/10 bg-sand/80 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between gap-4">
          <Link to="/" className="font-display text-2xl text-ink tracking-tight">
            Readiness<span className="text-coral">Check</span>
          </Link>
          <nav className="flex gap-4 text-sm font-semibold text-sea">
            <Link to="/" className="hover:text-coral transition-colors">
              New audit
            </Link>
            <Link to="/history" className="hover:text-coral transition-colors">
              History
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/audit/:id" element={<AuditProgress />} />
          <Route path="/report/:id" element={<Report />} />
          <Route path="/history" element={<History />} />
          <Route path="/compare/:beforeId/:afterId" element={<Compare />} />
        </Routes>
      </main>

      <footer className="border-t border-ink/10 py-6 text-center text-xs text-ink/60 px-4">
        Scores are our readiness assessment (best-practice signals), not official Google rankings or AI
        citation scores. We audit and recommend only — we do not fix your site or guarantee results.
      </footer>
    </div>
  );
}
