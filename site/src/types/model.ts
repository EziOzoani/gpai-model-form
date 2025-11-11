/**
 * Transparency score information for the model
 * Each section has a score between 0 and 1
 */
export interface ModelTransparencyScore {
  overall: number;
  sections: {
    general: number;
    properties: number;
    distribution: number;
    use: number;
    data: number;
    training: number;
    compute: number;
    energy: number;
  };
}

/**
 * Source information for a documentation field
 */
export interface SourceInfo {
  url: string;
  type: 'official' | 'technical' | 'blog' | 'announcement' | 'documentation' | 'legal' | 'research' | 'report';
  confidence: number;
}

/**
 * Field data containing the text and source information
 */
export interface FieldData {
  text: string;
  source?: SourceInfo;
}

/**
 * Section data containing all fields and metadata
 */
export interface SectionData {
  [fieldName: string]: FieldData | boolean | undefined;
  _filled?: boolean;
  bonus_star?: boolean;  // Indicates if this section earns a bonus star
}

/**
 * Main model interface
 */
export interface Model {
  model_name: string;
  provider: string;
  region: string;
  size: string;
  release_date: string;
  transparency_score: ModelTransparencyScore;
  stars: number;
  label_x?: string;
  last_updated?: string;
  documentation?: ModelDocumentation;  // Legacy field for backward compatibility
  section_data?: {  // New field with full documentation text
    general?: SectionData;
    properties?: SectionData;
    distribution?: SectionData;
    use?: SectionData;
    data?: SectionData;
    training?: SectionData;
    compute?: SectionData;
    energy?: SectionData;
  };
}

export interface ModelDocumentation {
  general: {
    legal_name: string;
    model_name: string;
    authenticity: string;
    release_date: string;
    eu_release_date: string;
    dependencies: string;
  };
  properties: {
    architecture: string;
    design_specs: string;
    input_modalities: string[];
    output_modalities: string[];
    total_params: {
      display: string;
      range: string;
    };
  };
  distribution: {
    channels: string[];
    license_link: string;
    license_type: string;
    additional_assets: string[];
  };
  use: {
    aup_link?: string;
    intended_or_restricted: string;
    integration_types: string;
    integration_means: string;
    required_hw: string;
    required_sw: string;
  };
  training: {
    process_design: string;
    decision_rationale: string;
  };
  data: {
    types: string[];
    provenance: string[];
    obtain_select: string;
    num_points: Record<string, string>;
    scope_characteristics: string;
    curation: string;
    unsuitable_detection: string;
    bias_measures: string;
  };
  compute: {
    training_time: {
      display: string;
    };
    train_flops: {
      display: string;
    };
    train_measurement: string;
  };
  energy: {
    training_mwh: string;
    methodology: string;
    inference_flops: string;
    inference_methodology: string;
  };
}
