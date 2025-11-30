import { useState } from "react";
import { Model, SectionData, FieldData } from "@/types/model";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FeedbackButton } from "@/components/FeedbackButton";
import { X, ExternalLink, Calendar, Building2, Globe, Database, Info, Star, MessageSquare } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ModelDetailPanelProps {
  model: Model;
  onClose: () => void;
  onFeedback?: (section?: string) => void;
}

// Configuration for each documentation section
// Maps section keys to their display titles and icons
const SECTION_INFO = [
  { key: "general", title: "General Information", icon: Building2 },
  { key: "properties", title: "Model Properties", icon: Database },
  { key: "distribution", title: "Distribution & Licenses", icon: Globe },
  { key: "use", title: "Use Cases & Integration", icon: Globe },
  { key: "data", title: "Training Data", icon: Database },
  { key: "training", title: "Training Process", icon: Database },
  { key: "compute", title: "Computational Resources", icon: Database },
  { key: "energy", title: "Energy Consumption", icon: Database },
];

// Field labels for each section to provide proper formatting
// Maps field keys to human-readable labels
const FIELD_LABELS: Record<string, Record<string, string>> = {
  general: {
    legal_name: "Legal Name",
    model_name: "Model Name",
    authenticity: "Authenticity",
    release_date: "Release Date",
    eu_release_date: "EU Market Release Date",
    dependencies: "Dependencies",
  },
  properties: {
    architecture: "Architecture",
    design_specs: "Design Specifications",
    input_modalities: "Input Modalities",
    output_modalities: "Output Modalities",
    total_params: "Total Parameters",
  },
  distribution: {
    channels: "Distribution Channels",
    license_link: "License Link",
    license_type: "License Type",
    additional_assets: "Additional Assets",
  },
  use: {
    aup_link: "Acceptable Use Policy",
    intended_or_restricted: "Intended or Restricted Uses",
    integration_types: "Integration Types",
    integration_means: "Integration Means",
    required_hw: "Required Hardware",
    required_sw: "Required Software",
  },
  data: {
    types: "Data Types",
    provenance: "Data Provenance",
    obtain_select: "Data Obtaining & Selection",
    num_points: "Number of Data Points",
    scope_characteristics: "Scope & Characteristics",
    curation: "Data Curation",
    unsuitable_detection: "Unsuitable Content Detection",
    bias_measures: "Bias Mitigation Measures",
  },
  training: {
    process_design: "Training Process Design",
    decision_rationale: "Design Decision Rationale",
  },
  compute: {
    training_time: "Training Time",
    train_flops: "Training FLOPs",
    train_measurement: "Training Measurement Method",
  },
  energy: {
    training_mwh: "Training Energy (MWh)",
    methodology: "Energy Measurement Methodology",
    inference_flops: "Inference FLOPs",
    inference_methodology: "Inference Methodology",
  },
};

