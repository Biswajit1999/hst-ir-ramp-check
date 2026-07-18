import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Beaker,
  CheckCircle2,
  Database,
  Download,
  FileText,
  GitCommit,
  Layers3,
  ListChecks,
  ShieldCheck,
  Telescope,
} from 'lucide-react';

const HubbleHero = lazy(() => import('./HubbleHero.jsx'));
const panel = 'lab-panel rounded-[1.6rem] border border-amber-950/15 bg-[#fffaf1] p-5 md:p-6';

function useJson(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    fetch(path)
      .then((response) => {
        if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (!cancelled) setState({ data: null, error, loading: false });
      });

    return () => {
      cancelled = true;
    };
  }, [path]);

  return state;
}

function MetricCard({ metric, index }) {
  const hasUncertainty = metric.uncertainty_low != null && metric.uncertainty_high != null;

  return (
    <article className="metric-card relative overflow-hidden rounded-2xl border border-amber-950/15 bg-[#fffaf1] p-5">
      <span className="absolute right-4 top-3 font-mono text-[0.65rem] tracking-[0.2em] text-[#a86537]">
        READ {String(index + 1).padStart(2, '0')}
      </span>
      <p className="max-w-[80%] text-xs font-semibold uppercase tracking-[0.12em] text-[#765545]">
        {metric.name.replace(/_/g, ' ')}
      </p>
      <p className="mt-5 font-mono text-2xl font-semibold text-[#2b1912]">
        {typeof metric.estimate === 'number' ? metric.estimate.toPrecision(4) : String(metric.estimate)}
        <span className="ml-2 text-xs font-normal text-[#765545]">{metric.units}</span>
      </p>
      {hasUncertainty && (
        <p className="mt-2 text-xs text-[#765545]">
          95% CI [{metric.uncertainty_low.toPrecision(3)}, {metric.uncertainty_high.toPrecision(3)}]
        </p>
      )}
      <p className="mt-2 text-xs text-[#9b6f54]">sample size n = {metric.sample_size}</p>
    </article>
  );
}

