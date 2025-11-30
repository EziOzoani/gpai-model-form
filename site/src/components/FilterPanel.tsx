import React from 'react';
import { Filter, Calendar, Shield } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";

interface FilterPanelProps {
  regionFilter: string;
  setRegionFilter: (value: string) => void;
  sizeFilter: string;
  setSizeFilter: (value: string) => void;
  minTransparency: number;
  setMinTransparency: (value: number) => void;
  codeOfPracticeFilter: string;
  setCodeOfPracticeFilter: (value: string) => void;
  dateCutoff: string;
  setDateCutoff: (value: string) => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  regionFilter,
  setRegionFilter,
  sizeFilter,
  setSizeFilter,
  minTransparency,
  setMinTransparency,
  codeOfPracticeFilter,
  setCodeOfPracticeFilter,
  dateCutoff,
  setDateCutoff,
}) => {
  return (
    <div className="border-b border-border bg-card/30 backdrop-blur-sm">
      <div className="container mx-auto px-6 py-6">
        <div className="flex items-center gap-3 mb-4">
          <Filter className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Filters
          </h2>
        </div>
        
        {/* First row of filters */}
        <div className="grid gap-6 md:grid-cols-4 mb-4">
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
                <SelectItem value="Non-EU UK">Non-EU UK</SelectItem>
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
                <SelectItem value="big">Big ({">"}10B parameters)</SelectItem>
                <SelectItem value="small">Small (≤10B parameters)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="cop-filter" className="text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Code of Practice
              </div>
            </Label>
            <Select value={codeOfPracticeFilter} onValueChange={setCodeOfPracticeFilter}>
              <SelectTrigger id="cop-filter" className="bg-panel">
                <SelectValue placeholder="All providers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Providers</SelectItem>
                <SelectItem value="signatories">Signatories Only</SelectItem>
                <SelectItem value="non_signatories">Non-Signatories</SelectItem>
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
        
        {/* Second row - Date cutoff toggle */}
        <div className="flex items-center gap-6 pt-4 border-t border-border">
          <div className="flex items-center gap-3">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <Label className="text-sm text-muted-foreground">
              Code of Practice Cutoff Date:
            </Label>
          </div>
          
          <div className="flex items-center gap-4">
            <Label 
              htmlFor="date-toggle" 
              className={`text-sm ${dateCutoff === '2024-05-31' ? 'text-foreground font-semibold' : 'text-muted-foreground'}`}
            >
              January 2024
            </Label>
            <Switch
              id="date-toggle"
              checked={dateCutoff === '2024-09-30'}
              onCheckedChange={(checked) => 
                setDateCutoff(checked ? '2024-09-30' : '2024-05-31')
              }
            />
            <Label 
              htmlFor="date-toggle" 
              className={`text-sm ${dateCutoff === '2024-09-30' ? 'text-foreground font-semibold' : 'text-muted-foreground'}`}
            >
              September 2024
            </Label>
          </div>
          
          <div className="text-sm text-muted-foreground ml-auto">
            {dateCutoff === '2024-05-31' ? (
              <span>Showing original signatories (May 2024)</span>
            ) : (
              <span>Including September 2024 signatories</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};