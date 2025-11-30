import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Model } from "@/types/model";
import { useModelData } from "@/hooks/useModelData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Database } from "lucide-react";
import { Link } from "react-router-dom";
import { ModelRadarChart } from "@/components/ModelRadarChart";

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

const getScoreColor = (score: number): string => {
  if (score >= 0.8) return "text-success";
  if (score >= 0.4) return "text-warning";
  return "text-danger";
};

const Compare = () => {
  const [searchParams] = useSearchParams();
  const { models, loading } = useModelData();
  const [selectedModels, setSelectedModels] = useState<Model[]>([]);

  useEffect(() => {
    const modelNames = searchParams.get("models")?.split(",") || [];
    if (models.length > 0 && modelNames.length > 0) {
      const selected = models.filter(model => modelNames.includes(model.model_name));
      setSelectedModels(selected);
    }
  }, [models, searchParams]);

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
          <div className="flex items-center gap-4">
            <Button variant="ghost" asChild>
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
                {SECTIONS.map((section) => (
                  <tr key={section.key}>
                    <td className="border-b border-r border-border p-4 font-medium sticky left-0 bg-card z-10">
                      {section.label}
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
                ))}
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

        {/* Key Differences Section */}
        <div className="mt-8 rounded-2xl border border-border bg-card/50 p-6 shadow-xl backdrop-blur-sm">
          <h2 className="text-xl font-semibold mb-6">Key Differences</h2>
          <div className="grid gap-4">
            {SECTIONS.map((section) => {
              const scores = selectedModels.map(
                (model) =>
                  model.transparency_score?.sections[
                    section.key as keyof typeof model.transparency_score.sections
                  ] ?? 0
              );
              const maxScore = Math.max(...scores);
              const minScore = Math.min(...scores);
              const difference = maxScore - minScore;

              if (difference > 0.2) {
                return (
                  <div key={section.key} className="flex items-center gap-4">
                    <span className="font-medium w-32">{section.label}:</span>
                    <span className="text-sm text-muted-foreground">
                      Varies by {Math.round(difference * 100)}% between models
                    </span>
                  </div>
                );
              }
              return null;
            }).filter(Boolean)}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Compare;