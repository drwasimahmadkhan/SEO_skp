import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listAudits } from '../api';

export default function History() {
  const [audits, setAudits] = useState([]);
  const [error, setError] = useState('');
  const [beforeId, setBeforeId] = useState('');
  const [afterId, setAfterId] = useState('');

  useEffect(() => {
    listAudits()
      .then(setAudits)
      .catch((e) => setError(e.message));
  }, []);

  const done = useMemo(() => audits.filter((a) => a.status === 'done'), [audits]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Audit history</h1>
        <p className="text-sea text-sm mt-1">Stored for this browser session only (anonymous UUID).</p>
      </div>

      {error && <p className="text-coral">{error}</p>}

      <div className="bg-white/60 border border-ink/5 p-4 space-y-3">
        <h2 className="font-semibold text-ink">Before / after compare</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm">
            Before
            <select
              className="block mt-1 border border-ink/15 px-3 py-2 min-w-[220px]"
              value={beforeId}
              onChange={(e) => setBeforeId(e.target.value)}
            >
              <option value="">Select…</option>
              {done.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.url} · {a.created_at}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            After
            <select
              className="block mt-1 border border-ink/15 px-3 py-2 min-w-[220px]"
              value={afterId}
              onChange={(e) => setAfterId(e.target.value)}
            >
              <option value="">Select…</option>
              {done.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.url} · {a.created_at}
                </option>
              ))}
            </select>
          </label>
          {beforeId && afterId ? (
            <Link
              to={`/compare/${beforeId}/${afterId}`}
              className="px-4 py-2 bg-coral text-white text-sm font-semibold rounded-md"
            >
              Compare
            </Link>
          ) : (
            <button type="button" disabled className="px-4 py-2 bg-ink/20 text-ink/40 text-sm rounded-md">
              Compare
            </button>
          )}
        </div>
      </div>

      <ul className="divide-y divide-ink/10 bg-white/50 border border-ink/5">
        {audits.map((a) => (
          <li key={a.id} className="px-4 py-3 flex flex-wrap justify-between gap-2 items-center">
            <div>
              <div className="font-semibold text-ink break-all">{a.url}</div>
              <div className="text-xs text-ink/50">
                {a.status} · {a.progress}% · {a.created_at}
              </div>
            </div>
            {a.status === 'done' ? (
              <Link to={`/report/${a.id}`} className="text-sm font-semibold text-sea hover:text-coral">
                View report
              </Link>
            ) : (
              <Link to={`/audit/${a.id}`} className="text-sm font-semibold text-sea">
                Resume
              </Link>
            )}
          </li>
        ))}
        {!audits.length && !error && <li className="px-4 py-8 text-ink/50 text-center">No audits yet.</li>}
      </ul>
    </div>
  );
}
