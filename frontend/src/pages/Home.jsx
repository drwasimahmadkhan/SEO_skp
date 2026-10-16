import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createAudit } from '../api';

export default function Home() {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const audit = await createAudit(url.trim());
      navigate(`/audit/${audit.id}`);
    } catch (err) {
      setError(err.message || 'Could not start audit');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="relative overflow-hidden rounded-none min-h-[70vh] flex flex-col justify-center">
      <div
        className="absolute inset-0 -z-10 opacity-90"
        style={{
          backgroundImage:
            'linear-gradient(135deg, rgba(15,28,46,0.92), rgba(26,74,110,0.75)), url(https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1600&q=80)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div className="text-sand px-2 py-16 md:py-24 max-w-2xl animate-[fadeIn_0.7s_ease]">
        <p className="font-display text-4xl md:text-6xl leading-tight mb-3">ReadinessCheck</p>
        <h1 className="text-xl md:text-2xl font-semibold text-sand/95 mb-3">
          See what search and AI tools can — and cannot — learn from your site
        </h1>
        <p className="text-sand/80 mb-8 max-w-xl">
          Enter a URL for separate SEO, AEO, and GEO readiness scores, plain-language issues, and
          site-specific recommendations.
        </p>
        <form onSubmit={onSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            required
            placeholder="https://your-business.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 rounded-md border-0 px-4 py-3 text-ink shadow-lg focus:outline-none focus:ring-2 focus:ring-coral"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-coral px-6 py-3 font-semibold text-white hover:bg-coral/90 disabled:opacity-60 transition-transform hover:scale-[1.02]"
          >
            {loading ? 'Starting…' : 'Run audit'}
          </button>
        </form>
        {error && <p className="mt-4 text-sm bg-black/40 text-red-200 px-3 py-2 rounded">{error}</p>}
      </div>
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
      `}</style>
    </section>
  );
}
