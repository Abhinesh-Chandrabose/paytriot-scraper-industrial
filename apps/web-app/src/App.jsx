import React, { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/utils/api";
import ReactMarkdown from "react-markdown";
import {
  MagnifyingGlass, Robot, Export, Trash, PaperPlaneTilt, LinkedinLogo,
  Globe, Envelope, Phone, TwitterLogo, TelegramLogo, ArrowRight,
  Lightning, CircleNotch, CheckCircle, XCircle, Buildings, Users,
  ClockCounterClockwise, CaretDown, ArrowClockwise, Warning, ChartBar
} from "@phosphor-icons/react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const SECTORS = [
  "Any sector", "Technology", "E-commerce / Retail", "Healthcare",
  "Finance / Banking", "Education", "Real Estate",
  "Marketing / Advertising", "Legal", "Hospitality / Travel",
  "Manufacturing", "Media / Publishing", "Non-profit",
  "Construction", "Logistics / Transport"
];

const COUNTRIES = [
  "Any country", "United States", "United Kingdom", "Canada",
  "Australia", "Germany", "France", "India", "South Africa", "Nigeria", "UAE"
];

const SIZES = ["Any size", "Startup / Small", "Mid-market", "Enterprise / Large"];

const QUICK_PROMPTS = [
  "Find all contact info for Apple Inc",
  "What are the top SaaS companies in 2026?",
  "Summarise all the scraped results so far",
  "How can I improve my lead generation strategy?",
  "Compare Google vs Microsoft employee structure"
];

// --- Header ---
function Header() {
  return (
    <header className="header-glass sticky top-0 z-50" data-testid="app-header">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Lightning size={20} weight="fill" className="text-amber-500" />
            <span className="font-heading text-lg font-black tracking-tight text-white" data-testid="app-logo">
              GOscraper
            </span>
          </div>
          <span className="badge badge-amber" data-testid="version-badge">v2.0 — AI + Apify</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge badge-green">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5 inline-block"></span>
            Live
          </span>
        </div>
      </div>
    </header>
  );
}

// --- TabBar ---
function TabBar({ activeTab, setActiveTab }) {
  return (
    <div className="flex border-b border-zinc-800" data-testid="tab-bar">
      <button
        className={`tab-btn ${activeTab === "scraper" ? "active" : ""}`}
        onClick={() => setActiveTab("scraper")}
        data-testid="tab-scraper"
      >
        <MagnifyingGlass size={14} className="inline mr-1.5 -mt-0.5" />
        Scraper
      </button>
      <button
        className={`tab-btn ${activeTab === "linkedin" ? "active" : ""}`}
        onClick={() => setActiveTab("linkedin")}
        data-testid="tab-linkedin"
      >
        <LinkedinLogo size={14} className="inline mr-1.5 -mt-0.5" />
        LinkedIn
      </button>
      <button
        className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
        onClick={() => setActiveTab("chat")}
        data-testid="tab-chat"
      >
        <Robot size={14} className="inline mr-1.5 -mt-0.5" />
        AI Assistant
      </button>
      <button
        className={`tab-btn ${activeTab === "leads" ? "active" : ""}`}
        onClick={() => setActiveTab("leads")}
        data-testid="tab-leads"
      >
        <Lightning size={14} className="inline mr-1.5 -mt-0.5" />
        Leads
      </button>
    </div>
  );
}

// --- Status Indicator ---
function StatusIndicator({ status, message }) {
  if (!message) return null;
  const icon = status === "loading" ? <CircleNotch size={14} className="animate-spin text-amber-500" /> :
    status === "success" ? <CheckCircle size={14} weight="fill" className="text-green-500" /> :
    status === "error" ? <XCircle size={14} weight="fill" className="text-red-500" /> : null;

  return (
    <div className={`flex items-center gap-2 text-sm font-mono ${
      status === "loading" ? "text-amber-500" : status === "success" ? "text-green-500" : "text-red-500"
    }`} data-testid="status-indicator">
      {icon}
      <span>{message}</span>
    </div>
  );
}

