import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { compareAudits } from '../api';
import ScoreRing from '../components/ScoreRing';

function Delta({ label, value }) {
  const positive = value > 0;
  const negative = value < 0;
  return (
    <div className="text-center">
      <div
        className={`font-display text-2xl ${
          positive ? 'text-moss' : negative ? 'text-coral' : 'text-ink'
        }`}
      >
        {positive ? '+' : ''}
        {value}
      </div>
      <div className="text-xs text-sea font-semibold">{label}</div>
    </div>
  );
}

export default function Compare() {
  const { beforeId, afterId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    compareAudits(beforeId, afterId)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [beforeId, afterId]);

  if (error) return <p className="text-coral">{error}</p>;
  if (!data) return <p className="text-sea">Loading comparison…</p>;

  const { before, after, score_delta, resolved_issue_ids, new_issue_ids } = data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Before / after</h1>
        <p className="text-sm text-sea break-all mt-1">{before.audit.url}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white/60 border border-ink/5 p-4">
          <h2 className="font-semibold mb-4">Before</h2>
          <div className="flex justify-around">
            <ScoreRing label="Overall" value={before.score?.overall} size={80} />
            <ScoreRing label="SEO" value={before.score?.seo} size={72} />
            <ScoreRing label="AEO" value={before.score?.aeo} size={72} />
            <ScoreRing label="GEO" value={before.score?.geo} size={72} />
          </div>
          <Link to={`/report/${before.audit.id}`} className="text-sm text-sea font-semibold mt-4 inline-block">
            Open report
          </Link>
        </div>
        <div className="bg-white/60 border border-ink/5 p-4">
          <h2 className="font-semibold mb-4">After</h2>
          <div className="flex justify-around">
            <ScoreRing label="Overall" value={after.score?.overall} size={80} />
            <ScoreRing label="SEO" value={after.score?.seo} size={72} />
            <ScoreRing label="AEO" value={after.score?.aeo} size={72} />
            <ScoreRing label="GEO" value={after.score?.geo} size={72} />
          </div>
          <Link to={`/report/${after.audit.id}`} className="text-sm text-sea font-semibold mt-4 inline-block">
            Open report
          </Link>
        </div>
      </div>

      <div className="flex justify-around bg-mist/80 py-6">
        <Delta label="Overall" value={score_delta.overall} />
        <Delta label="SEO" value={score_delta.seo} />
        <Delta label="AEO" value={score_delta.aeo} />
        <Delta label="GEO" value={score_delta.geo} />
      </div>

      <div className="grid md:grid-cols-2 gap-6 text-sm">
        <div>
          <h3 className="font-semibold text-moss mb-2">Resolved checks</h3>
          <ul className="list-disc list-inside space-y-1">
            {resolved_issue_ids.map((id) => (
              <li key={id}>{id}</li>
            ))}
            {!resolved_issue_ids.length && <li className="text-ink/50 list-none">None</li>}
          </ul>
        </div>
        <div>
          <h3 className="font-semibold text-coral mb-2">New issues</h3>
          <ul className="list-disc list-inside space-y-1">
            {new_issue_ids.map((id) => (
              <li key={id}>{id}</li>
            ))}
            {!new_issue_ids.length && <li className="text-ink/50 list-none">None</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
