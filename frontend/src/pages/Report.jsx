import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { downloadPdf, getReport } from '../api';
import ScoreRing from '../components/ScoreRing';

const SEVERITIES = ['All', 'Critical', 'Warning', 'Info'];
const PILLARS = ['All', 'SEO', 'AEO', 'GEO'];

export default function Report() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [severity, setSeverity] = useState('All');
  const [pillar, setPillar] = useState('All');
  const [tab, setTab] = useState('issues');

  useEffect(() => {
    getReport(id)
      .then(setReport)
      .catch((e) => setError(e.message));
  }, [id]);

  const failed = useMemo(() => {
    if (!report) return [];
    return report.issues.filter((i) => !i.passed);
  }, [report]);

  const filtered = useMemo(() => {
    return failed.filter((i) => {
      if (severity !== 'All' && i.severity !== severity) return false;
      if (pillar !== 'All' && i.pillar !== pillar) return false;
      return true;
    });
  }, [failed, severity, pillar]);

  const quickWins = useMemo(() => {
    if (!report) return [];
    return report.recommendations.filter((r) => r.is_quick_win);
  }, [report]);

  if (error) return <p className="text-coral">{error}</p>;
  if (!report) return <p className="text-sea">Loading report…</p>;

  const score = report.score;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-sea uppercase tracking-wide">Audit report</p>
          <h1 className="font-display text-3xl text-ink break-all">{report.audit.url}</h1>
          <p className="text-sm text-ink/60 mt-1">
            {score?.grade || '—'} · {report.audit.completed_at || report.audit.created_at}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => downloadPdf(id)}
            className="px-4 py-2 bg-sea text-white rounded-md text-sm font-semibold hover:bg-ink transition-colors"
          >
            Download PDF
          </button>
          <Link
            to="/history"
            className="px-4 py-2 border border-sea/30 text-sea rounded-md text-sm font-semibold hover:bg-mist"
          >
            History
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap justify-around gap-6 py-6 bg-white/60 border border-ink/5">
        <ScoreRing label="Overall" value={score?.overall} size={110} />
        <ScoreRing label="SEO" value={score?.seo} />
        <ScoreRing label="AEO" value={score?.aeo} />
        <ScoreRing label="GEO" value={score?.geo} />
      </div>

      {score?.breakdown?.seo_categories && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
          {Object.entries(score.breakdown.seo_categories).map(([k, v]) => (
            <div key={k} className="bg-mist/80 px-3 py-2">
              <div className="text-ink/60 text-xs">{k}</div>
              <div className="font-semibold text-ink">{Math.round(v)}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-b border-ink/10 pb-2">
        {['issues', 'quickwins', 'recommendations', 'aeo', 'entities'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-sm font-semibold rounded-md transition-colors ${
              tab === t ? 'bg-ink text-sand' : 'text-sea hover:bg-mist'
            }`}
          >
            {t === 'quickwins'
              ? 'Quick Wins'
              : t === 'aeo'
                ? 'AEO Answerability'
                : t === 'entities'
                  ? 'Entity Graph'
                  : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'issues' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="border border-ink/15 bg-white px-3 py-2 text-sm"
            >
              {SEVERITIES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
            <select
              value={pillar}
              onChange={(e) => setPillar(e.target.value)}
              className="border border-ink/15 bg-white px-3 py-2 text-sm"
            >
              {PILLARS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
            <span className="text-sm text-ink/50 self-center">{filtered.length} issues</span>
          </div>
          <ul className="space-y-3">
            {filtered.map((issue) => (
              <li key={issue.id} className="border-l-4 border-coral/80 bg-white/70 px-4 py-3">
                <div className="flex flex-wrap gap-2 text-xs font-semibold mb-1">
                  <span className="text-coral">{issue.severity}</span>
                  <span className="text-sea">
                    {issue.pillar} · {issue.category}
                  </span>
                </div>
                <div className="font-semibold text-ink">{issue.title}</div>
                <p className="text-sm text-ink/70 mt-1">{issue.message}</p>
              </li>
            ))}
            {!filtered.length && <p className="text-ink/50">No issues match these filters.</p>}
          </ul>
        </div>
      )}

      {tab === 'quickwins' && (
        <ul className="space-y-3">
          {quickWins.map((r) => (
            <li key={r.id} className="bg-moss/10 border border-moss/20 px-4 py-3 text-sm">
              {r.text}
            </li>
          ))}
          {!quickWins.length && <p className="text-ink/50">No quick wins flagged for this audit.</p>}
        </ul>
      )}

      {tab === 'recommendations' && (
        <ul className="space-y-3">
          {report.recommendations.map((r) => (
            <li key={r.id} className="bg-white/70 px-4 py-3 text-sm border border-ink/5">
              <span className="text-xs text-sea font-semibold uppercase mr-2">{r.source}</span>
              {r.text}
            </li>
          ))}
        </ul>
      )}

      {tab === 'aeo' && (
        <ul className="space-y-4">
          {report.questions.map((q) => (
            <li key={q.id} className="bg-white/70 px-4 py-3 border border-ink/5">
              <div className="flex flex-wrap justify-between gap-2">
                <p className="font-semibold text-ink">{q.question}</p>
                <span
                  className={`text-xs font-bold px-2 py-1 ${
                    q.answerability === 'Clear'
                      ? 'bg-moss/15 text-moss'
                      : q.answerability === 'Partial'
                        ? 'bg-coral/15 text-coral'
                        : 'bg-ink/10 text-ink/70'
                  }`}
                >
                  {q.answerability}
                </span>
              </div>
              {q.evidence && <p className="text-sm text-ink/60 mt-2">Evidence: {q.evidence}</p>}
              {q.suggested_rewrite && (
                <p className="text-sm text-sea mt-2">{q.suggested_rewrite}</p>
              )}
            </li>
          ))}
          {!report.questions.length && <p className="text-ink/50">No AEO questions generated.</p>}
        </ul>
      )}

      {tab === 'entities' && (
        <div className="space-y-4">
          {report.entities.map((ent) => (
            <div key={ent.id} className="bg-white/70 border border-ink/5 p-4 space-y-3">
              <h3 className="font-display text-xl">{ent.name}</h3>
              <p className="text-sm text-ink/60">{ent.entity_type}</p>
              {ent.attributes && (
                <pre className="text-xs bg-mist p-3 overflow-auto">
                  {JSON.stringify(ent.attributes, null, 2)}
                </pre>
              )}
              {ent.missing?.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-coral mb-1">What AI may miss</p>
                  <ul className="list-disc list-inside text-sm">
                    {ent.missing.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              {ent.graph_summary && (
                <div>
                  <p className="text-sm font-semibold mb-1">
                    Graph · {ent.graph_summary.node_count} nodes · {ent.graph_summary.edge_count}{' '}
                    edges
                  </p>
                  <ul className="text-sm space-y-1">
                    {(ent.relations || []).map((r, idx) => (
                      <li key={idx} className="text-ink/70">
                        {r.from} —{r.relation}→ {r.to}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {ent.schema_draft && (
                <div>
                  <p className="text-sm font-semibold mb-1">LocalBusiness JSON-LD draft</p>
                  <pre className="text-xs bg-mist p-3 overflow-auto">
                    {JSON.stringify(ent.schema_draft, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
          {!report.entities.length && <p className="text-ink/50">No entity graph for this audit.</p>}
        </div>
      )}

      <p className="text-xs text-ink/50">{report.disclaimer}</p>
    </div>
  );
}
