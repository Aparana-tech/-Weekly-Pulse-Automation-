import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Link, useParams } from 'react-router-dom';
import { Activity, MessageSquare, DollarSign, Loader2, ArrowRight, Calendar, ExternalLink, Quote, Zap, LayoutDashboard, Settings, User } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

// API Base URL
const API_BASE = import.meta.env.BASE_URL + 'api';

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 p-6 hidden lg:flex flex-col border-r border-slate-200/60 bg-white/40 backdrop-blur-xl z-50">
      <div className="mb-8 p-5 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-xl shadow-indigo-200/50">
        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-sm mb-3">P</div>
        <h1 className="font-bold text-lg leading-tight">Pulse Ops AI</h1>
        <p className="text-white/80 text-xs mt-1">Product Operations Dashboard</p>
      </div>

      <div className="mb-3 text-[10px] font-bold text-slate-400 tracking-widest">SURFACES</div>
      <nav className="space-y-2">
        <button className="w-full text-left flex flex-col px-4 py-3 rounded-xl hover:bg-slate-50 text-slate-600 transition-all cursor-not-allowed">
          <span className="font-semibold text-sm">Customer</span>
          <span className="text-xs text-slate-400">AI assistant</span>
        </button>
        <Link to="/" className="flex flex-col px-4 py-3 rounded-xl bg-white shadow-sm border border-slate-100 text-indigo-900 transition-all relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500"></div>
          <span className="font-bold text-sm">Product</span>
          <span className="text-xs text-slate-500">Weekly Pulse</span>
        </Link>
        <button className="w-full text-left flex flex-col px-4 py-3 rounded-xl hover:bg-slate-50 text-slate-600 transition-all cursor-not-allowed">
          <span className="font-semibold text-sm">Advisor</span>
          <span className="text-xs text-slate-400">Approvals</span>
        </button>
      </nav>

      <div className="mt-auto pt-6 border-t border-slate-200/60">
        <div className="text-[10px] font-bold text-slate-400 tracking-widest mb-2">TIMEZONE</div>
        <div className="text-sm font-bold text-slate-700">Asia/Kolkata (IST)</div>
        <div className="text-xs text-slate-400 leading-relaxed mt-1">Booking slots and pulse cadence are shown in IST.</div>
      </div>
    </aside>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <Sidebar />
      {/* Mobile nav fallback */}
      <nav className="lg:hidden p-4 bg-white border-b border-slate-100 flex items-center justify-between">
         <div className="font-bold text-indigo-900">Pulse Ops AI</div>
         <div className="text-xs font-bold text-slate-400">Weekly Pulse</div>
      </nav>
      <main className="lg:ml-64 p-6 lg:p-10 max-w-5xl mx-auto">
        {children}
      </main>
    </div>
  );
}

function StatCard({ title, value, subtitle, icon: Icon }) {
  return (
    <div className="p-6 rounded-3xl bg-white/70 backdrop-blur-sm border border-slate-100 shadow-sm flex flex-col items-center text-center hover:bg-white transition-colors cursor-default">
      <Icon className="w-5 h-5 text-indigo-400 mb-4" />
      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{title}</div>
      <div className="text-3xl font-bold text-slate-800 mb-1">{value}</div>
      <div className="text-xs text-slate-500 font-medium">{subtitle}</div>
    </div>
  );
}

