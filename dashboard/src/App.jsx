import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom';
import { Activity, MessageSquare, DollarSign, Loader2, ArrowRight, Calendar, ExternalLink } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// API Base URL
const API_BASE = 'http://localhost:8000/api';

// --- Components ---

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-50 font-sans selection:bg-indigo-500/30">
      <nav className="fixed top-0 w-full border-b border-white/10 bg-slate-900/50 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              P
            </div>
            <span className="font-bold text-lg tracking-tight">Pulse<span className="text-white/50">Dashboard</span></span>
          </Link>
          <div className="flex space-x-6 text-sm font-medium text-white/70">
            <Link to="/" className="hover:text-white transition-colors">Overview</Link>
          </div>
        </div>
      </nav>
      <main className="pt-24 pb-12 px-6 max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, colorClass, onClick }) {
  return (
    <button 
      onClick={onClick}
      className="text-left w-full p-8 rounded-3xl bg-white/5 border border-white/10 relative overflow-hidden group hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] transition-all cursor-pointer shadow-xl"
    >
      <div className={`absolute -right-4 -top-4 w-32 h-32 blur-3xl opacity-20 rounded-full transition-opacity group-hover:opacity-40 ${colorClass}`}></div>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white/60 font-medium text-base">{title}</h3>
        <Icon className="w-6 h-6 text-white/40 group-hover:text-white/80 transition-colors" />
      </div>
      <p className="text-5xl font-bold tracking-tight">{value}</p>
    </button>
  );
}

