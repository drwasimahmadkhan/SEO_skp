import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getAudit } from '../api';

export default function AuditProgress() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await getAudit(id);
        if (!alive) return;
        setAudit(data);
        if (data.status === 'done') navigate(`/report/${id}`, { replace: true });
        if (data.status === 'failed') setError(data.error_message || 'Audit failed');
      } catch (err) {
        if (alive) setError(err.message);
      }
    };
    tick();
    const t = setInterval(tick, 1500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [id, navigate]);

  const progress = audit?.progress ?? 0;

  return (
    <div className="max-w-xl mx-auto py-16 text-center">
      <h1 className="font-display text-3xl text-ink mb-2">Auditing your site</h1>
      <p className="text-sea mb-8">{audit?.progress_message || 'Connecting…'}</p>
      <div className="h-3 rounded-full bg-mist overflow-hidden">
        <div
          className="h-full bg-sea transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-3 text-sm text-ink/60">{progress}%</p>
      {error && <p className="mt-6 text-coral">{error}</p>}
    </div>
  );
}
