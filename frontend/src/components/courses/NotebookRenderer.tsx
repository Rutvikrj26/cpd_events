import React, { useState, useEffect } from 'react';
import { Download, BookOpen, AlertCircle, Cpu, Layers, Terminal, FileCheck, Maximize2, Minimize2 } from 'lucide-react';
// @ts-ignore - no type definitions available
import { IpynbRenderer } from 'react-ipynb-renderer';
import { useTheme } from '@/components/theme-provider';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import './NotebookRenderer.css';

interface NotebookMetadata {
  filename?: string;
  cell_count?: number;
  language?: string;
  kernel?: string;
  colab_enabled?: boolean;
  has_outputs?: boolean;
}

interface NotebookRendererProps {
  fileUrl: string;
  metadata?: NotebookMetadata;
}

export const NotebookRenderer: React.FC<NotebookRendererProps> = ({ fileUrl, metadata = {} }) => {
  const [notebookData, setNotebookData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullWidth, setIsFullWidth] = useState(false);
  const { theme } = useTheme();

  // Dynamic Stylesheet Injection for Notebook Themes
  useEffect(() => {
    const linkId = 'notebook-theme-link';
    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    const themeFile = isDark ? '/styles/notebook-dark.css' : '/styles/notebook-light.css';

    // Remove existing link if it exists
    const existingLink = document.getElementById(linkId);
    if (existingLink) {
      existingLink.remove();
    }

    // Inject new link
    const link = document.createElement('link');
    link.id = linkId;
    link.rel = 'stylesheet';
    link.href = themeFile;
    document.head.appendChild(link);

    // Cleanup on unmount (optional, but good practice to avoid side effects on other pages)
    return () => {
      const linkToRemove = document.getElementById(linkId);
      if (linkToRemove) {
        linkToRemove.remove();
      }
    };
  }, [theme]);

  useEffect(() => {
    const fetchNotebook = async () => {
      try {
        setLoading(true);
        setError(null);

        let finalUrl = fileUrl;
        if (fileUrl && fileUrl.startsWith('/')) {
          // Construct absolute URL for local development
          const baseUrl = window.location.origin.replace('5173', '8000');
          finalUrl = `${baseUrl}${fileUrl}`;
        }

        const response = await fetch(finalUrl);

        if (!response.ok) {
          throw new Error(`Failed to fetch notebook: ${response.statusText}`);
        }

        const data = await response.json();
        setNotebookData(data);
      } catch (err) {
        console.error('Error loading notebook:', err);
        setError(err instanceof Error ? err.message : 'Failed to load notebook');
      } finally {
        setLoading(false);
      }
    };

    if (fileUrl) {
      fetchNotebook();
    }
  }, [fileUrl]);

  const getAbsoluteUrl = (url: string) => {
    if (url && url.startsWith('/')) {
      const baseUrl = window.location.origin.replace('5173', '8000');
      return `${baseUrl}${url}`;
    }
    return url;
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = getAbsoluteUrl(fileUrl);
    link.download = metadata.filename || 'notebook.ipynb';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-24">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-purple-600 mb-4"></div>
          <p className="text-muted-foreground font-medium">Parsing Notebook Content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-8 max-w-2xl mx-auto my-12">
        <div className="flex items-start">
          <AlertCircle className="h-6 w-6 text-destructive mt-0.5 mr-4 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-bold text-destructive">Error Loading Notebook</h3>
            <p className="text-muted-foreground mt-2">{error}</p>
            <button 
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-destructive text-white rounded-md text-sm font-medium hover:bg-destructive/90 transition-colors"
            >
              Retry Loading
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!notebookData) {
    return (
      <div className="bg-warning/10 border border-warning/20 rounded-xl p-8 max-w-2xl mx-auto my-12">
        <div className="flex items-start">
          <AlertCircle className="h-6 w-6 text-warning mt-0.5 mr-4 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-bold text-warning">Empty Notebook</h3>
            <p className="text-muted-foreground mt-2">The notebook file appears to be empty or invalid.</p>
          </div>
        </div>
      </div>
    );
  }

  // Safely extract metadata from notebook data if props metadata is missing info
  const displayLang = metadata.language || notebookData.metadata?.language_info?.name || 'Python';
  const displayKernel = metadata.kernel || notebookData.metadata?.kernelspec?.display_name || 'Python 3';
  const cellCount = metadata.cell_count !== undefined ? metadata.cell_count : (notebookData.cells?.length || 0);

  const NotebookContent = () => (
    <div className="notebook-renderer-root">
      <IpynbRenderer ipynb={notebookData} />
    </div>
  );

  return (
    <>
      <div className="max-w-[1400px] mx-auto space-y-6 pb-20">
        {/* Header with metadata and actions */}
        <div className="bg-card border rounded-2xl p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center">
                  <BookOpen className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold tracking-tight">
                    {metadata.filename || 'Jupyter Notebook'}
                  </h3>
                  <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Interactive Document</p>
                </div>
              </div>

              {/* Metadata badges */}
              <div className="flex flex-wrap gap-2 pt-1">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-100 gap-1.5">
                  <Terminal className="h-3 w-3" />
                  {displayLang}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-slate-50 text-slate-700 border border-slate-200 gap-1.5">
                  <Layers className="h-3 w-3" />
                  {cellCount} Cells
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-purple-50 text-purple-700 border border-purple-100 gap-1.5">
                  <Cpu className="h-3 w-3" />
                  {displayKernel}
                </span>
                {notebookData.cells?.some((c: any) => c.outputs?.length > 0) && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-green-50 text-green-700 border border-green-100 gap-1.5">
                    <FileCheck className="h-3 w-3" />
                    Pre-computed Results
                  </span>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3 flex-shrink-0">
              <button
                onClick={() => setIsFullWidth(true)}
                className="p-2.5 bg-background border rounded-xl hover:bg-muted transition-all text-muted-foreground hover:text-foreground"
                title="Full Screen"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
              
              <button
                onClick={handleDownload}
                className="inline-flex items-center px-5 py-2.5 bg-background border text-sm font-bold rounded-xl hover:bg-muted transition-all gap-2"
              >
                <Download className="h-4 w-4" />
                Download
              </button>
            </div>
          </div>
        </div>

        {/* Notebook content */}
        <NotebookContent />
      </div>

      {/* Full Screen Modal */}
      <Dialog open={isFullWidth} onOpenChange={setIsFullWidth}>
        <DialogContent className="max-w-[95vw] w-full h-[95vh] flex flex-col p-0 gap-0 bg-background/95 backdrop-blur-sm">
          <DialogHeader className="px-6 py-4 border-b flex-shrink-0 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <BookOpen className="h-5 w-5 text-purple-600" />
              <DialogTitle>{metadata.filename || 'Jupyter Notebook'}</DialogTitle>
            </div>
            <div className="flex items-center gap-2">
               {/* Close button is handled by DialogPrimitive.Close inside DialogContent */}
            </div>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto p-6 bg-background">
             <NotebookContent />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default NotebookRenderer;
