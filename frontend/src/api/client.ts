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
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  output_file_ids: string[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
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
  getFile: (fileId: string) => requestJson<FileRecord>(`/files/${fileId}`),
  getJob: (jobId: string) => requestJson<JobRecord>(`/jobs/${jobId}`),
};
