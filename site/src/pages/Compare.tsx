import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Model } from "@/types/model";
import { useModelData } from "@/hooks/useModelData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Database, ChevronDown, ChevronUp, AlertCircle, ArrowUpDown } from "lucide-react";
import { Link } from "react-router-dom";
import { ModelRadarChart } from "@/components/ModelRadarChart";
import { FeedbackButton } from "@/components/FeedbackButton";
import { FeedbackDialog } from "@/components/FeedbackDialog";

const SECTIONS = [
  { key: "general", label: "General" },
  { key: "properties", label: "Properties" },
  { key: "distribution", label: "Distribution" },
  { key: "use", label: "Use" },
  { key: "data", label: "Data" },
  { key: "training", label: "Training" },
  { key: "compute", label: "Compute" },
  { key: "energy", label: "Energy" },
];

const FIELD_LABELS: Record<string, Record<string, string>> = {
  general: {
    legal_name: "Legal Name",
    model_name: "Model Name",
    release_date: "Release Date",
    eu_release_date: "EU Market Release",
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
    intended_or_restricted: "Intended/Restricted Uses",
    required_hw: "Required Hardware",
    required_sw: "Required Software",
  },
  data: {
    types: "Data Types",
    provenance: "Data Provenance",
    num_points: "Number of Data Points",
    bias_measures: "Bias Mitigation",
  },
  training: {
    process_design: "Training Process",
    decision_rationale: "Design Rationale",
  },
  compute: {
    training_time: "Training Time",
    train_flops: "Training FLOPs",
  },
  energy: {
    training_mwh: "Training Energy (MWh)",
    methodology: "Measurement Methodology",
  },
};

const getScoreColor = (score: number): string => {
  if (score >= 0.8) return "text-success";
  if (score >= 0.4) return "text-warning";
  return "text-danger";
};

