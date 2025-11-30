import { useState, useMemo } from "react";
import { Model } from "@/types/model";
import { useCleanedModelData } from "@/hooks/useCleanedModelData";
import { ModelHeatmap } from "@/components/ModelHeatmap";
import { ModelDetailPanel } from "@/components/ModelDetailPanel";
import { FilterPanel } from "@/components/FilterPanel";
import { Button } from "@/components/ui/button";
import { Database, Loader2, GitCompare, BarChart3, Shield } from "lucide-react";
import { Link } from "react-router-dom";

const IndexEnhanced = () => {
  // State management
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [regionFilter, setRegionFilter] = useState<string>("all");
  const [sizeFilter, setSizeFilter] = useState<string>("all");
  const [minTransparency, setMinTransparency] = useState<number>(0);
  const [codeOfPracticeFilter, setCodeOfPracticeFilter] = useState<string>("all");
  const [dateCutoff, setDateCutoff] = useState<string>("2024-09-30");
  const [sortBy, setSortBy] = useState<string>('overall');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [selectionMode, setSelectionMode] = useState(false);

  // Load cleaned model data with filters
  const { models, loading, error, lastUpdated, signatoriesCount } = useCleanedModelData(
    regionFilter,
    sizeFilter,
    codeOfPracticeFilter,
    dateCutoff
  );

  // Handle sorting
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // Handle model selection
  const handleModelSelect = (modelName: string) => {
    setSelectedModels(prev => {
      if (prev.includes(modelName)) {
        return prev.filter(name => name !== modelName);
      }
      if (prev.length >= 4) {
        alert('You can compare up to 4 models at a time');
        return prev;
      }
      return [...prev, modelName];
    });
  };

  // Apply transparency filter and sorting
  const filteredModels = useMemo(() => {
    const filtered = models.filter((model) => {
      if (model.transparency_score.overall < minTransparency) return false;
      return true;
    });

    return filtered.sort((a, b) => {
      let aValue: number | string = 0;
      let bValue: number | string = 0;

      if (sortBy === 'model_name') {
        aValue = a.model_name.toLowerCase();
        bValue = b.model_name.toLowerCase();
      } else if (sortBy === 'overall') {
        aValue = a.transparency_score.overall;
        bValue = b.transparency_score.overall;
      } else {
        aValue = a.transparency_score.sections[sortBy as keyof typeof a.transparency_score.sections] || 0;
        bValue = b.transparency_score.sections[sortBy as keyof typeof b.transparency_score.sections] || 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
      }

      return sortOrder === 'asc' ? (aValue as number) - (bValue as number) : (bValue as number) - (aValue as number);
    });
  }, [models, minTransparency, sortBy, sortOrder]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-panel">
      {/* Header */}
      <header className="border-b border-border bg-panel/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <img 
                src="./appliedAI_horizontal_rgb_RZ.png" 
                alt="AppliedAI" 
                className="h-12 object-contain"
              />
              <div>
                <h1 className="text-3xl font-bold text-foreground">
                  GPAI Model Documentation Dashboard
                </h1>
                <p className="mt-2 text-muted-foreground max-w-3xl">
                  Comprehensive transparency tracking for general-purpose AI models with EU AI Code of Practice compliance monitoring.
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Link to="/analytics">
                <Button variant="outline" size="sm">
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Analytics
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Enhanced Filters */}
      <FilterPanel
        regionFilter={regionFilter}
        setRegionFilter={setRegionFilter}
        sizeFilter={sizeFilter}
        setSizeFilter={setSizeFilter}
        minTransparency={minTransparency}
        setMinTransparency={setMinTransparency}
        codeOfPracticeFilter={codeOfPracticeFilter}
        setCodeOfPracticeFilter={setCodeOfPracticeFilter}
        dateCutoff={dateCutoff}
        setDateCutoff={setDateCutoff}
      />

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="text-sm text-muted-foreground">
              Showing <span className="font-semibold text-foreground">{filteredModels.length}</span>{" "}
              of <span className="font-semibold text-foreground">{models.length}</span> models
              {codeOfPracticeFilter === 'signatories' && (
                <span className="ml-2">
                  (<Shield className="h-3 w-3 inline" /> {signatoriesCount} signatories)
                </span>
              )}
            </div>
            <Button
              variant={selectionMode ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setSelectionMode(!selectionMode);
                if (!selectionMode) setSelectedModels([]);
              }}
              className="flex items-center gap-2"
            >
              <GitCompare className="h-4 w-4" />
              {selectionMode ? 'Exit Compare Mode' : 'Compare Models'}
            </Button>
            {selectionMode && selectedModels.length >= 2 && (
              <Link to={`/compare?models=${selectedModels.join(',')}`}>
                <Button variant="default" size="sm">
                  Compare {selectedModels.length} Models
                </Button>
              </Link>
            )}
          </div>
          <div className="bg-red-500/15 border-2 border-red-500/30 text-red-700 dark:text-red-400 px-6 py-3 rounded-lg text-base font-semibold flex-1 text-center">
            ⚠️ THIS DASHBOARD IS A WORK IN PROGRESS !!
          </div>
          <div className="text-sm text-muted-foreground">
            Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleDateString('en-GB') : 'Loading...'}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card/50 p-6 shadow-xl backdrop-blur-sm">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-4 text-sm text-muted-foreground">Loading model data...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-destructive">{error}</p>
            </div>
          ) : filteredModels.length === 0 ? (
            <div className="text-center py-12">
              <Database className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-lg font-medium text-foreground">No models found</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Try adjusting your filters to see more results
              </p>
            </div>
          ) : (
            <ModelHeatmap
              models={filteredModels}
              onModelClick={setSelectedModel}
              onSort={handleSort}
              sortBy={sortBy}
              sortOrder={sortOrder}
              selectionMode={selectionMode}
              selectedModels={selectedModels}
              onModelSelect={handleModelSelect}
            />
          )}
        </div>
      </main>

      {selectedModel && (
        <ModelDetailPanel
          model={selectedModel}
          onClose={() => setSelectedModel(null)}
        />
      )}
    </div>
  );
};

export default IndexEnhanced;