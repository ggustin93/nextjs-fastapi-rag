'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { ChevronDown, FileText, Globe, Database, Zap, ArrowLeft, ExternalLink, Search, Maximize2, X } from 'lucide-react';
import Link from 'next/link';

interface SystemConfig {
  llm: { model: string; provider: string };
  embeddings: { model: string; dimensions: number };
  chunking: { chunk_size: number; chunk_overlap: number };
  retrieval?: {
    query_expansion_enabled: boolean;
    query_expansion_model: string;
    title_rerank_enabled: boolean;
    title_rerank_boost: number;
    rrf_k: number;
    similarity_threshold: number;
  };
}

interface Document {
  filename: string;
  path: string;
  size: number;
  type: string;
  ingested_at: string;
}

interface WebSource {
  url: string;
  title: string;
  pages_count: number;
  scraped_at: string;
}

// Format file size
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Stat card
function StatCard({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="bg-white rounded-lg px-4 py-3 border border-slate-200">
      <div className="text-xl font-semibold text-slate-800">{value}</div>
      <div className="text-xs text-slate-500 uppercase">{label}</div>
    </div>
  );
}

// Mermaid singleton for performance
let mermaidInstance: typeof import('mermaid').default | null = null;

async function getMermaid() {
  if (mermaidInstance) return mermaidInstance;
  const mermaid = (await import('mermaid')).default;
  mermaid.initialize({
    startOnLoad: false,
    theme: 'neutral',
    themeVariables: { fontSize: '16px' },
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      nodeSpacing: 50,
      rankSpacing: 80,
    },
  });
  mermaidInstance = mermaid;
  return mermaid;
}

// Mermaid diagram with loading state, error handling, and fullscreen modal
function MermaidDiagram({ chart, ariaLabel }: { chart: string; ariaLabel?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const renderDiagram = useCallback(async (targetRef: HTMLDivElement, id: string) => {
    const mermaid = await getMermaid();
    targetRef.innerHTML = '';
    const { svg } = await mermaid.render(id, chart);
    targetRef.innerHTML = svg;

    // Post-render SVG adjustments for proper sizing
    const svgElement = targetRef.querySelector('svg');
    if (svgElement) {
      svgElement.style.maxWidth = '100%';
      svgElement.style.height = 'auto';
      svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    }
  }, [chart]);

  useEffect(() => {
    let cancelled = false;

    const loadMermaid = async () => {
      if (ref.current && !cancelled) {
        try {
          await renderDiagram(ref.current, `mermaid-${Date.now()}`);
          if (!cancelled) {
            setIsLoading(false);
            setError(null);
          }
        } catch (err) {
          console.error('Mermaid error:', err);
          if (!cancelled) {
            setError(err instanceof Error ? err.message : 'Diagram render failed');
            setIsLoading(false);
          }
        }
      }
    };
    loadMermaid();

    return () => { cancelled = true; };
  }, [renderDiagram]);

  // Render diagram in modal when expanded
  useEffect(() => {
    if (isExpanded && modalRef.current) {
      renderDiagram(modalRef.current, `mermaid-modal-${Date.now()}`).catch(console.error);
    }
  }, [isExpanded, renderDiagram]);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 rounded border border-red-200 text-sm text-red-600">
        Failed to render diagram: {error}
      </div>
    );
  }

  return (
    <>
      <figure role="img" aria-label={ariaLabel || 'Flowchart diagram'} className="relative">
        {/* Expand button */}
        <button
          onClick={() => setIsExpanded(true)}
          className="absolute top-2 right-2 z-10 p-1.5 bg-white/90 rounded border border-slate-200 hover:bg-slate-100 transition-colors"
          aria-label="Expand diagram to fullscreen"
          title="Expand diagram"
        >
          <Maximize2 className="w-4 h-4 text-slate-600" />
        </button>

        {/* Scroll container with fade indicator */}
        <div className="relative">
          <div className="overflow-x-auto touch-pan-x scrollbar-thin scrollbar-thumb-slate-300">
            <div className="flex justify-center min-h-[200px] items-center" style={{ minWidth: '800px' }}>
              {isLoading && (
                <div role="status" aria-live="polite" className="text-sm text-slate-400 animate-pulse">
                  Loading diagram...
                </div>
              )}
              <div ref={ref} className={`w-full ${isLoading ? 'hidden' : ''}`} />
            </div>
          </div>

          {/* Fade indicator (right edge) - only show when not loading */}
          {!isLoading && (
            <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none" />
          )}
        </div>

        {/* Screen reader description */}
        <figcaption className="sr-only">
          {ariaLabel || 'Flowchart showing the data processing pipeline'}
        </figcaption>
      </figure>

      {/* Fullscreen modal */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setIsExpanded(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Expanded diagram view"
        >
          <div
            className="bg-white rounded-xl max-w-6xl w-full max-h-[90vh] overflow-auto p-6"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium text-slate-800">Pipeline Diagram</h3>
              <button
                onClick={() => setIsExpanded(false)}
                className="p-1 hover:bg-slate-100 rounded transition-colors"
                aria-label="Close expanded view"
              >
                <X className="w-5 h-5 text-slate-600" />
              </button>
            </div>
            <div ref={modalRef} className="w-full flex justify-center" />
          </div>
        </div>
      )}
    </>
  );
}

