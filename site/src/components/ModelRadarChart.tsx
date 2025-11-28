import { Model } from "@/types/model";
import { useEffect, useRef } from "react";

interface ModelRadarChartProps {
  models: Model[];
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

const COLORS = [
  "rgba(59, 130, 246, 0.8)", // blue
  "rgba(239, 68, 68, 0.8)",  // red
  "rgba(34, 197, 94, 0.8)",  // green
  "rgba(251, 146, 60, 0.8)", // orange
];

export const ModelRadarChart = ({ models }: ModelRadarChartProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 60;
    const angleStep = (2 * Math.PI) / SECTIONS.length;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = "rgba(148, 163, 184, 0.2)";
    ctx.lineWidth = 1;

    // Draw concentric circles
    for (let i = 1; i <= 5; i++) {
      ctx.beginPath();
      const r = (radius * i) / 5;
      for (let j = 0; j < SECTIONS.length; j++) {
        const angle = j * angleStep - Math.PI / 2;
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);
        if (j === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();
      ctx.stroke();
    }

    // Draw radial lines
    for (let i = 0; i < SECTIONS.length; i++) {
      const angle = i * angleStep - Math.PI / 2;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(
        centerX + radius * Math.cos(angle),
        centerY + radius * Math.sin(angle)
      );
      ctx.stroke();
    }

    // Draw labels
    ctx.fillStyle = "rgba(148, 163, 184, 1)";
    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (let i = 0; i < SECTIONS.length; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const labelX = centerX + (radius + 30) * Math.cos(angle);
      const labelY = centerY + (radius + 30) * Math.sin(angle);
      ctx.fillText(SECTIONS[i].label, labelX, labelY);
    }

    // Draw data for each model
    models.forEach((model, modelIndex) => {
      const color = COLORS[modelIndex % COLORS.length];
      
      // Draw filled area
      ctx.fillStyle = color.replace("0.8", "0.2");
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;

      ctx.beginPath();
      for (let i = 0; i < SECTIONS.length; i++) {
        const section = SECTIONS[i];
        const score =
          model.transparency_score?.sections[
            section.key as keyof typeof model.transparency_score.sections
          ] ?? 0;
        const angle = i * angleStep - Math.PI / 2;
        const r = radius * score;
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Draw points
      ctx.fillStyle = color;
      for (let i = 0; i < SECTIONS.length; i++) {
        const section = SECTIONS[i];
        const score =
          model.transparency_score?.sections[
            section.key as keyof typeof model.transparency_score.sections
          ] ?? 0;
        const angle = i * angleStep - Math.PI / 2;
        const r = radius * score;
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    });

    // Draw legend
    ctx.font = "14px Inter, sans-serif";
    let legendY = 20;
    models.forEach((model, index) => {
      const color = COLORS[index % COLORS.length];
      ctx.fillStyle = color;
      ctx.fillRect(20, legendY - 6, 12, 12);
      ctx.fillStyle = "rgba(148, 163, 184, 1)";
      ctx.textAlign = "left";
      ctx.fillText(model.model_name, 40, legendY);
      legendY += 25;
    });

    // Draw scale labels
    ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    for (let i = 1; i <= 5; i++) {
      ctx.fillText(
        `${i * 20}%`,
        centerX,
        centerY - (radius * i) / 5 - 5
      );
    }
  }, [models]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ minHeight: "400px" }}
    />
  );
};