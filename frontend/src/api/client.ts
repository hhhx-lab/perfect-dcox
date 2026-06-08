export type ServiceHealth = {
  status: string;
  app_name: string;
  services: {
    database_configured: boolean;
    redis_configured: boolean;
    llm_configured: boolean;
    soffice_configured: boolean;
  };
};

export type FileRecord = {
  file_id: string;
  filename: string;
  mime_type: string;
  size: number;
  sha256: string;
  storage_path: string;
  created_at: string;
};

export type JobRecord = {
  job_id: string;
  job_type: string;
  input_file_id: string;
  profile_id: string | null;
  profile_version: string | null;
  status:
    | "queued"
    | "running"
    | "completed"
    | "quality_failed"
    | "manual_review_required"
    | "export_failed"
    | "failed";
  progress: number;
  current_step: string | null;
  output_file_ids: string[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type DeliveryManifestItem = {
  input_file_id: string;
  job_id: string;
  final_docx_file_id: string | null;
  final_pdf_file_id: string | null;
  quality_report_id: string | null;
  fix_loop_ids: string[];
  download_urls: Record<string, string>;
  delivery_status: "completed" | "manual_review_required" | "failed";
};

export type BatchFormatRun = {
  batch_id: string;
  profile_id: string;
  profile_version: string;
  input_file_ids: string[];
  job_ids: string[];
  status:
    | "queued"
    | "running"
    | "partially_completed"
    | "completed"
    | "quality_failed"
    | "manual_review_required"
    | "export_failed"
    | "failed";
  delivery_manifest_id: string | null;
  manifest_download_url: string | null;
  items: DeliveryManifestItem[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ExtractionStatus = "queued" | "running" | "completed" | "failed" | "needs_review";
export type ExtractionSourceType = "document" | "natural_language";
export type RequirementSessionSourceType = "conversation" | "document";
export type RequirementSessionStatus =
  | "collecting"
  | "needs_user_answer"
  | "ready_for_confirmation"
  | "confirmed"
  | "failed";

export type ExtractionEvidence = {
  field_path: string;
  source: ExtractionSourceType;
  quote: string | null;
  note: string | null;
  confidence: number;
};

export type UncertainItem = {
  field_path: string;
  message: string;
  suggestion: string;
};

export type ProfileStatus = "draft" | "active" | "archived";
export type ProfileSource = "system" | "user" | "imported";

export type ProfileSummary = {
  profile_id: string;
  name: string;
  status: ProfileStatus;
  current_version: string;
  source: ProfileSource;
  updated_at: string;
};

export type TextFont = {
  chinese: string;
  latin: string;
  size_pt: number;
  weight: "normal" | "bold";
  color: string;
};

export type FormatProfile = {
  id: string;
  name: string;
  version: string;
  status: ProfileStatus;
  source: ProfileSource;
  description?: string | null;
  page: {
    size: "A4" | "Letter";
    orientation: "portrait" | "landscape";
    margins_cm: {
      top: number;
      bottom: number;
      left: number;
      right: number;
      gutter: number;
    };
  };
  fonts: {
    default_chinese: string;
    default_latin: string;
    default_size_pt: number;
  };
  body: {
    font: TextFont;
    first_line_indent_chars: number;
    line_spacing: number;
    alignment: "left" | "center" | "right" | "justified";
  };
  headings: Array<{
    level: number;
    font: TextFont;
    alignment: "left" | "center" | "right" | "justified";
    numbering: string;
  }>;
  abstract: {
    length_range_chars: {
      min: number;
      max: number;
    };
    title_font: TextFont;
    body_font: TextFont;
  };
  table: {
    caption: {
      position: "above" | "below";
      prefix: string;
      font: TextFont;
    };
  };
  figure: {
    caption: {
      position: "above" | "below";
      prefix: string;
      font: TextFont;
    };
  };
  equations: {
    alignment: "left" | "center" | "right" | "justified";
    numbering: "none" | "left" | "right";
    font: string;
  };
  references: {
    style: string;
    font: TextFont;
    hanging_indent_chars: number;
  };
  header_footer: {
    header_text: string | null;
    header_alignment: "left" | "center" | "right" | "justified";
    footer_page_number: boolean;
    footer_alignment: "left" | "center" | "right" | "justified";
    font: TextFont;
  };
  quality: {
    check_margins: boolean;
    check_fonts: boolean;
    check_line_spacing: boolean;
    check_headings: boolean;
    check_references: boolean;
    strictness: "lenient" | "standard" | "strict";
  };
};

export type ProfileExtractionRecord = {
  extraction_id: string;
  source_type: ExtractionSourceType;
  file_id: string | null;
  natural_language: string | null;
  status: ExtractionStatus;
  profile_draft: FormatProfile | null;
  uncertain_items: UncertainItem[];
  evidence: ExtractionEvidence[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type RequirementSessionMessage = {
  role: "user" | "agent" | "system";
  content: string;
  created_at: string;
};

export type RequirementRuleItem = {
  field_path: string;
  label: string;
  value: string;
  source: "conversation" | "document" | "system_default" | "user_confirmed";
  confidence: number;
  evidence: string[];
  needs_confirmation: boolean;
  supported: boolean;
};

export type RequirementSummary = {
  items: RequirementRuleItem[];
  missing_fields: string[];
  unsupported_or_uncertain_rules: UncertainItem[];
};

export type RequirementSession = {
  session_id: string;
  source_type: RequirementSessionSourceType;
  status: RequirementSessionStatus;
  file_id: string | null;
  natural_language: string | null;
  messages: RequirementSessionMessage[];
  missing_fields: string[];
  requirement_summary: RequirementSummary | null;
  profile_draft: FormatProfile | null;
  evidence: ExtractionEvidence[];
  uncertain_items: UncertainItem[];
  confirmed_profile_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type QualityStatus = "pass" | "fixed" | "warning" | "fail" | "unsupported";
export type QualitySeverity = "info" | "low" | "medium" | "high";
export type FixActionName =
  | "reapply_profile_formatting"
  | "apply_table_borders"
  | "apply_body_paragraph_style"
  | "apply_heading_style"
  | "mark_manual_review";

export type QualityIssue = {
  issue_id: string;
  status: QualityStatus;
  check_key: string;
  title: string;
  severity: QualitySeverity;
  description: string | null;
  profile_rule_ref: string | null;
  location: string | null;
  recommendation: string | null;
  fixable: boolean;
  details: Record<string, unknown>;
};

export type QualitySummary = {
  counts: Record<QualityStatus, number>;
  remaining_issue_count: number;
  all_compliant: boolean;
};

export type QualityReport = {
  report_id: string;
  job_id: string | null;
  profile_id: string;
  profile_version: string;
  output_file_ids: string[];
  summary: QualitySummary;
  issues: QualityIssue[];
  issues_by_status: Record<QualityStatus, QualityIssue[]>;
  created_at: string;
  updated_at: string;
};

export type IssueExplanation = {
  issue_id: string;
  reason: string;
  impact: string;
  automatic_repair_allowed: boolean;
  manual_review_guidance: string;
};

export type FixAction = {
  action: FixActionName;
  target_issue_ids: string[];
  params: Record<string, unknown>;
  requires_user_confirmation: boolean;
};

export type FixPlan = {
  fix_plan_id: string;
  report_id: string;
  actions: FixAction[];
  explanations: IssueExplanation[];
  manual_review_issue_ids: string[];
  explanation: string | null;
  created_at: string;
  updated_at: string;
  requires_user_confirmation: boolean;
};

export type FixLoopRecord = {
  fix_loop_id: string;
  original_report_id: string;
  fix_plan_id: string;
  selected_issue_ids: string[];
  selected_actions: FixAction[];
  status: "pending_confirmation" | "confirmed" | "running" | "completed" | "failed";
  new_job_id: string | null;
  new_output_file_ids: string[];
  updated_report_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const raw = await response.text();
    let message = raw;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      message = raw;
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const apiClient = {
  baseUrl: API_BASE_URL,
  getHealth: () => requestJson<ServiceHealth>("/health"),
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return requestJson<FileRecord>("/files", {
      method: "POST",
      body: formData,
    });
  },
  createJob: (fileId: string, profile?: { profile_id: string; profile_version: string }) =>
    requestJson<JobRecord>("/jobs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ input_file_id: fileId, ...profile }),
  }),
  createBatch: (payload: {
    profile_id: string;
    profile_version: string;
    input_file_ids: string[];
    output_formats: Array<"docx" | "pdf">;
    auto_quality: boolean;
    auto_fix?: boolean;
  }) =>
    requestJson<BatchFormatRun>("/batches", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  getBatch: (batchId: string) => requestJson<BatchFormatRun>(`/batches/${batchId}`),
  downloadBatchManifestUrl: (batchId: string) => `${API_BASE_URL}/batches/${batchId}/manifest`,
  getFile: (fileId: string) => requestJson<FileRecord>(`/files/${fileId}`),
  downloadFileUrl: (fileId: string) => `${API_BASE_URL}/files/${fileId}/download`,
  getJob: (jobId: string) => requestJson<JobRecord>(`/jobs/${jobId}`),
  createProfileExtraction: (payload: {
    source_type: ExtractionSourceType;
    file_id?: string | null;
    natural_language?: string | null;
  }) =>
    requestJson<ProfileExtractionRecord>("/profile-extractions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  getProfileExtraction: (extractionId: string) =>
    requestJson<ProfileExtractionRecord>(`/profile-extractions/${extractionId}`),
  createRequirementSession: (payload: {
    source_type: RequirementSessionSourceType;
    file_id?: string | null;
    natural_language?: string | null;
  }) =>
    requestJson<RequirementSession>("/requirement-sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  getRequirementSession: (sessionId: string) => requestJson<RequirementSession>(`/requirement-sessions/${sessionId}`),
  addRequirementMessage: (sessionId: string, content: string) =>
    requestJson<RequirementSession>(`/requirement-sessions/${sessionId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    }),
  confirmRequirementSession: (
    sessionId: string,
    payload: { profile_name: string; profile_version: string; profile_description?: string | null },
  ) =>
    requestJson<RequirementSession>(`/requirement-sessions/${sessionId}/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  createQualityReport: (payload: {
    profile_id: string;
    profile_version: string;
    output_file_ids: string[];
    job_id?: string | null;
  }) =>
    requestJson<QualityReport>("/quality-reports", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  getQualityReport: (reportId: string) => requestJson<QualityReport>(`/quality-reports/${reportId}`),
  downloadQualityReportUrl: (reportId: string, format: "json" | "markdown") =>
    `${API_BASE_URL}/quality-reports/${reportId}/download?format=${format}`,
  createFixPlan: (reportId: string) =>
    requestJson<FixPlan>(`/quality-reports/${reportId}/fix-plan`, {
      method: "POST",
    }),
  confirmFixLoop: (reportId: string, payload: { fix_plan_id: string; selected_issue_ids: string[] }) =>
    requestJson<FixLoopRecord>(`/quality-reports/${reportId}/fix-loops`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  executeFixLoop: (reportId: string, fixLoopId: string) =>
    requestJson<FixLoopRecord>(`/quality-reports/${reportId}/fix-loops/${fixLoopId}/execute`, {
      method: "POST",
    }),
  listProfiles: () => requestJson<ProfileSummary[]>("/profiles"),
  getProfile: (profileId: string, version: string) =>
    requestJson<FormatProfile>(`/profiles/${profileId}/versions/${version}`),
  saveProfile: (profile: FormatProfile) =>
    requestJson<FormatProfile>("/profiles", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    }),
  saveProfileVersion: (profile: FormatProfile) =>
    requestJson<FormatProfile>(`/profiles/${profile.id}/versions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    }),
  archiveProfile: (profileId: string) =>
    requestJson<ProfileSummary>(`/profiles/${profileId}/archive`, {
      method: "POST",
    }),
  importProfileYaml: (yamlText: string) =>
    requestJson<FormatProfile>("/profiles/import", {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
      },
      body: yamlText,
    }),
  exportProfileYaml: async (profileId: string, version: string) => {
    const response = await fetch(`${API_BASE_URL}/profiles/${profileId}/versions/${version}/export`);
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed with ${response.status}`);
    }
    return response.text();
  },
};