// Collapsible section
function Section({
  title,
  icon: Icon,
  isOpen,
  onToggle,
  badge,
  children
}: {
  title: string;
  icon: typeof FileText;
  isOpen: boolean;
  onToggle: () => void;
  badge?: number;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg border border-slate-200">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-slate-600" />
          <h2 className="font-medium text-slate-800">{title}</h2>
          {badge !== undefined && (
            <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full">{badge}</span>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && <div className="p-4 pt-4 border-t border-slate-100">{children}</div>}
    </div>
  );
}

export default function SystemPage() {
  const [openSections, setOpenSections] = useState<string[]>(['sources']);
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [webSources, setWebSources] = useState<WebSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    const fetchAll = async () => {
      setLoading(true);
      try {
        const [configRes, docsRes, sourcesRes] = await Promise.all([
          fetch(`${apiUrl}/system/config`),
          fetch(`${apiUrl}/system/documents`),
          fetch(`${apiUrl}/system/sources`),
        ]);

        if (configRes.ok) setConfig(await configRes.json());
        if (docsRes.ok) {
          const data = await docsRes.json();
          setDocuments(data.documents || []);
        }
        if (sourcesRes.ok) {
          const data = await sourcesRes.json();
          setWebSources(data.sources || []);
        }
      } catch (e) {
        console.error('Failed to fetch system data:', e);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const toggle = (id: string) => {
    setOpenSections(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  const isOpen = (id: string) => openSections.includes(id);

  // Filter PDFs and count pages
  const pdfDocs = documents.filter(d => d.type === 'pdf');
  const totalPages = webSources.reduce((acc, s) => acc + s.pages_count, 0);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
            <ArrowLeft className="w-4 h-4" />
            Back to Chat
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Title */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-slate-900 mb-1">Ingested Sources</h1>
          <p className="text-sm text-slate-600">Documents and websites indexed in the knowledge base</p>
        </div>

        {/* Stats - skeleton loading */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          {loading ? (
            <>
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white rounded-lg px-4 py-3 border border-slate-200 animate-pulse">
                  <div className="h-6 bg-slate-200 rounded w-12 mb-1" />
                  <div className="h-3 bg-slate-100 rounded w-16" />
                </div>
              ))}
            </>
          ) : (
            <>
              <StatCard value={pdfDocs.length} label="Documents" />
              <StatCard value={webSources.length} label="Websites" />
              <StatCard value={totalPages} label="Web Pages" />
              <StatCard value={config?.llm.model?.split('/').pop() || '-'} label="LLM" />
            </>
          )}
        </div>

        {/* Sections */}
        <div className="space-y-3">
          {/* Data Sources - PRIMARY */}
          <Section
            title="Data Sources"
            icon={Database}
            isOpen={isOpen('sources')}
            onToggle={() => toggle('sources')}
            badge={pdfDocs.length + webSources.length}
          >
            <div className="grid grid-cols-2 gap-6">
              {/* PDF Documents */}
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5" />
                  PDF Documents
                  <span className="text-slate-400 font-normal">({pdfDocs.length})</span>
                </h4>
                {loading ? (
                  <div className="text-sm text-slate-400 py-4">Loading...</div>
                ) : pdfDocs.length === 0 ? (
                  <div className="text-sm text-slate-400 py-4">No documents ingested</div>
                ) : (
                  <div className="space-y-1.5 max-h-80 overflow-y-auto">
                    {pdfDocs.map((doc, i) => (
                      <div key={i} className="flex justify-between text-sm py-2 px-3 bg-slate-50 rounded border border-slate-100 hover:border-slate-200">
                        <span className="text-slate-700 truncate flex-1" title={doc.filename}>
                          {doc.filename}
                        </span>
                        <span className="text-slate-400 text-xs ml-2 shrink-0">{formatSize(doc.size)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Web Sources */}
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5" />
                  Web Sources
                  <span className="text-slate-400 font-normal">({webSources.length})</span>
                </h4>
                {loading ? (
                  <div className="text-sm text-slate-400 py-4">Loading...</div>
                ) : webSources.length === 0 ? (
                  <div className="text-sm text-slate-400 py-4">No websites scraped</div>
                ) : (
                  <div className="space-y-1.5 max-h-80 overflow-y-auto">
                    {webSources.map((site, i) => {
                      // Extract domain from URL for display
                      const domain = (() => {
                        try {
                          return new URL(site.url).hostname.replace('www.', '');
                        } catch {
                          return site.title;
                        }
                      })();

                      return (
                        <div key={i} className="flex justify-between items-center text-sm py-2 px-3 bg-slate-50 rounded border border-slate-100 hover:border-slate-200">
                          <a
                            href={site.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-700 hover:text-blue-600 truncate flex-1 flex items-center gap-1.5"
                            title={site.url}
                          >
                            {domain}
                            <ExternalLink className="w-3 h-3 text-slate-400 shrink-0" />
                          </a>
                          <span className="text-slate-400 text-xs ml-2 shrink-0">{site.pages_count} pages</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </Section>

          {/* Ingestion Pipeline */}
          <Section title="Ingestion Pipeline" icon={Database} isOpen={isOpen('ingestion')} onToggle={() => toggle('ingestion')}>
            <div className="space-y-6">
              {/* Mermaid Diagram */}
              <div className="bg-white rounded-lg border border-slate-200 p-6">
                <MermaidDiagram
                  ariaLabel="Ingestion pipeline flowchart"
                  chart={`graph LR
    subgraph Sources
        PDF[PDF Files]
        WEB[Web Pages]
    end

    PDF --> DOC[Docling]
    WEB --> C4A[Crawl4AI]
    DOC --> MD[Markdown]
    C4A --> MD
    MD --> CHK[Hybrid Chunking]
    CHK --> EMB[Embeddings]
    EMB --> DB[(pgvector)]

    style PDF fill:#ffe4e6,stroke:#f43f5e
    style WEB fill:#e0f2fe,stroke:#0ea5e9
    style DOC fill:#ffe4e6,stroke:#f43f5e
    style C4A fill:#e0f2fe,stroke:#0ea5e9
    style CHK fill:#fef3c7,stroke:#f59e0b
    style EMB fill:#d1fae5,stroke:#10b981
    style DB fill:#d1fae5,stroke:#10b981`}
                />
              </div>

              {/* Steps */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-rose-50 rounded-lg p-4 border border-rose-200">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-rose-600" />
                    <h4 className="font-medium text-slate-800 text-sm">Docling</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    Parses PDFs preserving structure (tables, headers, lists).
                  </p>
                </div>

                <div className="bg-sky-50 rounded-lg p-4 border border-sky-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Globe className="w-4 h-4 text-sky-600" />
                    <h4 className="font-medium text-slate-800 text-sm">Crawl4AI</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    Scrapes websites with JS rendering, extracts clean markdown.
                  </p>
                </div>

                <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-amber-600" />
                    <h4 className="font-medium text-slate-800 text-sm">Hybrid Chunking</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    Token-aware splits respecting document structure (sections, tables). ~{config?.chunking.chunk_size || 512} tokens with heading context.
                  </p>
                </div>

                <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="w-4 h-4 text-emerald-600" />
                    <h4 className="font-medium text-slate-800 text-sm">Embeddings</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    OpenAI text-embedding-3-small → {config?.embeddings.dimensions || 1536}D vectors in pgvector.
                  </p>
                </div>
              </div>

              {/* Key insight */}
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                <p className="text-sm text-slate-600">
                  <span className="font-medium text-slate-700">Why Markdown?</span> Universal format that preserves semantics (headings, lists, tables) while staying lightweight. LLMs understand structured context better.
                </p>
              </div>
            </div>
          </Section>

          {/* Retrieval Pipeline */}
          <Section title="Retrieval Pipeline" icon={Search} isOpen={isOpen('pipeline')} onToggle={() => toggle('pipeline')}>
            <div className="space-y-6">
              {/* Mermaid Diagram */}
              <div className="bg-white rounded-lg border border-slate-200 p-6">
                <MermaidDiagram
                  ariaLabel="Retrieval pipeline: Query → Expansion → Embedding → Semantic + Lexical Search → RRF Fusion → Rerank → LLM"
                  chart={`graph LR
    Q[Query] --> QE[Query Expansion]
    QE --> E[Embed]
    E --> V[Semantic Search]
    E --> F[Lexical Search]
    V --> |Top-K| R[RRF Fusion]
    F --> |Top-K| R
    R --> TR[Rerank]
    TR --> L[LLM]

    style Q fill:#f1f5f9,stroke:#64748b
    style QE fill:#fef3c7,stroke:#f59e0b
    style E fill:#d1fae5,stroke:#10b981
    style V fill:#ede9fe,stroke:#8b5cf6
    style F fill:#e0e7ff,stroke:#6366f1
    style R fill:#ccfbf1,stroke:#14b8a6
    style TR fill:#fce7f3,stroke:#ec4899
    style L fill:#fef3c7,stroke:#d97706`}
                />
              </div>

              {/* Explanation - 5 steps now */}
              <div className="grid grid-cols-5 gap-3">
                <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <div className="w-4 h-4 rounded-full bg-amber-600 text-white text-[10px] flex items-center justify-center font-medium">1</div>
                    <h4 className="font-medium text-slate-800 text-xs">Query Expansion</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    {config?.retrieval?.query_expansion_enabled ? (
                      <>LLM adds domain synonyms via <span className="font-mono text-[10px]">{config.retrieval.query_expansion_model}</span></>
                    ) : (
                      <span className="text-slate-400">Disabled</span>
                    )}
                  </p>
                </div>

                <div className="bg-violet-50 rounded-lg p-3 border border-violet-200">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <div className="w-4 h-4 rounded-full bg-violet-600 text-white text-[10px] flex items-center justify-center font-medium">2</div>
                    <h4 className="font-medium text-slate-800 text-xs">Vector Search</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    Cosine similarity on {config?.embeddings.dimensions || 1536}D embeddings.
                  </p>
                </div>

                <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <div className="w-4 h-4 rounded-full bg-indigo-600 text-white text-[10px] flex items-center justify-center font-medium">3</div>
                    <h4 className="font-medium text-slate-800 text-xs">French FTS</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    PostgreSQL with French stemming for exact matches.
                  </p>
                </div>

                <div className="bg-teal-50 rounded-lg p-3 border border-teal-200">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <div className="w-4 h-4 rounded-full bg-teal-600 text-white text-[10px] flex items-center justify-center font-medium">4</div>
                    <h4 className="font-medium text-slate-800 text-xs">RRF Fusion</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    Merges rankings with k={config?.retrieval?.rrf_k || 60}.
                  </p>
                </div>

                <div className="bg-pink-50 rounded-lg p-3 border border-pink-200">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <div className="w-4 h-4 rounded-full bg-pink-600 text-white text-[10px] flex items-center justify-center font-medium">5</div>
                    <h4 className="font-medium text-slate-800 text-xs">Title Rerank</h4>
                  </div>
                  <p className="text-xs text-slate-600">
                    {config?.retrieval?.title_rerank_enabled ? (
                      <>Boosts matching titles +{((config.retrieval.title_rerank_boost || 0.15) * 100).toFixed(0)}%</>
                    ) : (
                      <span className="text-slate-400">Disabled</span>
                    )}
                  </p>
                </div>
              </div>

              {/* Pipeline rationale */}
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                <p className="text-sm text-slate-600">
                  <span className="font-medium text-slate-700">Why this pipeline?</span>{' '}
                  Query expansion addresses vocabulary mismatch (user terms ≠ document terms).
                  Title reranking boosts precision when document titles match query keywords.
                  RRF fusion combines semantic and lexical signals without manual weight tuning.
                </p>
              </div>

              {/* Formula */}
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-slate-600">Reciprocal Rank Fusion:</span>
                    <code className="ml-2 text-sm font-mono text-slate-800">RRF(d) = Σ 1/(k + rank)</code>
                    <span className="ml-2 text-xs text-slate-500">k={config?.retrieval?.rrf_k || 60}</span>
                  </div>
                  <span className="text-xs text-slate-500">Documents ranked high in both methods surface first</span>
                </div>
              </div>
            </div>
          </Section>

          {/* Config - Secondary */}
          <Section title="Configuration" icon={Zap} isOpen={isOpen('config')} onToggle={() => toggle('config')}>
            {config ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded p-3 border border-slate-200">
                  <div className="text-xs text-slate-500 uppercase mb-1">LLM</div>
                  <div className="font-medium text-slate-800">{config.llm.model}</div>
                  <div className="text-xs text-slate-500">Provider: {config.llm.provider}</div>
                </div>
                <div className="bg-slate-50 rounded p-3 border border-slate-200">
                  <div className="text-xs text-slate-500 uppercase mb-1">Embeddings</div>
                  <div className="font-medium text-slate-800">{config.embeddings.model}</div>
                  <div className="text-xs text-slate-500">{config.embeddings.dimensions} dimensions</div>
                </div>
                <div className="bg-slate-50 rounded p-3 border border-slate-200">
                  <div className="text-xs text-slate-500 uppercase mb-1">Chunking</div>
                  <div className="font-medium text-slate-800">{config.chunking.chunk_size} tokens</div>
                  <div className="text-xs text-slate-500">Overlap: {config.chunking.chunk_overlap}</div>
                </div>
                <div className="bg-slate-50 rounded p-3 border border-slate-200">
                  <div className="text-xs text-slate-500 uppercase mb-1">Vector DB</div>
                  <div className="font-medium text-slate-800">Supabase pgvector</div>
                  <div className="text-xs text-slate-500">HNSW index</div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-400 py-4">Loading configuration...</div>
            )}
          </Section>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-slate-500">
          Next.js + FastAPI + PydanticAI + Supabase pgvector
        </div>
      </main>
    </div>
  );
}
