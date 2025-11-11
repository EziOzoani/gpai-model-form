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
import { Model } from "@/types/model";
import { useModelData } from "@/hooks/useModelData";
import { ModelHeatmap } from "@/components/ModelHeatmap";
import { ModelDetailPanel } from "@/components/ModelDetailPanel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Database, Filter, Loader2 } from "lucide-react";

const Index = () => {
  // Load model data from the generated JSON file
  const { models, loading, error, lastUpdated } = useModelData();
  
  // State management for user interactions
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [regionFilter, setRegionFilter] = useState<string>("all");
  const [sizeFilter, setSizeFilter] = useState<string>("all");
  const [minTransparency, setMinTransparency] = useState<number>(0);

  // Apply filters to the model list
  // This is memoised to prevent unnecessary recalculations
  const filteredModels = useMemo(() => {
    return models.filter((model) => {
      // Region filter - "all" bypasses this check
      if (regionFilter !== "all" && model.region !== regionFilter) return false;
      
      // Size filter - "all" bypasses this check
      if (sizeFilter !== "all" && model.size !== sizeFilter) return false;
      
      // Transparency threshold - models below minimum are excluded
      if (model.transparency_score.overall < minTransparency) return false;
      
      return true;
    });
  }, [models, regionFilter, sizeFilter, minTransparency]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-panel">
      {/* Header */}
      <header className="border-b border-border bg-panel/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-primary/10 p-3">
              <Database className="h-8 w-8 text-primary" />
            </div>
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
          <div className="text-sm text-muted-foreground">
            Showing <span className="font-semibold text-foreground">{filteredModels.length}</span>{" "}
            of <span className="font-semibold text-foreground">{models.length}</span> models
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
            <ModelHeatmap models={filteredModels} onModelClick={setSelectedModel} />
          )}
        </div>
      </main>

      {/* Detail Panel - Slides in from the right when a model is selected */}
      {selectedModel && (
        <ModelDetailPanel 
          model={selectedModel} 
          onClose={() => setSelectedModel(null)} 
        />
      )}
    </div>
  );
};

export default Index;
