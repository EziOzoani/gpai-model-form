import { Model } from "@/types/model";
import { Badge } from "@/components/ui/badge";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface ModelHeatmapProps {
  models: Model[];
  onModelClick: (model: Model) => void;
  sortBy?: string | null;
  sortOrder?: 'asc' | 'desc';
  onSort?: (column: string) => void;
  selectedModels?: string[];
  onModelSelect?: (modelName: string) => void;
  selectionMode?: boolean;
}

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
  if (score >= 0.8) return "success";
  if (score >= 0.4) return "warning";
  return "danger";
};

const getScoreIcon = (score: number): string => {
  if (score >= 0.8) return "✓";
  if (score >= 0.4) return "○";
  return "×";
};

export const ModelHeatmap = ({ 
  models, 
  onModelClick, 
  sortBy = null,
  sortOrder = 'desc',
  onSort,
  selectedModels = [],
  onModelSelect,
  selectionMode = false
}: ModelHeatmapProps) => {
  if (models.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        No models match the current filters
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0">
        <thead className="sticky top-0 z-10">
          <tr>
            <th className="bg-panel border-b border-r border-border p-4 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <button
                onClick={() => onSort?.('model_name')}
                className="flex items-center gap-1 hover:text-foreground transition-colors"
              >
                Model
                {sortBy === 'model_name' ? (
                  sortOrder === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                ) : (
                  <ArrowUpDown className="h-3 w-3 opacity-50" />
                )}
              </button>
            </th>
            {SECTIONS.map((section) => (
              <th
                key={section.key}
                className="bg-panel border-b border-r border-border p-4 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground min-w-[80px]"
              >
                <button
                  onClick={() => onSort?.(section.key)}
                  className="flex items-center justify-center gap-1 hover:text-foreground transition-colors w-full"
                >
                  {section.label}
                  {sortBy === section.key ? (
                    sortOrder === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                  ) : (
                    <ArrowUpDown className="h-3 w-3 opacity-50" />
                  )}
                </button>
              </th>
            ))}
            <th className="bg-panel border-b border-border p-4 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground min-w-[100px]">
              <button
                onClick={() => onSort?.('overall')}
                className="flex items-center justify-center gap-1 hover:text-foreground transition-colors w-full"
              >
                Overall
                {sortBy === 'overall' ? (
                  sortOrder === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                ) : (
                  <ArrowUpDown className="h-3 w-3 opacity-50" />
                )}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {models.map((model, idx) => (
            <tr
              key={`${model.model_name}-${idx}`}
              className="group cursor-pointer transition-colors hover:bg-secondary/20"
              onClick={() => !selectionMode && onModelClick(model)}
            >
              <td className="border-b border-r border-border p-4">
                <div className="flex items-center gap-3">
                  {selectionMode && (
                    <input
                      type="checkbox"
                      checked={selectedModels.includes(model.model_name)}
                      onChange={(e) => {
                        e.stopPropagation();
                        onModelSelect?.(model.model_name);
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                  )}
                  <div className="flex flex-col gap-1">
                    <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                      {model.model_name}
                    </span>
                  <div className="flex gap-2">
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
                    {model.stars > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {"⭐".repeat(model.stars)}
                      </Badge>
                    )}
                    </div>
                  </div>
                </div>
              </td>
              {SECTIONS.map((section) => {
                const score =
                  model.transparency_score?.sections[
                    section.key as keyof typeof model.transparency_score.sections
                  ] ?? 0;
                const color = getScoreColor(score);
                const icon = getScoreIcon(score);
                return (
                  <td
                    key={section.key}
                    className="border-b border-r border-border p-4 text-center"
                  >
                    <div
                      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-all group-hover:scale-110 ${
                        color === "success"
                          ? "border-success/40 bg-success/10 text-success"
                          : color === "warning"
                          ? "border-warning/40 bg-warning/10 text-warning"
                          : "border-danger/40 bg-danger/10 text-danger"
                      }`}
                      title={`${section.label}: ${Math.round(score * 100)}%`}
                    >
                      <span className="text-sm font-bold">{icon}</span>
                    </div>
                  </td>
                );
              })}
              <td className="border-b border-border p-4 text-center">
                <div className="flex flex-col items-center gap-1">
                  <span className="text-lg font-bold text-foreground">
                    {model.transparency_score?.overall ?? 0}%
                  </span>
                  <div
                    className={`h-1.5 w-16 rounded-full ${
                      getScoreColor(
                        (model.transparency_score?.overall ?? 0) / 100
                      ) === "success"
                        ? "bg-success"
                        : getScoreColor(
                            (model.transparency_score?.overall ?? 0) / 100
                          ) === "warning"
                        ? "bg-warning"
                        : "bg-danger"
                    }`}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-6 flex gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded border border-success/40 bg-success/10" />
          <span>≥80% complete</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded border border-warning/40 bg-warning/10" />
          <span>40-79% complete</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded border border-danger/40 bg-danger/10" />
          <span>&lt;40% complete</span>
        </div>
      </div>
    </div>
  );
};