// --- GoogleSearchTab ---
function GoogleSearchTab({ businesses, setBusinesses }) {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("");
  const [sector, setSector] = useState("Any sector");
  const [country, setCountry] = useState("Any country");
  const [size, setSize] = useState("Any size");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: null, message: "" });
  const [searchResults, setSearchResults] = useState([]);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setStatus({ type: "loading", message: "Starting Google search via Apify..." });
    setSearchResults([]);

    let searchQuery = query;
    if (domain) searchQuery += ` site:${domain}`;
    if (sector !== "Any sector") searchQuery += ` ${sector}`;
    if (country !== "Any country") searchQuery += ` ${country}`;
    if (size !== "Any size") searchQuery += ` ${size}`;
    searchQuery += " contact information email phone website linkedin";

    try {
      const data = await api.post("/search/google", {
        queries: [searchQuery],
        country_code: "us",
        language_code: "en",
        max_pages: 1,
        results_per_page: 10
      });

      if (data.success) {
        const results = data.results || [];
        setSearchResults(results);
        const parsed = [];
        results.forEach(r => {
          const organic = r.organicResults || r.nonPromotedSearchResults || [];
          organic.forEach(o => {
            const isSocial = (url) => url?.includes("linkedin.com") || url?.includes("twitter.com") || url?.includes("facebook.com") || url?.includes("instagram.com");
            parsed.push({
              id: crypto.randomUUID(),
              name: o.title || "Unknown",
              website: isSocial(o.url) ? "" : (o.url || o.displayedUrl || ""),
              emails: [],
              phones: [],
              linkedin: o.url?.includes("linkedin.com") ? o.url : "",
              twitter: o.url?.includes("twitter.com") ? o.url : "",
              telegram: "",
              sector: sector !== "Any sector" ? sector : "",
              source: "google_search",
              created_at: new Date().toISOString(),
              description: o.description || ""
            });
          });
        });
        setBusinesses(prev => [...parsed, ...prev]);
        setStatus({ type: "success", message: `Found ${parsed.length} results` });
        if (parsed.length > 0) {
          try { await api.post("/businesses/bulk", parsed); } catch (e) { /* silent */ }
        }
      }
    } catch (err) {
      setStatus({ type: "error", message: err.response?.data?.detail || "Search failed" });
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => window.open(`${API_URL}/export/csv`, "_blank");

  const clearAll = async () => {
    setBusinesses([]);
    setSearchResults([]);
    setStatus({ type: null, message: "" });
    try { await api.delete("/businesses"); } catch (e) { /* silent */ }
  };

  return (
    <div className="animate-fade-in" data-testid="google-search-tab">
      <div className="border border-zinc-800 p-6" data-testid="search-form">
        <div className="flex items-center gap-2 mb-4">
          <Globe size={16} className="text-amber-500" />
          <span className="font-mono text-xs uppercase tracking-widest text-zinc-400">Google Search Scraper</span>
          <span className="badge badge-amber ml-auto">Apify Powered</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <input className="input-terminal" placeholder="Business name (e.g. Stripe, Nike)" value={query}
            onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} data-testid="search-input-name" />
          <input className="input-terminal" placeholder="Domain (e.g. stripe.com) — optional" value={domain}
            onChange={e => setDomain(e.target.value)} data-testid="search-input-domain" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <select className="select-terminal" value={sector} onChange={e => setSector(e.target.value)} data-testid="search-select-sector">
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="select-terminal" value={country} onChange={e => setCountry(e.target.value)} data-testid="search-select-country">
            {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select className="select-terminal" value={size} onChange={e => setSize(e.target.value)} data-testid="search-select-size">
            {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary" onClick={doSearch} disabled={loading || !query.trim()} data-testid="search-submit-button">
            {loading ? <CircleNotch size={14} className="animate-spin" /> : <MagnifyingGlass size={14} />}
            {loading ? "Searching..." : "Search & Scrape"}
          </button>
          <button className="btn-secondary" onClick={exportCSV} data-testid="export-csv-button">
            <Export size={14} /> Export CSV
          </button>
          <button className="btn-ghost" onClick={clearAll} data-testid="clear-all-button">
            <Trash size={14} /> Clear
          </button>
          <div className="ml-auto"><StatusIndicator status={status.type} message={status.message} /></div>
        </div>
        {loading && <div className="progress-bar mt-4" data-testid="search-progress-bar"></div>}
      </div>

      {businesses.length > 0 && (
        <div className="mt-0" data-testid="search-results-section">
          <div className="border border-zinc-800 border-t-0 px-6 py-3 flex items-center justify-between bg-zinc-900/30">
            <span className="font-mono text-xs uppercase tracking-widest text-zinc-400">Results</span>
            <span className="badge badge-zinc" data-testid="results-count">{businesses.length} records</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
            {businesses.map((biz, i) => (
              <div key={biz.id || i} className="biz-card animate-fade-in" style={{ animationDelay: `${i * 50}ms` }} data-testid={`biz-card-${i}`}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-heading font-bold text-white text-base">{biz.name}</h3>
                    {biz.sector && <span className="badge badge-zinc mt-1">{biz.sector}</span>}
                  </div>
                  <span className="badge badge-amber">{biz.source}</span>
                </div>
                {biz.website && (
                  <div className="field-row">
                    <span className="field-label">Website</span>
                    <span className="field-value">
                      <a href={biz.website.startsWith("http") ? biz.website : `https://${biz.website}`} target="_blank" rel="noreferrer">
                        {biz.website.length > 50 ? biz.website.slice(0, 50) + "..." : biz.website}
                      </a>
                    </span>
                  </div>
                )}
                {biz.emails?.length > 0 && (
                  <div className="field-row">
                    <span className="field-label"><Envelope size={12} className="inline mr-1" />Emails</span>
                    <span className="field-value">{biz.emails.join(", ")}</span>
                  </div>
                )}
                {biz.phones?.length > 0 && (
                  <div className="field-row">
                    <span className="field-label"><Phone size={12} className="inline mr-1" />Phones</span>
                    <span className="field-value">{biz.phones.join(", ")}</span>
                  </div>
                )}
                {biz.linkedin && (
                  <div className="field-row">
                    <span className="field-label"><LinkedinLogo size={12} className="inline mr-1" />LinkedIn</span>
                    <span className="field-value">
                      <a href={biz.linkedin} target="_blank" rel="noreferrer">
                        {biz.linkedin.length > 50 ? biz.linkedin.slice(0, 50) + "..." : biz.linkedin}
                      </a>
                    </span>
                  </div>
                )}
                {biz.description && <p className="text-xs text-zinc-500 mt-2 leading-relaxed line-clamp-2">{biz.description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {businesses.length === 0 && !loading && (
        <div className="border border-zinc-800 border-t-0 p-12 flex flex-col items-center justify-center text-center" data-testid="empty-state">
          <MagnifyingGlass size={48} className="text-zinc-700 mb-4" />
          <p className="text-zinc-500 text-sm font-mono">Enter a business name and hit Search & Scrape</p>
          <p className="text-zinc-600 text-xs mt-1">Results from Apify Google Search will appear here</p>
        </div>
      )}
    </div>
  );
}

// --- LinkedInTab ---
function LinkedInTab() {
  const [companyUrl, setCompanyUrl] = useState("");
  const [maxResults, setMaxResults] = useState(50);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: null, message: "" });
  const [employees, setEmployees] = useState([]);

  const doScrape = async () => {
    if (!companyUrl.trim()) return;
    setLoading(true);
    setStatus({ type: "loading", message: "Starting LinkedIn scraper via Apify..." });
    setEmployees([]);
    try {
      const data = await api.post("/search/linkedin", { company_urls: [companyUrl.trim()], max_results: maxResults });
      if (data.success) {
        setEmployees(data.employees || []);
        setStatus({ type: "success", message: `Found ${data.count || 0} employees` });
      }
    } catch (err) {
      setStatus({ type: "error", message: err || "Scrape failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" data-testid="linkedin-tab">
      <div className="border border-zinc-800 p-6">
        <div className="flex items-center gap-2 mb-4">
          <LinkedinLogo size={16} className="text-amber-500" />
          <span className="font-mono text-xs uppercase tracking-widest text-zinc-400">LinkedIn Employee Scraper</span>
          <span className="badge badge-amber ml-auto">Apify Powered</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div className="md:col-span-2">
            <input className="input-terminal" placeholder="LinkedIn company URL (e.g. https://linkedin.com/company/google)"
              value={companyUrl} onChange={e => setCompanyUrl(e.target.value)} onKeyDown={e => e.key === "Enter" && doScrape()} data-testid="linkedin-input-url" />
          </div>
          <input className="input-terminal" type="number" placeholder="Max results" value={maxResults}
            onChange={e => setMaxResults(parseInt(e.target.value) || 50)} data-testid="linkedin-input-max" />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary" onClick={doScrape} disabled={loading || !companyUrl.trim()} data-testid="linkedin-submit-button">
            {loading ? <CircleNotch size={14} className="animate-spin" /> : <Users size={14} />}
            {loading ? "Scraping..." : "Scrape Employees"}
          </button>
          <div className="ml-auto"><StatusIndicator status={status.type} message={status.message} /></div>
        </div>
        {loading && <div className="progress-bar mt-4"></div>}
      </div>

      {employees.length > 0 && (
        <div className="mt-0" data-testid="linkedin-results">
          <div className="border border-zinc-800 border-t-0 px-6 py-3 flex items-center justify-between bg-zinc-900/30">
            <span className="font-mono text-xs uppercase tracking-widest text-zinc-400">Employees</span>
            <span className="badge badge-zinc">{employees.length} found</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0">
            {employees.map((emp, i) => (
              <div key={i} className="employee-card animate-fade-in" style={{ animationDelay: `${i * 30}ms` }} data-testid={`employee-card-${i}`}>
                <div className="flex items-start gap-3">
                  {emp.profilePicture || emp.avatar ? (
                    <img src={emp.profilePicture || emp.avatar} alt="" className="w-10 h-10 bg-zinc-800 flex-shrink-0 object-cover" />
                  ) : (
                    <div className="w-10 h-10 bg-zinc-800 flex-shrink-0 flex items-center justify-center">
                      <Users size={16} className="text-zinc-600" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <h4 className="font-heading font-bold text-white text-sm truncate">
                      {emp.name || emp.firstName ? `${emp.firstName || ""} ${emp.lastName || ""}`.trim() : "Unknown"}
                    </h4>
                    <p className="text-xs text-zinc-400 truncate mt-0.5">{emp.title || emp.headline || emp.currentPosition?.title || "—"}</p>
                    {emp.location && <p className="text-xs text-zinc-500 mt-0.5">{typeof emp.location === "string" ? emp.location : emp.location.default || ""}</p>}
                  </div>
                </div>
                {(emp.profileUrl || emp.url || emp.linkedinUrl) && (
                  <a href={emp.profileUrl || emp.url || emp.linkedinUrl} target="_blank" rel="noreferrer"
                    className="block mt-2 text-xs text-amber-500 hover:text-amber-400 font-mono truncate">
                    View Profile →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {employees.length === 0 && !loading && (
        <div className="border border-zinc-800 border-t-0 p-12 flex flex-col items-center justify-center text-center" data-testid="linkedin-empty-state">
          <LinkedinLogo size={48} className="text-zinc-700 mb-4" />
          <p className="text-zinc-500 text-sm font-mono">Paste a LinkedIn company URL to scrape employees</p>
          <p className="text-zinc-600 text-xs mt-1">Powered by Apify LinkedIn Employee Scraper</p>
        </div>
      )}
    </div>
  );
}

// --- ChatTab ---
function ChatTab() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${crypto.randomUUID()}`);
  const chatEndRef = useRef(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: msg }]);
    setMessages(prev => [...prev, { role: "ai", text: "", thinking: true }]);
    setLoading(true);
    try {
      const data = await api.post("/chat", { session_id: sessionId, message: msg });
      if (data.success) {
        setMessages(prev => { 
          const u = [...prev]; 
          u[u.length - 1] = { role: "ai", text: data.response }; 
          return u; 
        });
      } else {
        setMessages(prev => { 
          const u = [...prev]; 
          u[u.length - 1] = { role: "ai", text: `Error: ${data.error || "Unknown error"}`, error: true }; 
          return u; 
        });
      }
    } catch (err) {
      setMessages(prev => { 
        const u = [...prev]; 
        u[u.length - 1] = { role: "ai", text: `Error: ${err.message || "Failed to get response"}`, error: true }; 
        return u; 
      });
    } finally {
      setLoading(false);
    }

  };

  return (
    <div className="animate-fade-in flex flex-col" style={{ height: "calc(100vh - 160px)" }} data-testid="chat-tab">
      <div className="flex-1 overflow-y-auto border border-zinc-800 p-6 space-y-4" data-testid="chat-messages">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Robot size={48} className="text-zinc-700 mb-4" />
            <h3 className="font-heading font-bold text-zinc-400 text-lg mb-2">GOscraper AI Assistant</h3>
            <p className="text-zinc-500 text-sm mb-6 max-w-md">Ask me about businesses, industries, scraping strategies, or anything related to business intelligence.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
              {QUICK_PROMPTS.map((p, i) => (
                <button key={i} className="quick-chip" onClick={() => sendMessage(p)} data-testid={`quick-prompt-${i}`}>
                  <ArrowRight size={12} className="inline mr-1.5 text-amber-500" />{p}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role} animate-slide-in ${msg.error ? "border-red-900/50" : ""}`}
            style={{ animationDelay: `${i * 30}ms` }} data-testid={`chat-msg-${i}`}>
            {msg.thinking ? (
              <div className="flex items-center gap-2">
                <span className="typing-dot w-1.5 h-1.5 bg-amber-500 rounded-full inline-block"></span>
                <span className="typing-dot w-1.5 h-1.5 bg-amber-500 rounded-full inline-block"></span>
                <span className="typing-dot w-1.5 h-1.5 bg-amber-500 rounded-full inline-block"></span>
                <span className="text-xs text-zinc-500 font-mono ml-2">Thinking...</span>
              </div>
            ) : (
              <div className="text-sm leading-relaxed">
                {msg.role === "ai" && <span className="text-xs text-amber-500 font-mono font-bold block mb-1.5">AI</span>}
                {msg.role === "user" && <span className="text-xs text-zinc-500 font-mono font-bold block mb-1.5">YOU</span>}
                {msg.role === "ai" ? (
                  <div className="markdown-content">
                    <ReactMarkdown components={{
                      h1: ({children}) => <h1 className="font-heading text-xl font-bold text-white mt-3 mb-2">{children}</h1>,
                      h2: ({children}) => <h2 className="font-heading text-lg font-bold text-white mt-3 mb-1.5">{children}</h2>,
                      h3: ({children}) => <h3 className="font-heading text-base font-semibold text-white mt-2 mb-1">{children}</h3>,
                      p: ({children}) => <p className="text-zinc-300 mb-2 leading-relaxed">{children}</p>,
                      strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
                      em: ({children}) => <em className="text-zinc-400 italic">{children}</em>,
                      ul: ({children}) => <ul className="list-disc list-inside space-y-1 mb-2 text-zinc-300">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal list-inside space-y-1 mb-2 text-zinc-300">{children}</ol>,
                      li: ({children}) => <li className="text-zinc-300">{children}</li>,
                      code: ({inline, children}) => inline
                        ? <code className="bg-zinc-800 text-amber-400 px-1.5 py-0.5 font-mono text-xs">{children}</code>
                        : <pre className="bg-zinc-900 border border-zinc-800 p-3 my-2 overflow-x-auto"><code className="font-mono text-xs text-zinc-300">{children}</code></pre>,
                      a: ({href, children}) => <a href={href} target="_blank" rel="noreferrer" className="text-amber-500 hover:text-amber-400 underline">{children}</a>,
                      blockquote: ({children}) => <blockquote className="border-l-2 border-amber-500 pl-3 my-2 text-zinc-400 italic">{children}</blockquote>,
                      hr: () => <hr className="border-zinc-800 my-3" />,
                    }}>{msg.text}</ReactMarkdown>
                  </div>
                ) : (
                  <span className="whitespace-pre-wrap">{msg.text}</span>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <div className="border border-zinc-800 border-t-0 p-4 flex items-center gap-3" data-testid="chat-input-area">
        <input className="input-terminal flex-1" placeholder="Ask GOscraper AI anything..." value={input}
          onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendMessage()} disabled={loading} data-testid="chat-input" />
        <button className="btn-primary" onClick={() => sendMessage()} disabled={loading || !input.trim()} data-testid="chat-send-button">
          {loading ? <CircleNotch size={14} className="animate-spin" /> : <PaperPlaneTilt size={14} />}
          Send
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Module 5 — LeadsTab
// ═══════════════════════════════════════════════════════════════════════════

// Score badge: red >= 8, amber >= 5, green < 5
function ScoreBadge({ score }) {
  const cls =
    score >= 8 ? "inline-flex items-center px-2 py-0.5 font-mono text-xs font-bold bg-red-900/60 text-red-400 border border-red-800" :
    score >= 5 ? "inline-flex items-center px-2 py-0.5 font-mono text-xs font-bold bg-amber-900/60 text-amber-400 border border-amber-800" :
                 "inline-flex items-center px-2 py-0.5 font-mono text-xs font-bold bg-green-900/60 text-green-400 border border-green-800";
  return <span className={cls}>{score}</span>;
}

// Source tag
function SourceTag({ source }) {
  const isReddit = source === "reddit";
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-mono text-xs border ${
      isReddit ? "bg-orange-900/40 text-orange-400 border-orange-800" : "bg-blue-900/40 text-blue-400 border-blue-800"
    }`}>
      {isReddit ? <Globe size={10} /> : <TelegramLogo size={10} />}
      {source}
    </span>
  );
}

// Urgency pill
function UrgencyPill({ urgency }) {
  const styles = {
    critical: "bg-red-900/60 text-red-300 border-red-800",
    high:     "bg-amber-900/60 text-amber-300 border-amber-800",
    medium:   "bg-yellow-900/60 text-yellow-300 border-yellow-800",
    low:      "bg-green-900/60 text-green-300 border-green-800",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 font-mono text-xs border ${styles[urgency] || styles.low}`}>
      {urgency}
    </span>
  );
}

function LeadsTab() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterMinScore, setFilterMinScore] = useState("");
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterStatus)   params.set("status", filterStatus);
      if (filterSource)   params.set("source", filterSource);
      if (filterMinScore) params.set("min_score", filterMinScore);

      const [leadsData, statsData] = await Promise.all([
        api.get(`/leads${params.toString() ? "?" + params.toString() : ""}`),
        api.get("/stats"),
      ]);

      setLeads(leadsData.leads || []);
      setStats(statsData);
      setLastRefresh(new Date());
    } catch (err) {
      console.error("Failed to fetch leads:", err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterSource, filterMinScore]);

  // Initial load + auto-refresh every 60s
  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 60_000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const updateStatus = async (id, newStatus) => {
    try {
      await api.patch(`/leads/${id}`, { status: newStatus });
      // Optimistic update
      setLeads(prev => prev.map(l => l.id === id ? { ...l, status: newStatus } : l));
    } catch (err) {
      console.error("Failed to update lead status:", err);
    }
  };

  return (
    <div className="animate-fade-in" data-testid="leads-tab">
      {/* Stats Bar */}
      {stats && (
        <div className="border border-zinc-800 border-b-0 grid grid-cols-2 md:grid-cols-4 divide-x divide-zinc-800" data-testid="stats-bar">
          <div className="px-6 py-4 flex items-center gap-3">
            <Buildings size={18} className="text-amber-500 flex-shrink-0" />
            <div>
              <p className="font-mono text-xs text-zinc-500 uppercase tracking-widest">Total Leads</p>
              <p className="font-heading font-black text-white text-xl">{stats.total_leads ?? 0}</p>
            </div>
          </div>
          <div className="px-6 py-4 flex items-center gap-3">
            <ClockCounterClockwise size={18} className="text-amber-500 flex-shrink-0" />
            <div>
              <p className="font-mono text-xs text-zinc-500 uppercase tracking-widest">Today</p>
              <p className="font-heading font-black text-white text-xl">{stats.leads_today ?? 0}</p>
            </div>
          </div>
          <div className="px-6 py-4 flex items-center gap-3">
            <Lightning size={18} className="text-red-500 flex-shrink-0" />
            <div>
              <p className="font-mono text-xs text-zinc-500 uppercase tracking-widest">High Intent</p>
              <p className="font-heading font-black text-white text-xl">{stats.by_score_band?.high ?? 0}</p>
            </div>
          </div>
          <div className="px-6 py-4 flex items-center gap-3">
            <ChartBar size={18} className="text-amber-500 flex-shrink-0" />
            <div>
              <p className="font-mono text-xs text-zinc-500 uppercase tracking-widest">Reddit / Telegram</p>
              <p className="font-heading font-black text-white text-xl">
                {stats.by_source?.reddit ?? 0} / {stats.by_source?.telegram ?? 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="border border-zinc-800 p-4 flex flex-wrap items-center gap-3 bg-zinc-900/30" data-testid="leads-filter-bar">
        <span className="font-mono text-xs uppercase tracking-widest text-zinc-500">Filter:</span>
        <select className="select-terminal text-xs py-1.5" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="closed">Closed</option>
        </select>
        <select className="select-terminal text-xs py-1.5" value={filterSource} onChange={e => setFilterSource(e.target.value)}>
          <option value="">All sources</option>
          <option value="reddit">Reddit</option>
          <option value="telegram">Telegram</option>
        </select>
        <select className="select-terminal text-xs py-1.5" value={filterMinScore} onChange={e => setFilterMinScore(e.target.value)}>
          <option value="">Any score</option>
          <option value="7">Score ≥ 7</option>
          <option value="8">Score ≥ 8</option>
          <option value="9">Score ≥ 9</option>
        </select>
        <button className="btn-secondary text-xs py-1.5" onClick={fetchAll} disabled={loading} data-testid="leads-refresh-btn">
          <ArrowClockwise size={13} className={loading ? "animate-spin" : ""} />
          {loading ? "Refreshing…" : "Refresh"}
        </button>
        {lastRefresh && (
          <span className="ml-auto font-mono text-xs text-zinc-600">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Leads Table */}
      {leads.length > 0 ? (
        <div className="border border-zinc-800 border-t-0 overflow-x-auto" data-testid="leads-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50">
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Score</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Source</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Channel</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Urgency</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Snippet</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Link</th>
                <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-zinc-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {leads.map((lead, i) => (
                <tr key={lead.id || i} className="hover:bg-zinc-900/40 transition-colors" data-testid={`lead-row-${i}`}>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <ScoreBadge score={lead.score ?? 0} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <SourceTag source={lead.source} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-300 whitespace-nowrap">
                    {lead.channel || "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <UrgencyPill urgency={lead.urgency || "low"} />
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400 max-w-xs">
                    <span title={lead.snippet}>
                      {lead.snippet ? lead.snippet.slice(0, 120) + (lead.snippet.length > 120 ? "…" : "") : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {lead.url ? (
                      <a href={lead.url} target="_blank" rel="noreferrer"
                        className="font-mono text-xs text-amber-500 hover:text-amber-400">
                        View →
                      </a>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <select
                      className="select-terminal text-xs py-1"
                      value={lead.status || "new"}
                      onChange={e => updateStatus(lead.id, e.target.value)}
                      data-testid={`lead-status-${i}`}
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="closed">Closed</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="border border-zinc-800 border-t-0 p-12 flex flex-col items-center justify-center text-center" data-testid="leads-empty-state">
          <Lightning size={48} className="text-zinc-700 mb-4" />
          <p className="text-zinc-500 text-sm font-mono">No leads yet</p>
          <p className="text-zinc-600 text-xs mt-1">
            The Reddit & Telegram monitors will surface leads here once the API is running
          </p>
        </div>
      )}
    </div>
  );
}

// --- App ---
function App() {
  const [activeTab, setActiveTab] = useState("scraper");
  const [businesses, setBusinesses] = useState([]);

  return (
    <div className="min-h-screen bg-[#09090B]" data-testid="app-container">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="mb-6">
          <h1 className="font-heading text-3xl sm:text-4xl font-black tracking-tight text-white mb-1" data-testid="main-heading">
            Business Intelligence Scraper
          </h1>
          <p className="text-zinc-500 text-sm">
            Powered by Apify actors for Google Search & LinkedIn data extraction
          </p>
        </div>
        <TabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        <div className="mt-0">
          {activeTab === "scraper"  && <GoogleSearchTab businesses={businesses} setBusinesses={setBusinesses} />}
          {activeTab === "linkedin" && <LinkedInTab />}
          {activeTab === "chat"     && <ChatTab />}
          {activeTab === "leads"    && <LeadsTab />}
        </div>
      </main>
    </div>
  );
}

export default App;