function Overview() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/runs.json`)
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-indigo-400" /></div>;
  }

  const completedRuns = runs.filter(r => r.status === 'completed' || r.status === 'partial');
  const totalReviews = completedRuns.reduce((acc, r) => acc + (r.reviews_fetched?.total || 0), 0);
  const totalThemes = completedRuns.reduce((acc, r) => acc + (r.themes_generated || 0), 0);
  const totalActions = completedRuns.reduce((acc, r) => acc + ((r.themes_generated || 0) * 3), 0);
  const totalQuotes = completedRuns.reduce((acc, r) => acc + (r.quotes_validated || 0), 0);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-8 flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-bold text-slate-400 tracking-widest uppercase mb-1">Product Surface</div>
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Weekly Pulse</h1>
          <p className="text-sm text-slate-500">Monitor themes, quotes, actions, and signals from customer feedback.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-100">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span> Services healthy
          </div>
          <div className="flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-100">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span> Data connected
          </div>
        </div>
      </header>

      {/* Top Banner */}
      <div className="mb-6 p-8 rounded-[2rem] bg-white/80 backdrop-blur-md shadow-sm border border-slate-100 flex flex-col md:flex-row justify-between items-center gap-6">
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className="px-2.5 py-1 bg-amber-50 border border-amber-100 text-amber-600 text-[10px] font-bold rounded uppercase tracking-wider flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5"></span> Latest pulse ready
            </span>
            <span className="text-[10px] text-slate-500 font-bold bg-slate-50 border border-slate-100 px-2.5 py-1 rounded uppercase tracking-wider">Every Monday • 10:00 AM IST</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Weekly Pulse</h2>
          <p className="text-sm text-slate-500">Insights from customer questions, reviews, and signals.</p>
        </div>
        <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 text-center min-w-[220px]">
          <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">Next scheduled send</div>
          <div className="font-bold text-slate-700 text-sm mb-1">Monday, 10:00 AM IST</div>
          <div className="text-xs text-slate-400">Subscribers receive the same pulse.</div>
        </div>
      </div>

      {/* Warning Notice (Simulated from screenshot) */}
      <div className="mb-8 p-4 rounded-xl bg-amber-50/50 border border-amber-100 text-amber-800 text-sm">
        <strong className="font-semibold">Analysis is in normal mode.</strong> The pulse uses the available review set with primary ML analysis.
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard title="Reviews Analyzed" value={totalReviews.toLocaleString()} subtitle="Cleaned review inputs" icon={MessageSquare} />
        <StatCard title="Average Rating" value="2.39" subtitle="Across reviewed inputs" icon={Activity} />
        <StatCard title="Top Issue Theme" value="Support & changes" subtitle="Highest mention cluster" icon={Quote} />
        <StatCard title="Strategic Intent" value={totalActions} subtitle="Inferred from current themes" icon={Zap} />
      </div>

      <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest mb-4">Recent Reports</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {runs.map((run, i) => {
          const runIdPrefix = `${run.product}_${run.iso_year}_W${run.iso_week.toString().padStart(2, '0')}`;
          
          return (
            <Link key={i} to={`/report/${runIdPrefix}`} className="block group">
              <div className="h-full flex flex-col p-6 rounded-[2rem] bg-white border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-100 transition-all cursor-pointer">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="text-[10px] font-bold text-indigo-500 tracking-widest uppercase mb-1">W{run.iso_week} • {run.iso_year}</div>
                    <h3 className="text-lg font-bold text-slate-800 capitalize">{run.product}</h3>
                  </div>
                  <div className={`px-2 py-1 rounded text-[9px] font-bold uppercase tracking-wider ${run.status === 'completed' || run.status === 'partial' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-amber-50 text-amber-600 border border-amber-100'}`}>
                    {run.status}
                  </div>
                </div>
                
                <div className="flex items-center text-xs font-semibold text-slate-400 mb-4">
                  {run.clusters_found} Clusters Found
                </div>
                
                {run.preview && (
                  <div className="mb-6 space-y-2 flex-grow">
                    <div className="bg-slate-50/50 rounded-xl p-4 border border-slate-100">
                      <div className="text-xs font-bold text-slate-700 mb-1.5">{run.preview.theme_name}</div>
                      {run.preview.quote && (
                        <p className="text-xs text-slate-500 italic line-clamp-2 leading-relaxed">"{run.preview.quote}"</p>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="flex items-center justify-between mt-auto pt-4 border-t border-slate-50">
                  <div className="text-xs font-bold text-indigo-600 group-hover:text-indigo-700 transition-colors flex items-center">
                    View report <ArrowRight className="w-3 h-3 ml-1" />
                  </div>
                  <div className="flex space-x-3">
                    <a 
                      href="https://mail.google.com/mail/u/0/#drafts"
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-800 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Drafts
                    </a>
                    {run.doc_id && (
                      <a 
                        href={`https://docs.google.com/document/d/${run.doc_id}/edit`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-800 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
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
    fetch(`${API_BASE}/reports/${runId}.json`)
      .then(res => {
        if (!res.ok) throw new Error('Report not found');
        return res.json();
      })
      .then(data => setReport(data))
      .catch(e => setError(e.message));
  }, [runId]);

  if (error) return <div className="text-red-500 text-center py-20 bg-white rounded-3xl shadow-sm border border-red-100 mx-auto max-w-lg mt-10 text-sm font-medium">{error}</div>;
  if (!report) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-indigo-400" /></div>;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <Link to="/" className="inline-flex items-center text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-indigo-600 mb-6 transition-colors">
        <ArrowRight className="w-3 h-3 mr-2 rotate-180" /> Back to Overview
      </Link>
      
      <header className="mb-8 p-8 bg-white rounded-[2rem] shadow-sm border border-slate-100 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-[10px] font-bold rounded uppercase tracking-wider">W{report.iso_week} {report.iso_year}</span>
            <span className="text-xs text-slate-500 font-semibold">
              {new Date(report.review_window_start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – {new Date(report.review_window_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 capitalize">{report.display_name} Pulse</h1>
        </div>
        
        <div className="flex space-x-3">
          <a 
            href="https://mail.google.com/mail/u/0/#drafts"
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center px-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 transition-colors text-xs font-bold tracking-wide border border-slate-200"
          >
            <MessageSquare className="w-3.5 h-3.5 mr-2" />
            Email Drafts
          </a>
          {report.doc_id && (
            <a 
              href={`https://docs.google.com/document/d/${report.doc_id}/edit`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center px-4 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-colors text-xs font-bold tracking-wide border border-indigo-200"
            >
              <ExternalLink className="w-3.5 h-3.5 mr-2" />
              Google Doc
            </a>
          )}
        </div>
      </header>

      {/* Summary Card */}
      <div className="mb-10 p-8 rounded-[2rem] bg-white shadow-sm border border-slate-100">
        <h3 className="text-base font-bold text-slate-800 mb-1">This week in summary</h3>
        <p className="text-xs text-slate-400 font-medium mb-6">Executive narrative for PM and operations review.</p>
        
        <p className="text-sm text-slate-600 leading-relaxed mb-8">
          This week's pulse highlights feedback across several critical areas. We analyzed {report.stats.total_reviews} reviews and extracted {report.stats.clusters_found} core themes. 
          {report.themes[0] ? ` The leading concern was related to '${report.themes[0].name}'.` : ''} 
          Below you will find the detailed breakdown of each theme, supporting quotes directly from users, and strategic action recommendations to improve the product experience.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-100">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Primary Signal</div>
            <div className="text-sm font-bold text-slate-800">{report.themes[0]?.name || "N/A"}</div>
          </div>
          <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-100">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Evidence</div>
            <div className="text-sm font-bold text-slate-800">{report.stats.total_reviews} reviews analyzed</div>
          </div>
          <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-100">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">PM Focus</div>
            <div className="text-sm font-bold text-slate-800 line-clamp-1">{report.themes[0]?.actions[0]?.title || "N/A"}</div>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between mb-2">
           <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest">Pulse Themes</h2>
        </div>
        {report.themes.map((theme, i) => (
          <div key={i} className="p-8 rounded-[2rem] bg-white border border-slate-100 shadow-sm flex flex-col md:flex-row gap-8">
            <div className="flex-1">
              <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-2">Theme {i + 1}</div>
              <h3 className="text-xl font-bold text-slate-800 mb-3">{theme.name}</h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-6">{theme.description}</p>
              
              <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center">
                  Key Quotes
                </h4>
                <div className="space-y-4">
                  {theme.quotes.filter(q => q.validated).slice(0, 3).map((quote, j) => (
                    <div key={j} className="text-sm italic text-slate-600 border-l-2 border-indigo-200 pl-4 py-0.5 leading-relaxed">
                      "{quote.text}"
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="w-full md:w-80 shrink-0">
              <div className="bg-indigo-50/50 rounded-2xl p-6 border border-indigo-100 h-full">
                <h4 className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest mb-5 flex items-center">
                  Action Items
                </h4>
                <ul className="space-y-5">
                  {theme.actions.map((action, j) => (
                    <li key={j}>
                      <div className="text-sm font-bold text-indigo-900 mb-1.5">{action.title}</div>
                      <div className="text-xs text-indigo-700/70 leading-relaxed">{action.details}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        ))}
      </div>
      
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/report/:runId" element={<ReportDetail />} />
        </Routes>
      </Layout>
    </HashRouter>
  );
}
