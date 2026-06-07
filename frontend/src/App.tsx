import {
  ClipboardCheck,
  FileText,
  FolderOpen,
  LayoutDashboard,
  ListChecks,
  Plus,
  RefreshCcw,
  Save,
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
    description: "跟踪文档排版任务的生命周期和输出状态。",
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

function profileKey(profileId: string, version: string) {
  return `${profileId}@${version}`;
}

function cloneProfile(profile: FormatProfile): FormatProfile {
  return JSON.parse(JSON.stringify(profile)) as FormatProfile;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} bytes`;
  }
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

function outputKind(file: FileRecord): string {
  const lowerName = file.filename.toLowerCase();
  if (
    lowerName.endsWith(".docx") ||
    file.mime_type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ) {
    return "DOCX";
  }
  if (lowerName.endsWith(".pdf") || file.mime_type === "application/pdf") {
    return "PDF";
  }
  return "FILE";
}

function App() {
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileKey, setSelectedProfileKey] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<FormatProfile | null>(null);
  const [profileDraft, setProfileDraft] = useState<FormatProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaveError, setProfileSaveError] = useState<string | null>(null);
  const [profileSaveMessage, setProfileSaveMessage] = useState<string | null>(null);
  const [yamlText, setYamlText] = useState("");
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [yamlMessage, setYamlMessage] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isImportingYaml, setIsImportingYaml] = useState(false);
  const [isExportingYaml, setIsExportingYaml] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileRecord | null>(null);
  const [job, setJob] = useState<JobRecord | null>(null);
  const [outputFiles, setOutputFiles] = useState<FileRecord[]>([]);
  const [outputError, setOutputError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingJob, setIsCreatingJob] = useState(false);
  const [isRefreshingJob, setIsRefreshingJob] = useState(false);
  const [isLoadingOutputs, setIsLoadingOutputs] = useState(false);
  const outputFileIdsKey = job?.output_file_ids.join("|") ?? "";

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

  const loadProfiles = async (nextSelectedKey?: string) => {
    setIsLoadingProfiles(true);
    try {
      const summaries = await apiClient.listProfiles();
      setProfiles(summaries);
      setProfileError(null);
      if (nextSelectedKey) {
        setSelectedProfileKey(nextSelectedKey);
      } else if (!selectedProfileKey && summaries.length > 0) {
        setSelectedProfileKey(profileKey(summaries[0].profile_id, summaries[0].current_version));
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
        setProfileDraft(cloneProfile(profile));
        setProfileError(null);
        setProfileSaveError(null);
        setProfileSaveMessage(null);
        setYamlError(null);
      })
      .catch((error: Error) => {
        setSelectedProfile(null);
        setProfileDraft(null);
        setProfileError(error.message);
      });
  }, [selectedProfileKey]);

  useEffect(() => {
    const outputIds = job?.output_file_ids ?? [];
    if (outputIds.length === 0) {
      setOutputFiles([]);
      setOutputError(null);
      setIsLoadingOutputs(false);
      return;
    }

    let cancelled = false;
    setIsLoadingOutputs(true);
    setOutputError(null);
    void Promise.allSettled(outputIds.map((fileId) => apiClient.getFile(fileId))).then((results) => {
      if (cancelled) {
        return;
      }
      const loadedFiles: FileRecord[] = [];
      const failedIds: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          loadedFiles.push(result.value);
        } else {
          failedIds.push(outputIds[index]);
        }
      });
      setOutputFiles(loadedFiles);
      setOutputError(failedIds.length > 0 ? `部分输出元数据加载失败：${failedIds.join(", ")}` : null);
      setIsLoadingOutputs(false);
    });

    return () => {
      cancelled = true;
    };
  }, [outputFileIdsKey, job]);

  const updateProfileDraft = (mutator: (draft: FormatProfile) => void) => {
    setProfileDraft((current) => {
      if (!current) {
        return current;
      }
      const next = cloneProfile(current);
      mutator(next);
      return next;
    });
    setProfileSaveError(null);
    setProfileSaveMessage(null);
  };

  const createDraftFromSelected = () => {
    const source = selectedProfile ?? profileDraft;
    if (!source) {
      setProfileSaveError("请先选择一个 profile。");
      return;
    }
    const next = cloneProfile(source);
    next.id = `draft_${Date.now()}`;
    next.name = `${source.name} Draft`;
    next.version = "0.1.0";
    next.status = "draft";
    next.source = "user";
    setSelectedProfileKey(null);
    setSelectedProfile(null);
    setProfileDraft(next);
    setProfileSaveError(null);
    setProfileSaveMessage("已创建本地 draft，保存后会写入后端。");
  };

  const saveProfileDraft = async () => {
    if (!profileDraft) {
      setProfileSaveError("没有可保存的 profile draft。");
      return;
    }
    setIsSavingProfile(true);
    setProfileSaveError(null);
    setProfileSaveMessage(null);
    try {
      const exists = profiles.some((profile) => profile.profile_id === profileDraft.id);
      const saved = exists ? await apiClient.saveProfileVersion(profileDraft) : await apiClient.saveProfile(profileDraft);
      const key = profileKey(saved.id, saved.version);
      setSelectedProfile(saved);
      setProfileDraft(cloneProfile(saved));
      setProfileSaveMessage(`已保存 ${saved.name} v${saved.version}`);
      await loadProfiles(key);
    } catch (error) {
      setProfileSaveError(error instanceof Error ? error.message : "保存 profile 失败。");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const importYaml = async () => {
    if (!yamlText.trim()) {
      setYamlError("请先粘贴 profile YAML。");
      return;
    }
    setIsImportingYaml(true);
    setYamlError(null);
    setYamlMessage(null);
    try {
      const imported = await apiClient.importProfileYaml(yamlText);
      setProfileDraft(cloneProfile(imported));
      setSelectedProfile(imported);
      setYamlMessage(`已导入 ${imported.name} v${imported.version}`);
      await loadProfiles(profileKey(imported.id, imported.version));
    } catch (error) {
      setYamlError(error instanceof Error ? error.message : "导入 YAML 失败。");
    } finally {
      setIsImportingYaml(false);
    }
  };

  const exportYaml = async () => {
    const source = profileDraft ?? selectedProfile;
    if (!source) {
      setYamlError("请先选择一个 profile。");
      return;
    }
    setIsExportingYaml(true);
    setYamlError(null);
    setYamlMessage(null);
    try {
      const exported = await apiClient.exportProfileYaml(source.id, source.version);
      setYamlText(exported);
      setYamlMessage(`已导出 ${source.name} v${source.version}`);
    } catch (error) {
      setYamlError(error instanceof Error ? error.message : "导出 YAML 失败。");
    } finally {
      setIsExportingYaml(false);
    }
  };

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
      setOutputFiles([]);
      setOutputError(null);
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
      const profileRef =
        selectedProfile && selectedProfileKey
          ? {
              profile_id: selectedProfile.id,
              profile_version: selectedProfile.version,
            }
          : undefined;
      const created = await apiClient.createJob(uploadedFile.file_id, profileRef);
      setJob(created);
      setOutputFiles([]);
      setOutputError(null);
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
            <button type="button" className="ghost-button" onClick={() => void loadProfiles()} disabled={isLoadingProfiles}>
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
                  const key = profileKey(profile.profile_id, profile.current_version);
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
                        {profiles.find((item) => profileKey(item.profile_id, item.current_version) === selectedProfileKey)
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
          {profileDraft && (
            <form className="profile-editor" onSubmit={(event) => event.preventDefault()}>
              <div className="editor-header">
                <div>
                  <p className="eyebrow">Structured Editor</p>
                  <h3>常用字段编辑</h3>
                </div>
                <div className="editor-actions">
                  <button type="button" className="ghost-button" onClick={createDraftFromSelected}>
                    <Plus size={16} aria-hidden="true" />
                    新建 Draft
                  </button>
                  <button type="button" onClick={saveProfileDraft} disabled={isSavingProfile}>
                    <Save size={16} aria-hidden="true" />
                    {isSavingProfile ? "保存中" : "保存版本"}
                  </button>
                </div>
              </div>
              {(profileSaveError || profileSaveMessage) && (
                <p className={profileSaveError ? "error-text profile-error" : "success-text"} aria-live="polite">
                  {profileSaveError || profileSaveMessage}
                </p>
              )}
              <div className="editor-grid">
                <label>
                  <span>Profile ID</span>
                  <input
                    value={profileDraft.id}
                    onChange={(event) => updateProfileDraft((draft) => void (draft.id = event.target.value))}
                  />
                </label>
                <label>
                  <span>名称</span>
                  <input
                    value={profileDraft.name}
                    onChange={(event) => updateProfileDraft((draft) => void (draft.name = event.target.value))}
                  />
                </label>
                <label>
                  <span>版本</span>
                  <input
                    value={profileDraft.version}
                    onChange={(event) => updateProfileDraft((draft) => void (draft.version = event.target.value))}
                  />
                </label>
                <label>
                  <span>状态</span>
                  <select
                    value={profileDraft.status}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.status = event.target.value as FormatProfile["status"]))
                    }
                  >
                    <option value="draft">draft</option>
                    <option value="active">active</option>
                    <option value="archived">archived</option>
                  </select>
                </label>
                <label>
                  <span>上边距 cm</span>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.page.margins_cm.top}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.page.margins_cm.top = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>下边距 cm</span>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.page.margins_cm.bottom}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.page.margins_cm.bottom = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>左边距 cm</span>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.page.margins_cm.left}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.page.margins_cm.left = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>右边距 cm</span>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.page.margins_cm.right}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.page.margins_cm.right = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>中文正文字体</span>
                  <input
                    value={profileDraft.body.font.chinese}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.font.chinese = event.target.value))
                    }
                  />
                </label>
                <label>
                  <span>英文字体</span>
                  <input
                    value={profileDraft.body.font.latin}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.font.latin = event.target.value))
                    }
                  />
                </label>
                <label>
                  <span>正文字号 pt</span>
                  <input
                    type="number"
                    step="0.5"
                    value={profileDraft.body.font.size_pt}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.font.size_pt = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>行距</span>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.body.line_spacing}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.line_spacing = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>一级标题字体</span>
                  <input
                    value={profileDraft.headings[0]?.font.chinese ?? ""}
                    onChange={(event) =>
                      updateProfileDraft((draft) => {
                        if (draft.headings[0]) draft.headings[0].font.chinese = event.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  <span>表题位置</span>
                  <select
                    value={profileDraft.table.caption.position}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) =>
                          void (draft.table.caption.position = event.target.value as FormatProfile["table"]["caption"]["position"]),
                      )
                    }
                  >
                    <option value="above">above</option>
                    <option value="below">below</option>
                  </select>
                </label>
                <label>
                  <span>图题位置</span>
                  <select
                    value={profileDraft.figure.caption.position}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) =>
                          void (draft.figure.caption.position = event.target.value as FormatProfile["figure"]["caption"]["position"]),
                      )
                    }
                  >
                    <option value="below">below</option>
                    <option value="above">above</option>
                  </select>
                </label>
                <label>
                  <span>检查强度</span>
                  <select
                    value={profileDraft.quality.strictness}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) =>
                          void (draft.quality.strictness = event.target.value as FormatProfile["quality"]["strictness"]),
                      )
                    }
                  >
                    <option value="lenient">lenient</option>
                    <option value="standard">standard</option>
                    <option value="strict">strict</option>
                  </select>
                </label>
              </div>
              <div className="quality-toggles">
                {[
                  ["check_margins", "页边距"],
                  ["check_fonts", "字体"],
                  ["check_line_spacing", "行距"],
                  ["check_headings", "标题"],
                  ["check_references", "参考文献"],
                ].map(([key, label]) => (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={Boolean(profileDraft.quality[key as keyof FormatProfile["quality"]])}
                      onChange={(event) =>
                        updateProfileDraft(
                          (draft) =>
                            void ((draft.quality[key as keyof FormatProfile["quality"]] as boolean) = event.target.checked),
                        )
                      }
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </form>
          )}
          <section className="yaml-panel" aria-labelledby="yaml-title">
            <div className="editor-header">
              <div>
                <p className="eyebrow">YAML</p>
                <h3 id="yaml-title">高级导入 / 导出</h3>
              </div>
              <div className="editor-actions">
                <button type="button" className="ghost-button" onClick={exportYaml} disabled={isExportingYaml}>
                  {isExportingYaml ? "导出中" : "导出 YAML"}
                </button>
                <button type="button" onClick={importYaml} disabled={isImportingYaml}>
                  {isImportingYaml ? "导入中" : "导入 YAML"}
                </button>
              </div>
            </div>
            {(yamlError || yamlMessage) && (
              <p className={yamlError ? "error-text profile-error" : "success-text"} aria-live="polite">
                {yamlError || yamlMessage}
              </p>
            )}
            <textarea
              value={yamlText}
              onChange={(event) => {
                setYamlText(event.target.value);
                setYamlError(null);
                setYamlMessage(null);
              }}
              spellCheck={false}
              aria-label="Profile YAML"
            />
          </section>
        </section>

        <section className="job-panel" id="任务" aria-labelledby="job-title">
          <div>
            <p className="eyebrow">Task</p>
            <h2 id="job-title">文档排版任务</h2>
            <p>创建任务后会进入 queued 状态，等待后端 worker 按所选 profile 生成规范化 DOCX 输出。</p>
          </div>
          <div className="task-context-grid">
            <div className="task-reference">
              <span>Input File</span>
              <strong>{uploadedFile ? uploadedFile.filename : "No uploaded file"}</strong>
              {uploadedFile && <small>{uploadedFile.file_id}</small>}
            </div>
            <div className="task-reference">
              <span>Profile Reference</span>
              <strong>{selectedProfile ? `${selectedProfile.id} v${selectedProfile.version}` : "Unprofiled"}</strong>
              {selectedProfile && <small>{selectedProfile.name}</small>}
            </div>
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
                    <div>
                      <dt>profile</dt>
                      <dd>
                        {job.profile_id && job.profile_version
                          ? `${job.profile_id} v${job.profile_version}`
                          : "Unprofiled"}
                      </dd>
                    </div>
                  </dl>
                  {job.error_message && (
                    <section className="formatting-error" aria-label="排版失败诊断">
                      <strong>排版失败诊断</strong>
                      <p>{job.error_message}</p>
                    </section>
                  )}
                  {job.output_file_ids.length > 0 && (
                    <section className="output-section" aria-label="任务输出文件">
                      <div className="output-heading">
                        <FolderOpen size={18} aria-hidden="true" />
                        <h3>输出文件</h3>
                      </div>
                      {isLoadingOutputs && <p className="muted">正在读取输出文件元数据。</p>}
                      {outputError && <p className="error-text">{outputError}</p>}
                      {outputFiles.length > 0 && (
                        <ul className="output-list">
                          {outputFiles.map((file) => (
                            <li key={file.file_id}>
                              <span className={`output-kind ${outputKind(file).toLowerCase()}`}>{outputKind(file)}</span>
                              <strong>{file.filename}</strong>
                              <span>{formatFileSize(file.size)}</span>
                              <code>{file.file_id}</code>
                              <small>{file.mime_type}</small>
                            </li>
                          ))}
                        </ul>
                      )}
                    </section>
                  )}
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
