import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom';
import { Activity, MessageSquare, DollarSign, Loader2, ArrowRight, Calendar, ExternalLink, Quote, Zap } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

// API Base URL
const API_BASE = 'http://localhost:8000/api';

// --- Components ---

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-800 text-slate-50 font-sans selection:bg-indigo-500/30">
      <nav className="fixed top-0 w-full border-b border-white/10 bg-slate-800/50 backdrop-blur-md z-50">
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

function StatCard({ title, value, icon: Icon, colorClass, borderColorClass, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`text-left w-full p-8 rounded-3xl bg-white/5 border border-white/10 border-t-4 ${borderColorClass} relative overflow-hidden group hover:bg-white/10 hover:border-white/30 hover:-translate-y-2 hover:shadow-2xl transition-all duration-300 cursor-pointer shadow-lg`}
    >
      <div className={`absolute -right-4 -top-4 w-32 h-32 blur-3xl opacity-20 rounded-full transition-all duration-500 group-hover:scale-150 group-hover:opacity-40 ${colorClass}`}></div>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white/60 font-medium text-base group-hover:text-white/90 transition-colors duration-300">{title}</h3>
        <Icon className="w-6 h-6 text-white/40 group-hover:text-white/90 group-hover:scale-110 transition-all duration-300" />
      </div>
      <p className="text-3xl lg:text-4xl font-bold tracking-tight group-hover:scale-105 origin-left transition-transform duration-300">{value}</p>
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
  const totalQuotes = completedRuns.reduce((acc, r) => acc + (r.quotes_validated || 0), 0);
  const totalCost = completedRuns.reduce((acc, r) => acc + (r.llm_tokens?.estimated_cost_usd || 0), 0);

  // Prepare chart data
  const chartData = completedRuns.map(r => ({
    name: `W${r.iso_week}`,
    reviews: r.reviews_fetched?.total || 0,
    themes: r.themes_generated || 0,
    quotes: r.quotes_validated || 0,
    cost: r.llm_tokens?.estimated_cost_usd || 0,
  }));

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {activeModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-slate-800 border border-white/10 rounded-3xl p-8 max-w-3xl w-full mx-4 shadow-2xl relative">
            <button 
              onClick={() => setActiveModal(null)}
              className="absolute top-6 right-6 text-white/40 hover:text-white"
            >
              Close ✕
            </button>
            <h2 className="text-2xl font-bold mb-6 capitalize">{activeModal} Breakdown</h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 10 }}>
                  <defs>
                    <linearGradient id="color0" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#818cf8" stopOpacity={1}/><stop offset="95%" stopColor="#4f46e5" stopOpacity={0.8}/></linearGradient>
                    <linearGradient id="color1" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#34d399" stopOpacity={1}/><stop offset="95%" stopColor="#059669" stopOpacity={0.8}/></linearGradient>
                    <linearGradient id="color2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#fbbf24" stopOpacity={1}/><stop offset="95%" stopColor="#d97706" stopOpacity={0.8}/></linearGradient>
                    <linearGradient id="color3" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={1}/><stop offset="95%" stopColor="#e11d48" stopOpacity={0.8}/></linearGradient>
                    <linearGradient id="color4" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#22d3ee" stopOpacity={1}/><stop offset="95%" stopColor="#0891b2" stopOpacity={0.8}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#fff1" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="#fff5" 
                    tick={{fill: '#fff8', fontSize: 12, fontWeight: 500}} 
                    axisLine={{stroke: '#fff2'}} 
                    tickLine={false} 
                    dy={10}
                  />
                  <YAxis 
                    stroke="#fff5" 
                    tick={{fill: '#fff8', fontSize: 12}} 
                    axisLine={false} 
                    tickLine={false} 
                    dx={-10}
                  />
                  <Tooltip 
                    cursor={{fill: '#fff1'}} 
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                      borderColor: 'rgba(255, 255, 255, 0.1)',
                      borderRadius: '12px',
                      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
                      padding: '12px 16px',
                      color: '#fff'
                    }} 
                    itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                  />
                  <Bar 
                    dataKey={activeModal} 
                    radius={[6, 6, 0, 0]}
                    barSize={48}
                    animationDuration={1500}
                    animationEasing="ease-out"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={`url(#color${index % 5})`} />
                    ))}
                  </Bar>
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

      <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-16">
        <StatCard onClick={() => setActiveModal('reviews')} title="Total Reviews Analyzed" value={totalReviews.toLocaleString()} icon={MessageSquare} colorClass="bg-blue-500" borderColorClass="border-t-blue-500" />
        <StatCard onClick={() => setActiveModal('themes')} title="Themes Extracted" value={totalThemes} icon={Activity} colorClass="bg-purple-500" borderColorClass="border-t-purple-500" />
        <StatCard onClick={() => setActiveModal('quotes')} title="Quotes Validated" value={totalQuotes} icon={Quote} colorClass="bg-rose-500" borderColorClass="border-t-rose-500" />
        <StatCard onClick={() => setActiveModal('themes')} title="Strategic Actions" value={totalThemes} icon={Zap} colorClass="bg-amber-500" borderColorClass="border-t-amber-500" />
        <StatCard onClick={() => setActiveModal('cost')} title="Total LLM Cost" value={`$${totalCost.toFixed(4)}`} icon={DollarSign} colorClass="bg-emerald-500" borderColorClass="border-t-emerald-500" />
      </div>

      <h2 className="text-2xl font-bold mb-6">Recent Reports</h2>
      <div className="flex flex-wrap justify-center gap-6">
        {runs.map((run, i) => {
          // Construct the run identifier used for the report fetch
          const runIdPrefix = `${run.product}_${run.iso_year}_W${run.iso_week.toString().padStart(2, '0')}`;
          
          const themeClasses = [
            'border-t-indigo-500 shadow-lg shadow-indigo-500/10 hover:shadow-2xl hover:shadow-indigo-500/30',
            'border-t-emerald-500 shadow-lg shadow-emerald-500/10 hover:shadow-2xl hover:shadow-emerald-500/30',
            'border-t-amber-500 shadow-lg shadow-amber-500/10 hover:shadow-2xl hover:shadow-amber-500/30',
            'border-t-rose-500 shadow-lg shadow-rose-500/10 hover:shadow-2xl hover:shadow-rose-500/30',
            'border-t-cyan-500 shadow-lg shadow-cyan-500/10 hover:shadow-2xl hover:shadow-cyan-500/30'
          ];
          const themeClass = themeClasses[i % themeClasses.length];
          
          return (
            <Link key={i} to={`/report/${runIdPrefix}`} className="block group w-full md:w-[calc(50%-0.75rem)] lg:w-[calc(33.333%-1rem)]">
              <div className={`h-full flex flex-col p-6 rounded-2xl bg-white/5 border border-white/10 border-t-4 ${themeClass} hover:border-white/30 hover:bg-white/10 hover:scale-[1.02] transition-all relative overflow-hidden cursor-pointer`}>
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
                  <div className="flex space-x-2">
                    <a 
                      href="https://mail.google.com/mail/u/0/#drafts"
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-xs font-medium bg-white/5 hover:bg-rose-500/20 px-3 py-1.5 rounded-full transition-colors text-white/70 hover:text-rose-300 border border-transparent hover:border-rose-500/30"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MessageSquare className="w-3.5 h-3.5 mr-1" />
                      Drafts
                    </a>
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
            <a 
              href="https://mail.google.com/mail/u/0/#drafts"
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center px-3 py-1.5 rounded-full bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 transition-colors text-sm font-medium border border-rose-500/20"
            >
              <MessageSquare className="w-4 h-4 mr-1.5" />
              View Email Drafts
            </a>
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
            <div key={i} className="p-8 rounded-3xl bg-white/5 border border-white/10 relative group shadow-lg hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] transition-all cursor-pointer">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-bold leading-tight pr-4">{theme.name}</h3>
                <span className="px-2 py-1 rounded bg-white/10 text-xs font-mono text-white/60 shrink-0">{theme.review_count} reviews</span>
              </div>
              <p className="text-white/70 text-sm leading-relaxed mb-6">{theme.description}</p>
              
              <div className="space-y-3">
                {theme.quotes.filter(q => q.validated).map((quote, j) => {
                  const borderColors = ['border-l-indigo-500', 'border-l-emerald-500', 'border-l-amber-500', 'border-l-rose-500'];
                  const borderColorClass = borderColors[j % borderColors.length];
                  return (
                    <div key={j} className={`p-4 rounded-xl bg-black/40 border-y border-r border-white/5 border-l-4 ${borderColorClass} text-sm italic text-white/80 hover:bg-white/5 hover:border-white/20 hover:scale-[1.02] transition-all cursor-pointer shadow-md`}>
                      "{quote.text}"
                      <div className="mt-2 text-xs text-white/40 not-italic font-mono flex items-center justify-between">
                        <span>★ {quote.rating}/5 • {quote.store}</span>
                        <span className="text-white/20 hover:text-white/40 transition-colors">View Source ↗</span>
                      </div>
                    </div>
                  );
                })}
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