// Component to render section comparisons with difference highlighting
const SectionComparison = ({ 
  models, 
  sectionKey, 
  showOnlyDifferences 
}: { 
  models: Model[], 
  sectionKey: string,
  showOnlyDifferences: boolean
}) => {
  // Extract and normalize field data from all models
  const getFieldValue = (model: Model, fieldKey: string) => {
    try {
      const sectionData = model.section_data?.[sectionKey as keyof typeof model.section_data];
      if (!sectionData) return null;
      
      const fieldData = (sectionData as any)[fieldKey];
      if (!fieldData) return null;
      
      // Handle FieldData objects
      if (typeof fieldData === 'object' && fieldData !== null && 'text' in fieldData) {
        return fieldData.text;
      }
      
      // Handle arrays
      if (Array.isArray(fieldData)) {
        return fieldData.join(', ');
      }
      
      // Handle objects with display property
      if (typeof fieldData === 'object' && fieldData !== null && 'display' in fieldData) {
        return fieldData.display;
      }
      
      // Handle other values
      return String(fieldData || '');
    } catch (e) {
      console.error('Error getting field value:', e);
      return null;
    }
  };

  // Get all unique field keys from all models
  const allFieldKeys = new Set<string>();
  models.forEach(model => {
    try {
      const sectionData = model.section_data?.[sectionKey as keyof typeof model.section_data];
      if (sectionData && typeof sectionData === 'object') {
        Object.keys(sectionData).forEach(key => {
          if (!key.startsWith('_') && key !== 'bonus_star') {
            allFieldKeys.add(key);
          }
        });
      }
    } catch (e) {
      console.error('Error accessing section data:', e);
    }
  });

  // Analyze differences for each field
  const fieldAnalysis = Array.from(allFieldKeys).map(fieldKey => {
    const values = models.map(model => getFieldValue(model, fieldKey));
    const uniqueValues = [...new Set(values.filter(v => v !== null))];
    const hasDifferences = uniqueValues.length > 1 || values.some(v => v === null);
    
    return { fieldKey, values, uniqueValues, hasDifferences };
  });

  // Filter fields if showOnlyDifferences is enabled
  const fieldsToShow = showOnlyDifferences 
    ? fieldAnalysis.filter(f => f.hasDifferences)
    : fieldAnalysis;

  const getDifferenceClass = (value: string | null, allValues: (string | null)[]) => {
    if (value === null || value === '') return 'border-l-4 border-l-red-500 dark:border-l-red-400';
    
    const nonNullValues = allValues.filter(v => v !== null && v !== '');
    const uniqueValues = [...new Set(nonNullValues)];
    
    if (uniqueValues.length > 1) {
      return 'border-l-4 border-l-blue-500 dark:border-l-blue-400';
    }
    
    return '';
  };

  const labels = FIELD_LABELS[sectionKey] || {};

  if (fieldsToShow.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        {showOnlyDifferences ? 'No differences found in this section' : 'No data available for this section'}
      </div>
    );
  }

  return (
    <div className="p-6 bg-panel/30">
      <div className="grid gap-4">
        {fieldsToShow.map(({ fieldKey, values, hasDifferences }) => {
          const label = labels[fieldKey] || fieldKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
          
          return (
            <div key={fieldKey} className="space-y-2">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                {label}
                {hasDifferences && (
                  <div className="flex items-center gap-2">
                    <ArrowUpDown className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                    <Badge variant="outline" className="text-xs">
                      {values.filter(v => v === null).length > 0 ? 'Missing in some models' : 'Different values'}
                    </Badge>
                  </div>
                )}
              </h4>
              <div className="grid grid-cols-1 gap-2">
                {models.map((model, idx) => {
                  const value = values[idx];
                  const diffClass = hasDifferences ? getDifferenceClass(value, values) : '';
                  
                  return (
                    <div 
                      key={model.model_name} 
                      className={`p-3 rounded-lg border ${diffClass}`}
                    >
                      <div className="font-semibold text-xs mb-1 text-foreground/80">
                        {model.model_name}
                      </div>
                      <div className="text-sm">
                        {value || (
                          <span className="text-foreground/60 italic flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            No data
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      {fieldsToShow.some(f => f.hasDifferences) && (
        <div className="mt-4 text-xs text-muted-foreground space-y-1">
          <p className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 border-l-4 border-l-blue-500 dark:border-l-blue-400"></span>
            Different values across models
          </p>
          <p className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 border-l-4 border-l-red-500 dark:border-l-red-400"></span>
            Missing data
          </p>
        </div>
      )}
    </div>
  );
};

const Compare = () => {
  const [searchParams] = useSearchParams();
  const { models, loading } = useModelData();
  const [selectedModels, setSelectedModels] = useState<Model[]>([]);
  const [expandedSections, setExpandedSections] = useState<string[]>([]);
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  useEffect(() => {
    const modelNames = searchParams.get("models")?.split(",") || [];
    if (models.length > 0 && modelNames.length > 0) {
      const selected = models.filter(model => modelNames.includes(model.model_name));
      setSelectedModels(selected);
    }
  }, [models, searchParams]);

  const toggleSection = (sectionKey: string) => {
    setExpandedSections(prev => 
      prev.includes(sectionKey) 
        ? prev.filter(key => key !== sectionKey)
        : [...prev, sectionKey]
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4 animate-pulse" />
          <p className="text-muted-foreground">Loading models...</p>
        </div>
      </div>
    );
  }

  if (selectedModels.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">No models selected for comparison</p>
          <Button asChild>
            <Link to="/">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-panel">
      {/* Header */}
      <header className="border-b border-border bg-panel/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <Button variant="ghost" asChild className="mt-1">
                <Link to="/">
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
              <img 
                src="./appliedAI_horizontal_rgb_RZ.png" 
                alt="AppliedAI" 
                className="h-12 object-contain"
              />
              <div>
                <h1 className="text-3xl font-bold text-foreground">
                  Model Comparison
                </h1>
                <p className="mt-2 text-muted-foreground">
                  Comparing {selectedModels.length} models side by side
                </p>
              </div>
            </div>
            <FeedbackButton 
              onClick={() => setFeedbackOpen(true)}
              size="sm"
              showTooltip={true}
            />
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Radar Chart Comparison */}
        <div className="mb-8 rounded-2xl border border-border bg-card/50 p-6 shadow-xl backdrop-blur-sm">
          <h2 className="text-xl font-semibold mb-6">Visual Comparison</h2>
          <div className="h-[400px]">
            <ModelRadarChart models={selectedModels} />
          </div>
        </div>

        {/* Quick differences navigation */}
        <div className="mb-4">{/* Quick differences navigation */}
          {(() => {
            const sectionsWithDiffs = SECTIONS.map((section) => {
              // Count field differences for this section
              const allFieldKeys = new Set<string>();
              selectedModels.forEach(model => {
                const sectionData = model.section_data?.[section.key as keyof typeof model.section_data];
                if (sectionData && typeof sectionData === 'object') {
                  Object.keys(sectionData).forEach(key => {
                    if (!key.startsWith('_') && key !== 'bonus_star') {
                      allFieldKeys.add(key);
                    }
                  });
                }
              });

              let diffCount = 0;
              allFieldKeys.forEach(fieldKey => {
                const values = selectedModels.map(model => {
                  const sectionData = model.section_data?.[section.key as keyof typeof model.section_data];
                  const fieldData = sectionData?.[fieldKey as keyof typeof sectionData];
                  if (!fieldData) return null;
                  if (typeof fieldData === 'object' && 'text' in fieldData) return fieldData.text;
                  if (Array.isArray(fieldData)) return fieldData.join(', ');
                  if (typeof fieldData === 'object' && 'display' in fieldData) return fieldData.display;
                  return String(fieldData || '');
                });
                const uniqueValues = [...new Set(values.filter(v => v !== null))];
                if (uniqueValues.length > 1 || values.some(v => v === null)) {
                  diffCount++;
                }
              });

              return { section, diffCount };
            }).filter(item => item.diffCount > 0);

            if (sectionsWithDiffs.length > 0) {
              return (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-muted-foreground">Quick jump to differences:</span>
                  {sectionsWithDiffs.map(({ section, diffCount }) => (
                    <Button
                      key={section.key}
                      variant="outline"
                      size="sm"
                      className="h-7 px-3 text-xs"
                      onClick={() => {
                        // Expand the section if not already expanded
                        if (!expandedSections.includes(section.key)) {
                          setExpandedSections([...expandedSections, section.key]);
                        }
                        // Scroll to the section
                        const element = document.querySelector(`[data-section="${section.key}"]`);
                        if (element) {
                          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                      }}
                    >
                      {section.label}: {diffCount} {diffCount === 1 ? 'diff' : 'diffs'}
                    </Button>
                  ))}
                </div>
              );
            }
            return null;
          })()}
        </div>

        {/* Table Comparison */}
        <div className="rounded-2xl border border-border bg-card/50 p-6 shadow-xl backdrop-blur-sm">
          <h2 className="text-xl font-semibold mb-6">Detailed Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-separate border-spacing-0">
              <thead>
                <tr>
                  <th className="bg-panel border-b border-r border-border p-4 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground sticky left-0 z-10">
                    Section
                  </th>
                  {selectedModels.map((model) => (
                    <th
                      key={model.model_name}
                      className="bg-panel border-b border-r border-border p-4 text-center"
                    >
                      <div className="space-y-2">
                        <div className="font-semibold text-foreground">
                          {model.model_name}
                        </div>
                        <div className="flex gap-2 justify-center">
                          {model.region === "Non-EU UK" ? (
                            <>
                              <Badge variant="outline" className="text-xs">
                                Non-EU
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                UK
                              </Badge>
                            </>
                          ) : (
                            <Badge variant="outline" className="text-xs">
                              {model.region}
                            </Badge>
                          )}
                          <Badge variant="outline" className="text-xs">
                            {model.size}
                          </Badge>
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SECTIONS.map((section) => {
                  const isExpanded = expandedSections.includes(section.key);
                  
                  return (
                    <React.Fragment key={section.key}>
                      <tr 
                        className="cursor-pointer hover:bg-accent/50 transition-colors"
                        onClick={() => toggleSection(section.key)}
                        data-section={section.key}
                      >
                        <td className="border-b border-r border-border p-4 font-medium sticky left-0 bg-card z-10">
                          <div className="flex items-center gap-2">
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            {section.label}
                          </div>
                        </td>
                        {selectedModels.map((model) => {
                          const score =
                            model.transparency_score?.sections[
                              section.key as keyof typeof model.transparency_score.sections
                            ] ?? 0;
                          return (
                            <td
                              key={`${model.model_name}-${section.key}`}
                              className="border-b border-r border-border p-4 text-center"
                            >
                              <span className={`text-2xl font-bold ${getScoreColor(score)}`}>
                                {Math.round(score * 100)}%
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={selectedModels.length + 1} className="border-b border-border p-0">
                            <SectionComparison 
                              models={selectedModels} 
                              sectionKey={section.key}
                              showOnlyDifferences={false}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
                <tr>
                  <td className="border-b border-r border-border p-4 font-bold sticky left-0 bg-card z-10">
                    Overall Score
                  </td>
                  {selectedModels.map((model) => (
                    <td
                      key={`${model.model_name}-overall`}
                      className="border-b border-r border-border p-4 text-center"
                    >
                      <span className={`text-3xl font-bold ${getScoreColor((model.transparency_score?.overall ?? 0) / 100)}`}>
                        {model.transparency_score?.overall ?? 0}%
                      </span>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
      
      <FeedbackDialog
        isOpen={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        context={{
          type: 'model',
          modelName: `Comparison: ${selectedModels.map(m => m.model_name).join(' vs ')}`,
          modelId: selectedModels.map(m => m.model_name).join(','),
        }}
      />
    </div>
  );
};

export default Compare;