export const ModelDetailPanel = ({ model, onClose, onFeedback }: ModelDetailPanelProps) => {
  // State to control view mode - summary or full documentation
  const [showFullDocs, setShowFullDocs] = useState(false);
  // Determine the colour variant based on transparency score
  // Higher scores (80%+) are success, medium (40-79%) are warning, low (<40%) are danger
  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return "success";
    if (score >= 0.4) return "warning";
    return "danger";
  };

  // Helper function to render a field with its value and source information
  // Handles different data types and displays info icons with tooltips
  const renderField = (
    fieldName: string,
    fieldData: FieldData | string | string[] | Record<string, string> | undefined,
    label: string
  ) => {
    // Skip rendering if no data is provided
    if (!fieldData) return null;

    // Handle FieldData objects with text and source information
    if (typeof fieldData === 'object' && 'text' in fieldData) {
      return (
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <span className="font-semibold">{label}:</span>{" "}
            <span className="text-foreground/90">{fieldData.text}</span>
          </div>
          {fieldData.source && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground hover:text-foreground cursor-help flex-shrink-0 mt-0.5" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-1">
                  <p className="font-semibold">Source Information</p>
                  <p className="text-xs">Type: {fieldData.source.type}</p>
                  <p className="text-xs">Confidence: {Math.round(fieldData.source.confidence * 100)}%</p>
                  <p className="text-xs break-all">URL: {fieldData.source.url}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      );
    }

    // Handle array data (e.g., input/output modalities)
    if (Array.isArray(fieldData)) {
      return (
        <div>
          <span className="font-semibold">{label}:</span>{" "}
          <span className="text-foreground/90">{fieldData.join(", ") || "None specified"}</span>
        </div>
      );
    }

    // Handle object data (e.g., num_points)
    if (typeof fieldData === 'object') {
      // Special handling for total_params and training_time which have display properties
      if ('display' in fieldData && typeof fieldData.display === 'string') {
        return (
          <div>
            <span className="font-semibold">{label}:</span>{" "}
            <span className="text-foreground/90">{fieldData.display}</span>
          </div>
        );
      }
      
      // Handle key-value pairs
      return (
        <div>
          <span className="font-semibold">{label}:</span>
          <div className="ml-4 mt-1 space-y-1">
            {Object.entries(fieldData).map(([key, value]) => (
              <div key={key} className="text-foreground/90">
                <span className="text-sm">{key}: {value}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // Handle string data
    return (
      <div>
        <span className="font-semibold">{label}:</span>{" "}
        <span className="text-foreground/90">{fieldData}</span>
      </div>
    );
  };

  // Render all fields for a given section
  // Extracts field data from section_data and uses appropriate labels
  const renderSectionFields = (sectionKey: string, sectionData: any) => {
    if (!sectionData || Object.keys(sectionData).length === 0) {
      return (
        <p className="text-sm text-muted-foreground italic">
          No data available for this section
        </p>
      );
    }

    const labels = FIELD_LABELS[sectionKey] || {};
    const fields = Object.entries(sectionData)
      .filter(([key]) => !key.startsWith('_') && key !== 'bonus_star') // Exclude metadata fields
      .map(([fieldName, fieldData]) => {
        const label = labels[fieldName] || fieldName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return renderField(fieldName, fieldData, label);
      })
      .filter(Boolean); // Remove null entries

    if (fields.length === 0) {
      return (
        <p className="text-sm text-muted-foreground italic">
          No data available for this section
        </p>
      );
    }

    return <div className="space-y-3 text-sm">{fields}</div>;
  };

  return (
    <TooltipProvider>
      {/* Modal container - Height set to 85vh (85% of viewport height) */}
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        <div className="relative h-[85vh] w-[90vw] max-w-5xl overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border bg-panel p-6">
          <div className="flex-1">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-foreground">
                  {model.model_name}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Provider: {model.provider}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Globe className="h-3 w-3" />
                    {model.region}
                  </Badge>
                  <Badge variant="outline">{model.size}</Badge>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {model.release_date}
                  </Badge>
                  {model.stars > 0 && (
                    <Badge variant="secondary">
                      {"⭐".repeat(model.stars)} Bonus Features
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <div
                  className={`rounded-lg border px-4 py-2 text-center ${
                    getScoreColor(
                      (model.transparency_score?.overall ?? 0) / 100
                    ) === "success"
                      ? "border-success/40 bg-success/10"
                      : getScoreColor(
                          (model.transparency_score?.overall ?? 0) / 100
                        ) === "warning"
                      ? "border-warning/40 bg-warning/10"
                      : "border-danger/40 bg-danger/10"
                  }`}
                >
                  <div className="text-3xl font-bold text-foreground">
                    {model.transparency_score?.overall ?? 0}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Transparency Score
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onFeedback && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onFeedback()}
                    className="flex items-center gap-2"
                  >
                    <MessageSquare className="h-4 w-4" />
                    <span>Comments or Corrections</span>
                    <Info className="h-3 w-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>We welcome comments, corrections, insights and more</p>
                </TooltipContent>
              </Tooltip>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="ml-2 rounded-full"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Content - Height calculation: 85vh minus header (~120px) and footer (~100px with padding)
            Adjust the 220px value to increase/decrease content area */}
        <ScrollArea className="h-[calc(85vh-220px)]">
          <div className="p-6">
            <div className="space-y-6">
              {/* Show full documentation view if requested */}
              {showFullDocs ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <h2 className="text-xl font-semibold mb-4">Full Model Documentation</h2>
                  {SECTION_INFO.map((section) => {
                    const sectionData = model.section_data?.[section.key as keyof typeof model.section_data];
                    const hasContent = sectionData && Object.keys(sectionData).some(key => 
                      key !== '_filled' && key !== 'bonus_star' && sectionData[key as keyof typeof sectionData]
                    );
                    
                    if (!hasContent) return null;
                    
                    return (
                      <div key={section.key} className="mb-8">
                        <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                          <section.icon className="h-5 w-5 text-muted-foreground" />
                          {section.title}
                        </h3>
                        <div className="space-y-4 pl-7">
                          {Object.entries(sectionData).map(([fieldKey, fieldValue]) => {
                            // Skip metadata fields
                            if (fieldKey.startsWith('_') || fieldKey === 'bonus_star') return null;
                            
                            // Handle both FieldData objects and plain values
                            const text = typeof fieldValue === 'object' && fieldValue !== null && 'text' in fieldValue
                              ? fieldValue.text
                              : Array.isArray(fieldValue)
                              ? fieldValue.join(', ')
                              : typeof fieldValue === 'object'
                              ? JSON.stringify(fieldValue, null, 2)
                              : String(fieldValue);
                            
                            if (!text || text === '{}') return null;
                            
                            const labels = FIELD_LABELS[section.key] || {};
                            const label = labels[fieldKey] || fieldKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                            
                            return (
                              <div key={fieldKey} className="space-y-1">
                                <h4 className="font-medium">
                                  {label}
                                </h4>
                                <p className="text-muted-foreground whitespace-pre-wrap">
                                  {text}
                                </p>
                                {typeof fieldValue === 'object' && fieldValue !== null && 'source' in fieldValue && fieldValue.source && (
                                  <p className="text-xs text-muted-foreground/70">
                                    Source: {fieldValue.source.url} • 
                                    Type: {fieldValue.source.type} • 
                                    Confidence: {Math.round(fieldValue.source.confidence * 100)}%
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        <Separator className="my-6" />
                      </div>
                    );
                  })}
                  
                  {/* If no documentation available */}
                  {!SECTION_INFO.some(section => {
                    const sectionData = model.section_data?.[section.key as keyof typeof model.section_data];
                    return sectionData && Object.keys(sectionData).some(key => 
                      key !== '_filled' && key !== 'bonus_star' && sectionData[key as keyof typeof sectionData]
                    );
                  }) && (
                    <p className="text-muted-foreground italic">
                      No detailed documentation available for this model yet.
                    </p>
                  )}
                </div>
              ) : (
                <>
                  {SECTION_INFO.map((section) => {
                const score =
                  model.transparency_score?.sections[
                    section.key as keyof typeof model.transparency_score.sections
                  ] ?? 0;
                const color = getScoreColor(score);
                const Icon = section.icon;

                return (
                  <div key={section.key} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-5 w-5 text-muted-foreground" />
                        <h3 className="text-lg font-semibold text-foreground">
                          {section.title}
                        </h3>
                        {/* Display star for bonus sections */}
                        {['training', 'compute', 'energy'].includes(section.key) && 
                         model.section_data?.[section.key as keyof typeof model.section_data]?.bonus_star && (
                          <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        )}
                      </div>
                      <div
                        className={`flex items-center gap-2 rounded-lg border px-3 py-1 text-sm font-semibold ${
                          color === "success"
                            ? "border-success/40 bg-success/10 text-success"
                            : color === "warning"
                            ? "border-warning/40 bg-warning/10 text-warning"
                            : "border-danger/40 bg-danger/10 text-danger"
                        }`}
                      >
                        {Math.round(score * 100)}% complete
                      </div>
                    </div>
                    <div className="rounded-lg border border-border bg-secondary/20 p-4">
                      {/* Render section data from model.section_data if available, otherwise show no data message */}
                      {renderSectionFields(
                        section.key,
                        model.section_data?.[section.key as keyof typeof model.section_data]
                      )}
                      {/* Show partial information notice if section is not fully complete */}
                      {score > 0 && score < 1 && (
                        <p className="text-muted-foreground italic mt-3 text-xs">
                          Partial information available. Full documentation pending.
                        </p>
                      )}
                    </div>
                    {section.key !== SECTION_INFO[SECTION_INFO.length - 1].key && (
                      <Separator className="mt-4" />
                    )}
                  </div>
                );
              })}
                </>
              )}
            </div>
          </div>
        </ScrollArea>

        {/* Footer - Height controlled by padding (p-5 = 20px padding on all sides)
            Adjust p-4 (16px) for smaller footer, p-6 (24px) for larger footer
            Total footer height ~60-70px including border and content */}
        <div className="border-t border-border bg-panel p-5">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Last updated:{" "}
              {model.last_updated || new Date().toLocaleDateString()}
            </span>
            <Button 
              variant="outline" 
              size="sm" 
              className="gap-2"
              onClick={() => setShowFullDocs(!showFullDocs)}
              // Disable if no documentation available
              disabled={!model.section_data || Object.keys(model.section_data).length === 0}
            >
              <ExternalLink className="h-4 w-4" />
              {showFullDocs ? "Back to Summary" : "View Full Documentation"}
            </Button>
          </div>
        </div>
      </div>
    </div>
    </TooltipProvider>
  );
};
