import {
  ClipboardCheck,
  FileText,
  FolderOpen,
  LayoutDashboard,
  ListChecks,
  RefreshCcw,
  Upload,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { apiClient, FileRecord, FormatProfile, JobRecord, ProfileSummary, ServiceHealth } from "./api/client";

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
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileKey, setSelectedProfileKey] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<FormatProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileRecord | null>(null);
  const [job, setJob] = useState<JobRecord | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingJob, setIsCreatingJob] = useState(false);
  const [isRefreshingJob, setIsRefreshingJob] = useState(false);

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

  const loadProfiles = async () => {
    setIsLoadingProfiles(true);
    try {
      const summaries = await apiClient.listProfiles();
      setProfiles(summaries);
      setProfileError(null);
      if (!selectedProfileKey && summaries.length > 0) {
        setSelectedProfileKey(`${summaries[0].profile_id}@${summaries[0].current_version}`);
      }
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile 加载失败。");
    } finally {
      setIsLoadingProfiles(false);
    }
  };

  useEffect(() => {
    void loadProfiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProfileKey) {
      setSelectedProfile(null);
      return;
    }

    const [profileId, version] = selectedProfileKey.split("@");
    apiClient
      .getProfile(profileId, version)
      .then((profile) => {
        setSelectedProfile(profile);
        setProfileError(null);
      })
      .catch((error: Error) => {
        setSelectedProfile(null);
        setProfileError(error.message);
      });
  }, [selectedProfileKey]);

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
      setJob(null);
      setJobError(null);
    } catch (error) {
      setUploadedFile(null);
      setUploadError(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setIsUploading(false);
    }
  };

  const createJob = async () => {
    if (!uploadedFile) {
      setJobError("请先上传 Word 文件。");
      return;
    }
    setIsCreatingJob(true);
    setJobError(null);
    try {
      const created = await apiClient.createJob(uploadedFile.file_id);
      setJob(created);
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "创建任务失败。");
    } finally {
      setIsCreatingJob(false);
    }
  };

  const refreshJob = async () => {
    if (!job) {
      return;
    }
    setIsRefreshingJob(true);
    setJobError(null);
    try {
      const latest = await apiClient.getJob(job.job_id);
      setJob(latest);
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "刷新任务失败。");
    } finally {
      setIsRefreshingJob(false);
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

        <section className="profile-panel" id="Profile" aria-labelledby="profile-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Profile</p>
              <h2 id="profile-title">格式 Profile 管理</h2>
            </div>
            <button type="button" className="ghost-button" onClick={loadProfiles} disabled={isLoadingProfiles}>
              <RefreshCcw size={16} aria-hidden="true" />
              {isLoadingProfiles ? "加载中" : "刷新"}
            </button>
          </div>
          {profileError && <p className="error-text profile-error">{profileError}</p>}
          <div className="profile-layout">
            <div className="profile-list" aria-label="Profile 列表">
              {profiles.length === 0 && !profileError ? (
                <p className="muted">暂无可用 profile。</p>
              ) : (
                profiles.map((profile) => {
                  const key = `${profile.profile_id}@${profile.current_version}`;
                  return (
                    <button
                      type="button"
                      className={`profile-row ${selectedProfileKey === key ? "selected" : ""}`}
                      key={key}
                      onClick={() => setSelectedProfileKey(key)}
                    >
                      <span>{profile.name}</span>
                      <small>
                        {profile.status} · v{profile.current_version} · {profile.source}
                      </small>
                    </button>
                  );
                })
              )}
            </div>
            <div className="profile-detail" aria-live="polite">
              {selectedProfile ? (
                <>
                  <div className="detail-title">
                    <div>
                      <p className="eyebrow">{selectedProfile.id}</p>
                      <h3>{selectedProfile.name}</h3>
                    </div>
                    <span className={`status-badge ${selectedProfile.status}`}>{selectedProfile.status}</span>
                  </div>
                  <dl className="profile-meta">
                    <div>
                      <dt>当前版本</dt>
                      <dd>{selectedProfile.version}</dd>
                    </div>
                    <div>
                      <dt>来源</dt>
                      <dd>{selectedProfile.source}</dd>
                    </div>
                    <div>
                      <dt>页面</dt>
                      <dd>
                        {selectedProfile.page.size} · {selectedProfile.page.orientation}
                      </dd>
                    </div>
                    <div>
                      <dt>正文</dt>
                      <dd>
                        {selectedProfile.body.font.chinese} / {selectedProfile.body.font.latin} ·{" "}
                        {selectedProfile.body.font.size_pt}pt · {selectedProfile.body.line_spacing}x
                      </dd>
                    </div>
                    <div>
                      <dt>页边距</dt>
                      <dd>
                        上 {selectedProfile.page.margins_cm.top} / 下 {selectedProfile.page.margins_cm.bottom} / 左{" "}
                        {selectedProfile.page.margins_cm.left} / 右 {selectedProfile.page.margins_cm.right} cm
                      </dd>
                    </div>
                    <div>
                      <dt>更新时间</dt>
                      <dd>
                        {profiles.find((item) => `${item.profile_id}@${item.current_version}` === selectedProfileKey)
                          ?.updated_at || "N/A"}
                      </dd>
                    </div>
                  </dl>
                </>
              ) : (
                <p className="muted">选择一个 profile 查看详情。</p>
              )}
            </div>
          </div>
        </section>

        <section className="job-panel" id="任务" aria-labelledby="job-title">
          <div>
            <p className="eyebrow">Task</p>
            <h2 id="job-title">占位排版任务</h2>
            <p>创建任务后会进入 queued 状态，等待后端 placeholder worker 处理。</p>
          </div>
          <div className="job-actions">
            <button type="button" onClick={createJob} disabled={!uploadedFile || isCreatingJob}>
              <ListChecks size={18} aria-hidden="true" />
              {isCreatingJob ? "创建中" : "创建任务"}
            </button>
            <button type="button" onClick={refreshJob} disabled={!job || isRefreshingJob}>
              <RefreshCcw size={18} aria-hidden="true" />
              {isRefreshingJob ? "刷新中" : "刷新状态"}
            </button>
          </div>
          {(job || jobError) && (
            <div className="job-status" aria-live="polite">
              {job ? (
                <>
                  <span className={`status-badge ${job.status}`}>{job.status}</span>
                  <dl>
                    <div>
                      <dt>job_id</dt>
                      <dd>{job.job_id}</dd>
                    </div>
                    <div>
                      <dt>progress</dt>
                      <dd>{job.progress}%</dd>
                    </div>
                    <div>
                      <dt>current_step</dt>
                      <dd>{job.current_step || "N/A"}</dd>
                    </div>
                    {job.error_message && (
                      <div>
                        <dt>error</dt>
                        <dd>{job.error_message}</dd>
                      </div>
                    )}
                  </dl>
                </>
              ) : (
                <p className="error-text">{jobError}</p>
              )}
            </div>
          )}
        </section>

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