function Overview() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeModal, setActiveModal] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/runs`)
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-white/40" /></div>;
  }

  const completedRuns = runs.filter(r => r.status === 'completed' || r.status === 'partial');
  const totalReviews = completedRuns.reduce((acc, r) => acc + (r.reviews_fetched?.total || 0), 0);
  const totalThemes = completedRuns.reduce((acc, r) => acc + (r.themes_generated || 0), 0);
  const totalCost = completedRuns.reduce((acc, r) => acc + (r.llm_tokens?.estimated_cost_usd || 0), 0);

  // Prepare chart data
  const chartData = completedRuns.map(r => ({
    name: `W${r.iso_week}`,
    reviews: r.reviews_fetched?.total || 0,
    themes: r.themes_generated || 0,
    cost: r.llm_tokens?.estimated_cost_usd || 0,
  }));

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {activeModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-[#111] border border-white/10 rounded-3xl p-8 max-w-3xl w-full mx-4 shadow-2xl relative">
            <button 
              onClick={() => setActiveModal(null)}
              className="absolute top-6 right-6 text-white/40 hover:text-white"
            >
              Close ✕
            </button>
            <h2 className="text-2xl font-bold mb-6 capitalize">{activeModal} Breakdown</h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="name" stroke="#fff5" />
                  <YAxis stroke="#fff5" />
                  <Tooltip cursor={{fill: '#fff1'}} contentStyle={{backgroundColor: '#000', borderColor: '#333'}} />
                  <Bar dataKey={activeModal} fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      <header className="mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-2">Pulse Overview</h1>
        <p className="text-slate-400">Automated App Review Intelligence</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        <StatCard onClick={() => setActiveModal('reviews')} title="Total Reviews Analyzed" value={totalReviews.toLocaleString()} icon={MessageSquare} colorClass="bg-blue-500" />
        <StatCard onClick={() => setActiveModal('themes')} title="Themes Extracted" value={totalThemes} icon={Activity} colorClass="bg-purple-500" />
        <StatCard onClick={() => setActiveModal('cost')} title="Total LLM Cost" value={`$${totalCost.toFixed(4)}`} icon={DollarSign} colorClass="bg-emerald-500" />
      </div>

      <h2 className="text-2xl font-bold mb-6">Recent Reports</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {runs.map((run, i) => {
          // Construct the run identifier used for the report fetch
          const runIdPrefix = `${run.product}_${run.iso_year}_W${run.iso_week.toString().padStart(2, '0')}`;
          
          return (
            <Link key={i} to={`/report/${runIdPrefix}`} className="block group">
              <div className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/[0.07] transition-all relative overflow-hidden">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="text-xs font-mono text-white/40 mb-2">W{run.iso_week} • {run.iso_year}</div>
                    <h3 className="text-xl font-bold capitalize">{run.product}</h3>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-medium ${run.status === 'completed' || run.status === 'partial' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                    {run.status}
                  </div>
                </div>
                <div className="flex items-center text-sm text-white/60 mb-6">
                  <span className="w-2 h-2 rounded-full bg-white/20 mr-2"></span>
                  {run.clusters_found} Clusters Found
                </div>
                
                {run.preview && (
                  <div className="mb-6 space-y-3">
                    <div className="bg-white/5 rounded p-3">
                      <div className="text-xs font-semibold text-indigo-300 mb-1">Top Theme: {run.preview.theme_name}</div>
                      {run.preview.quote && (
                        <p className="text-sm text-white/80 italic line-clamp-2">"{run.preview.quote}"</p>
                      )}
                    </div>
                    {run.preview.action && (
                      <div className="text-xs text-white/60">
                        <span className="text-blue-300 font-medium">Action:</span> {run.preview.action}
                      </div>
                    )}
                  </div>
                )}
                
                <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
                  <div className="flex items-center text-sm text-indigo-400 font-medium group-hover:text-indigo-300 transition-colors">
                    View full report <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                  </div>
                  {run.doc_id && (
                    <a 
                      href={`https://docs.google.com/document/d/${run.doc_id}/edit`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-xs font-medium bg-white/5 hover:bg-blue-500/20 px-3 py-1.5 rounded-full transition-colors text-white/70 hover:text-blue-300 border border-transparent hover:border-blue-500/30"
                      onClick={(e) => e.stopPropagation()} // Prevent Link click
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1" />
                      Docs
                    </a>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function ReportDetail() {
  const { runId } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/reports/${runId}`)
      .then(res => {
        if (!res.ok) throw new Error('Report not found');
        return res.json();
      })
      .then(data => setReport(data))
      .catch(e => setError(e.message));
  }, [runId]);

  if (error) return <div className="text-red-400 text-center py-20">{error}</div>;
  if (!report) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-white/40" /></div>;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <Link to="/" className="inline-flex items-center text-sm text-white/50 hover:text-white mb-8 transition-colors">
        ← Back to Overview
      </Link>
      
      <header className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/10 pb-8">
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className="px-3 py-1.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-xs font-bold tracking-wide text-indigo-300">W{report.iso_week} {report.iso_year}</span>
            <span className="flex items-center px-3 py-1.5 rounded-full bg-white/10 text-slate-300 text-sm font-medium">
              <Calendar className="w-4 h-4 mr-2 text-slate-400" />
              {new Date(report.review_window_start).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })} – {new Date(report.review_window_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
            {report.doc_id && (
              <a 
                href={`https://docs.google.com/document/d/${report.doc_id}/edit`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center px-3 py-1.5 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 transition-colors text-sm font-medium border border-blue-500/20"
              >
                <ExternalLink className="w-4 h-4 mr-1.5" />
                Open Google Doc
              </a>
            )}
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight capitalize bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">{report.display_name} Pulse</h1>
        </div>
        
        <div className="flex space-x-8 text-sm">
          <div>
            <div className="text-white/40 mb-1">Reviews Analyzed</div>
            <div className="font-mono text-xl">{report.stats.total_reviews}</div>
          </div>
          <div>
            <div className="text-white/40 mb-1">Clusters</div>
            <div className="font-mono text-xl">{report.stats.clusters_found}</div>
          </div>
        </div>
      </header>

      <div className="mb-12">
        <h2 className="text-2xl font-bold mb-6 flex items-center">
          <span className="w-6 h-6 rounded bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm mr-3">1</span>
          Top Themes
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {report.themes.map((theme, i) => (
            <div key={i} className="p-8 rounded-3xl bg-white/5 border border-white/10 relative group shadow-lg">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-bold leading-tight pr-4">{theme.name}</h3>
                <span className="px-2 py-1 rounded bg-white/10 text-xs font-mono text-white/60 shrink-0">{theme.review_count} reviews</span>
              </div>
              <p className="text-white/70 text-sm leading-relaxed mb-6">{theme.description}</p>
              
              <div className="space-y-3">
                {theme.quotes.filter(q => q.validated).map((quote, j) => (
                  <div key={j} className="p-4 rounded-xl bg-black/40 border border-white/5 text-sm italic text-white/80">
                    "{quote.text}"
                    <div className="mt-2 text-xs text-white/40 not-italic font-mono">★ {quote.rating}/5 • {quote.store}</div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 pt-4 border-t border-white/10">
                <h4 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3">Suggested Actions</h4>
                <ul className="space-y-2">
                  {theme.actions.map((action, j) => (
                    <li key={j} className="text-sm text-indigo-200 flex items-start">
                      <ArrowRight className="w-4 h-4 mr-2 mt-0.5 shrink-0 text-indigo-500" />
                      <strong>{action.title}:</strong> {action.details}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
      
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/report/:runId" element={<ReportDetail />} />
        </Routes>
      </Layout>
    </Router>
  );
}