function Section({ icon: Icon, title, eyebrow, className = '', children }) {
  return (
    <article className={`${panel} ${className}`}>
      <div className="mb-5 flex items-center gap-3 border-b border-amber-950/10 pb-4">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-[#f0d5b5] text-[#7f3f22]">
          <Icon size={17} aria-hidden="true" />
        </span>
        <div>
          {eyebrow && <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[#9b6f54]">{eyebrow}</p>}
          <h2 className="display-font text-xl font-semibold text-[#2b1912]">{title}</h2>
        </div>
      </div>
      {children}
    </article>
  );
}

function inverseNormalCDF(p) {
  if (p <= 0 || p >= 1) return NaN;
  const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
  const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
  const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
  const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
  const pLow = 0.02425;
  const pHigh = 1 - pLow;
  let q;
  let r;

  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
      / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p <= pHigh) {
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
      / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  q = Math.sqrt(-2 * Math.log(1 - p));
  return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
    / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
}

function ConfidenceExplorer({ metrics }) {
  const withCI = useMemo(
    () => (metrics || []).filter((metric) => metric.uncertainty_low != null && metric.uncertainty_high != null),
    [metrics],
  );
  const [selected, setSelected] = useState(null);
  const [confidence, setConfidence] = useState(95);

  useEffect(() => {
    if (!selected && withCI.length > 0) setSelected(withCI[0].name);
  }, [withCI, selected]);

  if (withCI.length === 0) return null;
  const metric = withCI.find((item) => item.name === selected) ?? withCI[0];
  const sigma = ((metric.uncertainty_high - metric.uncertainty_low) / 2) / 1.959963984540054;
  const zLevel = inverseNormalCDF(0.5 + confidence / 200);
  const lo = metric.estimate - zLevel * sigma;
  const hi = metric.estimate + zLevel * sigma;

  return (
    <Section icon={Beaker} title="Confidence-level explorer" eyebrow="Sensitivity tool">
      <p className="mb-4 text-xs leading-relaxed text-[#765545]">
        This client-side approximation rescales the reported 95% bootstrap interval under a normal
        sampling assumption. It does not rerun the bootstrap; the metric card retains the computed result.
      </p>
      {withCI.length > 1 && (
        <select
          className="mb-4 w-full rounded-lg border border-[#c89169] bg-white px-3 py-2 text-sm text-[#2b1912]"
          value={metric.name}
          onChange={(event) => setSelected(event.target.value)}
        >
          {withCI.map((item) => (
            <option key={item.name} value={item.name}>{item.name.replace(/_/g, ' ')}</option>
          ))}
        </select>
      )}
      <label className="flex items-center justify-between text-sm text-[#5d4033]">
        <span>Confidence level</span>
        <span className="font-mono">{confidence.toFixed(1)}%</span>
      </label>
      <input
        type="range"
        min="50"
        max="99.9"
        step="0.1"
        value={confidence}
        onChange={(event) => setConfidence(Number(event.target.value))}
        className="mt-2 w-full accent-[#a6532c]"
      />
      <p className="mt-4 font-mono text-2xl font-semibold text-[#2b1912]">
        [{lo.toPrecision(4)}, {hi.toPrecision(4)}]
        <span className="ml-2 text-sm font-normal text-[#765545]">{metric.units}</span>
      </p>
    </Section>
  );
}

const WARNING_RULES = [
  {
    matches: (warning) => /only \d+ reads survive DQ exclusion/i.test(warning),
    title: 'Insufficient DQ-valid reads',
    description: 'Fit candidates excluded because fewer than four reads remained after required data-quality masking.',
    tone: 'quality',
  },
  {
    matches: (warning) => /covariance condition number/i.test(warning),
    title: 'Ill-conditioned fits rejected',
    description: 'Unstable covariance estimates exceeded the configured condition-number threshold and were not reported as measurements.',
    tone: 'quality',
  },
  {
    matches: (warning) => /below minimum_sample_size/i.test(warning),
    title: 'Underpowered fluence bins',
    description: 'These bins remain visible, but their sample sizes do not meet the configured threshold for interval estimation.',
    tone: 'limitation',
  },
  {
    matches: (warning) => /did not converge|non-?convergent|convergence/i.test(warning),
    title: 'Non-convergent fits rejected',
    description: 'Candidates without a converged fit were excluded by the analysis quality gate.',
    tone: 'quality',
  },
  {
    matches: (warning) => /implausible|outside (the )?physical|physical range/i.test(warning),
    title: 'Outside physical range',
    description: 'Candidate values outside the configured physical range were rejected.',
    tone: 'quality',
  },
  {
    matches: (warning) => /checksum|schema|corrupt|fatal|zero[- ]tolerance/i.test(warning),
    title: 'Data-integrity failures',
    description: 'These entries indicate a failed integrity or schema requirement and require attention.',
    tone: 'failure',
  },
];

function groupWarnings(warnings) {
  const groups = new Map();

  warnings.forEach((warning) => {
    const rule = WARNING_RULES.find((candidate) => candidate.matches(warning)) ?? {
      title: 'Other recorded notices',
      description: 'Additional pipeline notices retained for complete auditability.',
      tone: 'limitation',
    };
    if (!groups.has(rule.title)) groups.set(rule.title, { ...rule, entries: [] });
    groups.get(rule.title).entries.push(warning);
  });

  return [...groups.values()];
}

function WarningSummary({ state }) {
  const records = useMemo(() => (Array.isArray(state.data) ? state.data : []), [state.data]);
  const groups = useMemo(() => groupWarnings(records), [records]);

  if (state.loading) return <p className="text-sm text-[#765545]">Loading recorded notices…</p>;
  if (state.error) {
    return (
      <div className="rounded-xl border border-red-800/30 bg-red-50 p-4 text-sm text-red-900">
        warnings.json could not be loaded: {String(state.error)}
      </div>
    );
  }
  if (records.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
        <CheckCircle2 size={17} aria-hidden="true" />
        No warnings recorded in results/warnings.json.
      </div>
    );
  }

  const failureCount = groups
    .filter((group) => group.tone === 'failure')
    .reduce((total, group) => total + group.entries.length, 0);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm leading-relaxed text-[#5d4033]">
          <strong>{records.length} analysis notices</strong> are retained for auditability and grouped
          below. Quality-control exclusions are expected records, not evidence of a crashed pipeline.
        </p>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${failureCount > 0 ? 'bg-red-100 text-red-900' : 'bg-emerald-100 text-emerald-900'}`}>
          {failureCount > 0 ? `${failureCount} integrity failures` : 'No integrity failures'}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {groups.map((group) => (
          <div key={group.title} className={`warning-group warning-${group.tone} rounded-xl border p-4`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-[#2b1912]">{group.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-[#765545]">{group.description}</p>
              </div>
              <span className="rounded-full bg-white/80 px-3 py-1 font-mono text-sm font-bold text-[#5b2e1c]">
                {group.entries.length}
              </span>
            </div>
          </div>
        ))}
      </div>

      <details className="raw-warning-list mt-4 rounded-xl border border-amber-950/15 bg-[#f8ebdb] p-4">
        <summary className="cursor-pointer font-semibold text-[#673722]">
          Show all {records.length} raw entries from warnings.json
        </summary>
        <ol className="mt-4 max-h-96 space-y-2 overflow-auto border-t border-amber-950/10 pt-4 font-mono text-[0.7rem] leading-relaxed text-[#60483d]">
          {records.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}
        </ol>
      </details>
    </div>
  );
}

function FigureGallery({ figures }) {
  return (
    <div className="figure-grid grid gap-4 md:grid-cols-2">
      {figures.map((figure, index) => (
        <figure
          key={figure.id}
          className={`group overflow-hidden rounded-2xl border border-amber-950/15 bg-[#f6e7d5] p-3 ${index === 0 ? 'md:col-span-2' : ''}`}
        >
          <div className="overflow-hidden rounded-xl bg-white">
            <img
              src={`./figures/${figure.id}.svg`}
              alt={figure.label}
              className={`w-full transition duration-500 group-hover:scale-[1.015] ${index === 0 ? 'max-h-[34rem] object-contain' : ''}`}
              onError={(event) => { event.currentTarget.style.display = 'none'; }}
            />
          </div>
          <figcaption className="flex items-center justify-between gap-3 px-2 pb-1 pt-3 text-sm font-medium text-[#5d4033]">
            <span>{figure.label}</span>
            <span className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-[#a86537]">
              Figure {String(index + 1).padStart(2, '0')}
            </span>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export default function App() {
  const project = useJson('./project.json');
  const summary = useJson('./results/summary.json');
  const warnings = useJson('./results/warnings.json');
  const benchmarks = useJson('./results/benchmarks.json');

  if (project.loading) {
    return <main className="grid min-h-screen place-items-center bg-[#1c100b] text-[#f4d6b0]">Loading project record…</main>;
  }
  if (project.error || !project.data) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#1c100b] px-6 text-amber-200">
        Could not load project.json: {String(project.error)}
      </main>
    );
  }

  const p = project.data;
  const isDemo = summary.data?.data_kind === 'synthetic_smoke_test' || summary.data?.data_kind === 'synthetic_demo';

  return (
    <main className="infrared-page min-h-screen">
      <header className="mission-hero relative overflow-hidden border-b border-[#d28a52]/30">
        <div className="hero-orbit" aria-hidden="true" />
        <div className="relative mx-auto grid max-w-7xl gap-8 px-5 py-8 md:px-8 lg:grid-cols-[1.12fr_0.88fr] lg:items-center lg:py-14">
          <div>
            <div className="mb-8 flex items-center gap-3 text-xs uppercase tracking-[0.25em] text-[#e9ae74]">
              <span className="h-px w-10 bg-[#d9884d]" />
              {p.category}
            </div>
            <h1 className="display-font max-w-4xl text-4xl font-semibold leading-[1.04] text-[#fff5e7] md:text-6xl">
              {p.title}
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-relaxed text-[#dec4ae] md:text-lg">{p.question}</p>
            <div className="mt-8 flex flex-wrap gap-2 text-xs">
              <span className="hero-pill">{p.status}</span>
              <span className="hero-pill">Priority {p.priority}/10</span>
              <span className="hero-pill">{p.dataMode}</span>
              {summary.data && (
                <span className={`hero-pill ${isDemo ? 'hero-pill-demo' : 'hero-pill-real'}`}>
                  {isDemo ? 'SYNTHETIC DEMO RESULTS' : 'REAL DATA RESULTS'}
                </span>
              )}
            </div>
          </div>

          <Suspense fallback={<div className="h-[22rem] animate-pulse rounded-[2rem] border border-amber-200/10 bg-white/5" />}>
            <HubbleHero />
          </Suspense>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-10 md:px-8 md:py-14">
        {isDemo && (
          <div className="mb-8 flex items-start gap-3 rounded-2xl border border-amber-800/30 bg-amber-100 p-4 text-sm text-amber-950">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
            The metrics and figures below were generated from clearly labelled synthetic demo data,
            not real WFC3/IR observations. Real-data outputs replace them after the archive pipeline runs.
          </div>
        )}

        <section aria-labelledby="metrics-title">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#a6532c]">Detector ledger</p>
              <h2 id="metrics-title" className="display-font mt-1 text-3xl font-semibold text-[#2b1912]">Measured outputs</h2>
            </div>
            <p className="font-mono text-xs text-[#765545]">values loaded from results/summary.json</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {summary.data?.metrics?.map((metric, index) => (
              <MetricCard key={metric.name} metric={metric} index={index} />
            ))}
            {!summary.data && (
              <article className={panel}>
                <p className="text-sm text-[#765545]">Result status</p>
                <p className="mt-2 font-mono text-xl font-semibold text-[#2b1912]">NO RESULTS YET</p>
                <p className="mt-1 text-xs text-[#9b6f54]">Run scripts/run_analysis.py first.</p>
              </article>
            )}
          </div>
        </section>

        <div className="mt-8">
          <ConfidenceExplorer metrics={summary.data?.metrics} />
        </div>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.65fr_0.75fr] lg:items-start">
          <Section icon={Layers3} title="Figure gallery" eyebrow="Publication figures">
            <FigureGallery figures={p.figures} />
          </Section>

          <div className="grid gap-6 lg:sticky lg:top-6">
            <Section icon={ShieldCheck} title="Provenance boundary" eyebrow="Scope">
              <p className="text-sm leading-relaxed text-[#5d4033]">{p.novelty}</p>
              <div className="mt-5 flex items-start gap-2 rounded-xl border border-[#bb6c3b]/25 bg-[#f7dfc2] p-4 text-sm text-[#673722]">
                <AlertTriangle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                Results are public-ready only after validation and provenance checks pass.
              </div>
              {summary.data?.provenance && (
                <dl className="mt-5 space-y-3 text-xs text-[#5d4033]">
                  <div className="flex items-center gap-2"><GitCommit size={14} /><dt>git commit</dt><dd className="ml-auto font-mono">{summary.data.provenance.git_commit}</dd></div>
                  <div className="flex items-center gap-2"><FileText size={14} /><dt>config sha256</dt><dd className="ml-auto max-w-[9rem] truncate font-mono">{summary.data.provenance.config_sha256 ?? 'n/a'}</dd></div>
                  <div className="flex items-center gap-2"><Beaker size={14} /><dt>package version</dt><dd className="ml-auto font-mono">{summary.data.provenance.package_version}</dd></div>
                </dl>
              )}
            </Section>

            <Section icon={ListChecks} title="Validation contract" eyebrow="Acceptance gates">
              <ul className="space-y-3 text-sm text-[#5d4033]">
                {p.validationContract.map((item) => (
                  <li key={item} className="flex gap-2"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#9a512e]" />{item}</li>
                ))}
              </ul>
            </Section>
          </div>
        </section>

        <section className="mt-8">
          <Section icon={AlertTriangle} title="Warnings and exclusions" eyebrow="Transparent reporting">
            <WarningSummary state={warnings} />
          </Section>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <Section icon={Telescope} title="Methodology" eyebrow="Up-the-ramp audit">
            <p className="text-sm leading-7 text-[#5d4033]">{p.methodology}</p>
          </Section>
          <Section icon={AlertOctagon} title="Assumptions and limitations" eyebrow="Interpretive boundary">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[#a6532c]">Assumptions</p>
            <ul className="mb-6 space-y-3 text-sm leading-relaxed text-[#5d4033]">
              {p.assumptions.map((item) => <li key={item} className="border-l-2 border-[#d59b6e] pl-3">{item}</li>)}
            </ul>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[#a6532c]">Limitations</p>
            <ul className="space-y-3 text-sm leading-relaxed text-[#5d4033]">
              {p.limitations.map((item) => <li key={item} className="border-l-2 border-[#d59b6e] pl-3">{item}</li>)}
            </ul>
          </Section>
        </section>

        <footer className="mt-8 grid gap-6 md:grid-cols-2">
          <Section icon={Download} title="Downloads and manifest" eyebrow="Machine-readable outputs">
            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <a className="download-link" href="./manifest.csv" download>data/manifest.csv</a>
              <a className="download-link" href="./results/summary.json" download>results/summary.json</a>
              <a className="download-link" href="./results/warnings.json" download>results/warnings.json</a>
              {benchmarks.data && <a className="download-link" href="./results/benchmarks.json" download>results/benchmarks.json</a>}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-[#765545]">
              The manifest records product ID, source URL, retrieval time, checksum, file size,
              selection reason, and archive terms for every real product used.
            </p>
          </Section>
          <Section icon={Database} title="Citation and licence" eyebrow="Reuse">
            <p className="text-sm text-[#5d4033]">Author: {p.citation.author}</p>
            <p className="mt-2 text-sm text-[#5d4033]">Licence: {p.citation.license}</p>
            <a className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[#8a4224] underline-offset-4 hover:underline" href={p.citation.repository}>
              Repository record <span aria-hidden="true">↗</span>
            </a>
          </Section>
        </footer>
      </div>
    </main>
  );
}
