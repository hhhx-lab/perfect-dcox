import {
  ClipboardCheck,
  FileText,
  FolderOpen,
  LayoutDashboard,
  ListChecks,
  Upload,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { apiClient, FileRecord, ServiceHealth } from "./api/client";

const workbenchAreas = [
  {
    title: "文件上传",
    description: "上传 .doc 或 .docx，生成可追踪的文件记录。",
    icon: Upload,
  },
  {
    title: "Profile",
    description: "查看、创建和版本化论文格式模板。",
    icon: FileText,
  },
  {
    title: "任务",
    description: "跟踪占位排版任务的生命周期状态。",
    icon: ListChecks,
  },
  {
    title: "质检",
    description: "后续展示 DOCX/PDF 合规检查结果。",
    icon: ClipboardCheck,
  },
  {
    title: "输出",
    description: "集中下载 DOCX、PDF 和报告产物。",
    icon: FolderOpen,
  },
];

function App() {
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileRecord | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    apiClient
      .getHealth()
      .then((payload) => {
        setHealth(payload);
        setHealthError(null);
      })
      .catch((error: Error) => {
        setHealth(null);
        setHealthError(error.message);
      });
  }, []);

  const onUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError("请先选择 .doc 或 .docx 文件。");
      return;
    }

    const lowerName = selectedFile.name.toLowerCase();
    if (!lowerName.endsWith(".doc") && !lowerName.endsWith(".docx")) {
      setUploadError("仅支持 .doc 和 .docx 文件。");
      setUploadedFile(null);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const record = await apiClient.uploadFile(selectedFile);
      setUploadedFile(record);
    } catch (error) {
      setUploadedFile(null);
      setUploadError(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="workbench">
      <aside className="sidebar" aria-label="产品区域">
        <div className="brand">
          <LayoutDashboard size={22} aria-hidden="true" />
          <span>Word Format Agent</span>
        </div>
        <nav>
          {workbenchAreas.map((area) => {
            const Icon = area.icon;
            return (
              <a href={`#${area.title}`} key={area.title}>
                <Icon size={18} aria-hidden="true" />
                <span>{area.title}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">MVP Foundation</p>
            <h1>文档格式规范化工作台</h1>
          </div>
          <div className="endpoint" title="当前后端 API 地址">
            {apiClient.baseUrl}
          </div>
        </header>

        <section className={`status-strip ${health ? "ok" : "warn"}`} aria-live="polite">
          <span>{health ? "后端可用" : "后端未连接"}</span>
          <p>
            {health
              ? `${health.app_name} 已响应，LLM ${health.services.llm_configured ? "已配置" : "未配置"}。`
              : healthError || "正在检查后端状态。"}
          </p>
        </section>

        <section className="command-panel" aria-labelledby="upload-title">
          <div>
            <p className="eyebrow">Upload</p>
            <h2 id="upload-title">上传入口</h2>
            <p>选择 Word 文件后会创建可追踪的文件记录，后续任务会基于这个 file_id 执行。</p>
          </div>
          <form className="upload-form" onSubmit={onUpload}>
            <input
              type="file"
              accept=".doc,.docx"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null);
                setUploadError(null);
              }}
            />
            <button type="submit" disabled={isUploading}>
              <Upload size={18} aria-hidden="true" />
              {isUploading ? "上传中" : "上传 Word"}
            </button>
          </form>
        </section>

        {(uploadedFile || uploadError) && (
          <section className="result-panel" aria-live="polite">
            {uploadedFile ? (
              <>
                <p className="eyebrow">File Record</p>
                <h2>{uploadedFile.filename}</h2>
                <dl>
                  <div>
                    <dt>file_id</dt>
                    <dd>{uploadedFile.file_id}</dd>
                  </div>
                  <div>
                    <dt>size</dt>
                    <dd>{uploadedFile.size} bytes</dd>
                  </div>
                  <div>
                    <dt>sha256</dt>
                    <dd>{uploadedFile.sha256}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <p className="error-text">{uploadError}</p>
            )}
          </section>
        )}

        <section className="area-grid" aria-label="工作台模块">
          {workbenchAreas.map((area) => {
            const Icon = area.icon;
            return (
              <article className="area-card" id={area.title} key={area.title}>
                <Icon size={22} aria-hidden="true" />
                <h2>{area.title}</h2>
                <p>{area.description}</p>
              </article>
            );
          })}
        </section>
      </section>
    </main>
  );
}

export default App;
