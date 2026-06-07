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
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  output_file_ids: string[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
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
  quality: {
    check_margins: boolean;
    check_fonts: boolean;
    check_line_spacing: boolean;
    check_headings: boolean;
    check_references: boolean;
    strictness: "lenient" | "standard" | "strict";
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
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
  getFile: (fileId: string) => requestJson<FileRecord>(`/files/${fileId}`),
  getJob: (jobId: string) => requestJson<JobRecord>(`/jobs/${jobId}`),
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
