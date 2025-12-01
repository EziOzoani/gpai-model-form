/**
 * Main Dashboard Page Component
 * 
 * This is the primary interface for the GPAI Model Documentation Dashboard.
 * It provides filtering capabilities and displays model transparency scores
 * in an interactive heatmap format.
 * 
 * Features:
 * - Region-based filtering (US, EU, Non-EU)
 * - Model size filtering (Big >10B params, Small ≤10B params)
 * - Transparency score threshold filtering
 * - Interactive heatmap with traffic light indicators
 * - Detail panel for viewing complete model documentation
 * 
 * @author GPAI Documentation Pipeline
 * @date November 2024
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Model } from "@/types/model";
import { useModelData } from "@/hooks/useModelData";
import { ModelHeatmap } from "@/components/ModelHeatmap";
import { ModelDetailPanel } from "@/components/ModelDetailPanel";
import { FeedbackDialog } from "@/components/FeedbackDialog";
import { FeedbackButton } from "@/components/FeedbackButton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Database, Filter, Loader2, GitCompare } from "lucide-react";

const Index = () => {
  // Load model data from the generated JSON file
  const { models, loading, error, lastUpdated } = useModelData();
  const navigate = useNavigate();
  
  // State management for user interactions
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [regionFilter, setRegionFilter] = useState<string>("all");
  const [sizeFilter, setSizeFilter] = useState<string>("all");
  const [minTransparency, setMinTransparency] = useState<number>(0);
  const [sortBy, setSortBy] = useState<string>('overall');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [selectionMode, setSelectionMode] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackContext, setFeedbackContext] = useState<any>({ type: 'general' });

  // Handle sorting
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // Handle model selection for comparison
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

  // Apply filters and sorting to the model list
  // This is memoised to prevent unnecessary recalculations
  const filteredModels = useMemo(() => {
    const filtered = models.filter((model) => {
      // Region filter - "all" bypasses this check
      if (regionFilter !== "all" && model.region !== regionFilter) return false;
      
      // Size filter - "all" bypasses this check
      if (sizeFilter !== "all" && model.size !== sizeFilter) return false;
      
      // Transparency threshold - models below minimum are excluded
      if (model.transparency_score.overall < minTransparency) return false;
      
      return true;
    });

    // Apply sorting
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
        // Sort by section score
        aValue = a.transparency_score.sections[sortBy as keyof typeof a.transparency_score.sections] || 0;
        bValue = b.transparency_score.sections[sortBy as keyof typeof b.transparency_score.sections] || 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
      }

      return sortOrder === 'asc' ? (aValue as number) - (bValue as number) : (bValue as number) - (aValue as number);
    });
  }, [models, regionFilter, sizeFilter, minTransparency, sortBy, sortOrder]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-panel">
      {/* Header */}
      <header className="border-b border-border bg-panel/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-start justify-between gap-4">
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
                  Comprehensive transparency tracking for general-purpose AI models. Filter by
                  region, size, and view per-section documentation completeness with traffic-light
                  indicators.
                </p>
              </div>
            </div>
            <FeedbackButton 
              onClick={() => {
                setFeedbackContext({ type: 'general' });
                setFeedbackOpen(true);
              }}
            />
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="border-b border-border bg-card/30 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center gap-3 mb-4">
            <Filter className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Filters
            </h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="region-filter" className="text-sm text-muted-foreground">
                Region
              </Label>
              <Select value={regionFilter} onValueChange={setRegionFilter}>
                <SelectTrigger id="region-filter" className="bg-panel">
                  <SelectValue placeholder="All regions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Regions</SelectItem>
                  <SelectItem value="US">US</SelectItem>
                  <SelectItem value="EU">EU</SelectItem>
                  <SelectItem value="Non-EU">Non-EU</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="size-filter" className="text-sm text-muted-foreground">
                Model Size
              </Label>
              <Select value={sizeFilter} onValueChange={setSizeFilter}>
                <SelectTrigger id="size-filter" className="bg-panel">
                  <SelectValue placeholder="All sizes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sizes</SelectItem>
                  <SelectItem value="Big">Big ({">"}10B parameters)</SelectItem>
                  <SelectItem value="Small">Small (≤10B parameters)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="transparency-slider" className="text-sm text-muted-foreground">
                Min. Transparency: {minTransparency}%
              </Label>
              <Slider
                id="transparency-slider"
                min={0}
                max={100}
                step={5}
                value={[minTransparency]}
                onValueChange={(value) => setMinTransparency(value[0])}
                className="mt-2"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="text-sm text-muted-foreground">
              Showing <span className="font-semibold text-foreground">{filteredModels.length}</span>{" "}
              of <span className="font-semibold text-foreground">{models.length}</span> models
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
              <Button
                variant="default"
                size="sm"
                onClick={() => {
                  // Open comparison view
                  navigate(`/compare?models=${selectedModels.join(',')}`);
                }}
              >
                Compare {selectedModels.length} Models
              </Button>
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
          {/* Show loading state whilst fetching data */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Loading model data...</span>
            </div>
          ) : error ? (
            // Display error message if data loading failed
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground mb-2">{error}</p>
              <ModelHeatmap models={filteredModels} onModelClick={setSelectedModel} />
            </div>
          ) : (
            // Display the heatmap once data is loaded
            <ModelHeatmap 
              models={filteredModels} 
              onModelClick={setSelectedModel}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              selectedModels={selectedModels}
              onModelSelect={handleModelSelect}
              selectionMode={selectionMode}
            />
          )}
        </div>
      </main>

      {/* Detail Panel - Slides in from the right when a model is selected */}
      {selectedModel && (
        <ModelDetailPanel 
          model={selectedModel} 
          onClose={() => setSelectedModel(null)}
          onFeedback={(section?: string) => {
            setFeedbackContext({
              type: 'model',
              modelName: selectedModel.model_name,
              modelId: selectedModel.model_name,
              section
            });
            setFeedbackOpen(true);
          }}
        />
      )}
      
      <FeedbackDialog
        isOpen={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        context={feedbackContext}
      />
    </div>
  );
};

export default Index;
