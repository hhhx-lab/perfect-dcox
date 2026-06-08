import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileSearch,
  FileText,
  FolderOpen,
  LayoutDashboard,
  ListChecks,
  MessageSquareText,
  Plus,
  RefreshCcw,
  Save,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  apiClient,
  BatchFormatRun,
  DeliveryManifestItem,
  FileRecord,
  FixLoopRecord,
  FixPlan,
  FormatProfile,
  JobRecord,
  ProfileSummary,
  QualityReport,
  QualityStatus,
  RequirementSession,
  ServiceHealth,
} from "./api/client";

const workflowAreas = [
  { title: "获取格式需求", description: "对话 Agent 或格式文档分析", icon: MessageSquareText, anchor: "intake" },
  { title: "确认 Profile", description: "命名、保存、版本化", icon: FileText, anchor: "profile" },
  { title: "上传并处理", description: "选择 Profile 后排版", icon: Upload, anchor: "process" },
  { title: "下载与质检", description: "DOCX / PDF / 报告", icon: FolderOpen, anchor: "delivery" },
];

const qualityStatusOrder: QualityStatus[] = ["pass", "fixed", "warning", "fail", "unsupported"];

const qualityStatusLabels: Record<QualityStatus, string> = {
  pass: "通过",
  fixed: "已修复",
  warning: "警告",
  fail: "失败",
  unsupported: "无法判断",
};

function profileKey(profileId: string, version: string) {
  return `${profileId}@${version}`;
}

function cloneProfile(profile: FormatProfile): FormatProfile {
  return JSON.parse(JSON.stringify(profile)) as FormatProfile;
}

function colorInputValue(color?: string): string {
  return `#${(color || "000000").replace("#", "").padStart(6, "0").slice(0, 6)}`;
}

function profileColorValue(color: string): string {
  return color.replace("#", "").toUpperCase();
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
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

function deliveryStatusLabel(item: DeliveryManifestItem): string {
  if (item.delivery_status === "completed") return item.fix_loop_ids.length > 0 ? "自动修复后合规" : "机器质检合规";
  if (item.delivery_status === "manual_review_required") return "需要人工复核";
  return "处理失败";
}

function deliveryStatusDetail(item: DeliveryManifestItem): string {
  if (item.delivery_status === "completed") {
    return item.fix_loop_ids.length > 0
      ? `已执行 ${item.fix_loop_ids.length} 轮安全修复，并通过最终质量报告。`
      : "最终质量报告没有 warning、fail 或 unsupported 项。";
  }
  if (item.delivery_status === "manual_review_required") {
    return "输出可下载，但存在系统无法自动确认的规则，不能声称完全合规。";
  }
  return "任务失败，请查看 job 状态或质量报告。";
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
  const [intakeMode, setIntakeMode] = useState<"conversation" | "document">("conversation");
  const [requirementText, setRequirementText] = useState("");
  const [requirementFollowUp, setRequirementFollowUp] = useState("");
  const [requirementSession, setRequirementSession] = useState<RequirementSession | null>(null);
  const [requirementError, setRequirementError] = useState<string | null>(null);
  const [confirmProfileName, setConfirmProfileName] = useState("");
  const [confirmProfileVersion, setConfirmProfileVersion] = useState("1.0.0");
  const [confirmProfileDescription, setConfirmProfileDescription] = useState("");
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isImportingYaml, setIsImportingYaml] = useState(false);
  const [isExportingYaml, setIsExportingYaml] = useState(false);
  const [isCreatingRequirementSession, setIsCreatingRequirementSession] = useState(false);
  const [isRefreshingRequirementSession, setIsRefreshingRequirementSession] = useState(false);
  const [isSendingRequirementMessage, setIsSendingRequirementMessage] = useState(false);
  const [isConfirmingRequirementSession, setIsConfirmingRequirementSession] = useState(false);
  const [selectedRuleFile, setSelectedRuleFile] = useState<File | null>(null);
  const [ruleFileRecord, setRuleFileRecord] = useState<FileRecord | null>(null);
  const [selectedInputFiles, setSelectedInputFiles] = useState<File[]>([]);
  const [inputFileRecords, setInputFileRecords] = useState<FileRecord[]>([]);
  const [batchRun, setBatchRun] = useState<BatchFormatRun | null>(null);
  const [job, setJob] = useState<JobRecord | null>(null);
  const [outputFiles, setOutputFiles] = useState<FileRecord[]>([]);
  const [outputError, setOutputError] = useState<string | null>(null);
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [fixPlan, setFixPlan] = useState<FixPlan | null>(null);
  const [fixLoop, setFixLoop] = useState<FixLoopRecord | null>(null);
  const [fixPlanError, setFixPlanError] = useState<string | null>(null);
  const [selectedFixIssueIds, setSelectedFixIssueIds] = useState<string[]>([]);
  const [ruleUploadError, setRuleUploadError] = useState<string | null>(null);
  const [inputUploadError, setInputUploadError] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [isUploadingRuleFile, setIsUploadingRuleFile] = useState(false);
  const [isUploadingInputFile, setIsUploadingInputFile] = useState(false);
  const [isCreatingJob, setIsCreatingJob] = useState(false);
  const [isCreatingBatch, setIsCreatingBatch] = useState(false);
  const [isRefreshingBatch, setIsRefreshingBatch] = useState(false);
  const [isRefreshingJob, setIsRefreshingJob] = useState(false);
  const [isLoadingOutputs, setIsLoadingOutputs] = useState(false);
  const [isCreatingQualityReport, setIsCreatingQualityReport] = useState(false);
  const [isRefreshingQualityReport, setIsRefreshingQualityReport] = useState(false);
  const [isCreatingFixPlan, setIsCreatingFixPlan] = useState(false);
  const [isConfirmingFixLoop, setIsConfirmingFixLoop] = useState(false);
  const [isExecutingFixLoop, setIsExecutingFixLoop] = useState(false);
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
      if (cancelled) return;
      const loadedFiles: FileRecord[] = [];
      const failedIds: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "fulfilled") loadedFiles.push(result.value);
        else failedIds.push(outputIds[index]);
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
      if (!current) return current;
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

  const loadRequirementDraft = () => {
    if (!requirementSession?.profile_draft) {
      setRequirementError("没有可载入的 profile draft。");
      return;
    }
    const next = cloneProfile(requirementSession.profile_draft);
    next.status = "draft";
    next.source = "imported";
    setSelectedProfileKey(null);
    setSelectedProfile(null);
    setProfileDraft(next);
    setConfirmProfileName(next.name);
    setConfirmProfileVersion(next.version);
    setConfirmProfileDescription(next.description || "");
    setProfileSaveError(null);
    setProfileSaveMessage("已载入 Agent profile draft，确认后可保存为 draft 或 active。");
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

  const uploadWordFile = async (
    file: File | null,
    setRecord: (record: FileRecord | null) => void,
    setError: (message: string | null) => void,
    setLoading: (loading: boolean) => void,
  ) => {
    if (!file) {
      setError("请先选择 .doc 或 .docx 文件。");
      return null;
    }
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".doc") && !lowerName.endsWith(".docx")) {
      setError("仅支持 .doc 和 .docx 文件。");
      setRecord(null);
      return null;
    }
    setLoading(true);
    setError(null);
    try {
      const record = await apiClient.uploadFile(file);
      setRecord(record);
      return record;
    } catch (error) {
      setRecord(null);
      setError(error instanceof Error ? error.message : "上传失败。");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const uploadRuleFile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const uploaded = await uploadWordFile(selectedRuleFile, setRuleFileRecord, setRuleUploadError, setIsUploadingRuleFile);
    if (uploaded) {
      setIntakeMode("document");
      setRequirementSession(null);
      setRequirementError(null);
      setSelectedProfileKey(null);
      setSelectedProfile(null);
      setProfileDraft(null);
      await createRequirementSession({ source_type: "document", file_id: uploaded.file_id });
    }
  };

  const uploadInputFile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedInputFiles.length === 0) {
      setInputUploadError("请先选择至少一个 .doc 或 .docx 文件。");
      return;
    }
    const invalid = selectedInputFiles.find((file) => {
      const lowerName = file.name.toLowerCase();
      return !lowerName.endsWith(".doc") && !lowerName.endsWith(".docx");
    });
    if (invalid) {
      setInputUploadError(`仅支持 .doc 和 .docx 文件：${invalid.name}`);
      return;
    }
    setIsUploadingInputFile(true);
    setInputUploadError(null);
    try {
      setInputFileRecords(await Promise.all(selectedInputFiles.map((file) => apiClient.uploadFile(file))));
    } catch (error) {
      setInputFileRecords([]);
      setInputUploadError(error instanceof Error ? error.message : "上传失败。");
      return;
    } finally {
      setIsUploadingInputFile(false);
    }
    setJob(null);
    setBatchRun(null);
    setOutputFiles([]);
    setOutputError(null);
    setQualityReport(null);
    setQualityError(null);
    setFixPlan(null);
    setFixLoop(null);
    setFixPlanError(null);
    setSelectedFixIssueIds([]);
    setJobError(null);
  };

  const createRequirementSession = async (
    overridePayload?: { source_type: "document"; file_id: string } | { source_type: "conversation"; natural_language: string },
  ) => {
    setIsCreatingRequirementSession(true);
    setRequirementError(null);
    setRequirementSession(null);
    setSelectedProfileKey(null);
    setSelectedProfile(null);
    setProfileDraft(null);
    setProfileSaveMessage(null);
    setProfileSaveError(null);
    try {
      const created = await apiClient.createRequirementSession(
        overridePayload ??
          (intakeMode === "document"
            ? { source_type: "document", file_id: ruleFileRecord?.file_id ?? null }
            : { source_type: "conversation", natural_language: requirementText }),
      );
      setRequirementSession(created);
      if (created.profile_draft) {
        setConfirmProfileName(created.profile_draft.name);
        setConfirmProfileVersion("1.0.0");
        setConfirmProfileDescription(created.profile_draft.description || "");
      }
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "创建需求会话失败。");
    } finally {
      setIsCreatingRequirementSession(false);
    }
  };

  const refreshRequirementSession = async () => {
    if (!requirementSession) return;
    setIsRefreshingRequirementSession(true);
    setRequirementError(null);
    try {
      setRequirementSession(await apiClient.getRequirementSession(requirementSession.session_id));
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "刷新需求会话失败。");
    } finally {
      setIsRefreshingRequirementSession(false);
    }
  };

  const sendRequirementMessage = async () => {
    if (!requirementSession) {
      setRequirementError("请先启动需求会话。");
      return;
    }
    if (!requirementFollowUp.trim()) {
      setRequirementError("请先填写要补充的格式信息。");
      return;
    }
    setIsSendingRequirementMessage(true);
    setRequirementError(null);
    try {
      const updated = await apiClient.addRequirementMessage(requirementSession.session_id, requirementFollowUp);
      setRequirementSession(updated);
      setRequirementFollowUp("");
      if (updated.profile_draft) {
        setConfirmProfileName(updated.profile_draft.name);
        setConfirmProfileVersion(confirmProfileVersion || "1.0.0");
        setConfirmProfileDescription(updated.profile_draft.description || "");
      }
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "提交补充信息失败。");
    } finally {
      setIsSendingRequirementMessage(false);
    }
  };

  const confirmRequirementProfile = async () => {
    if (!requirementSession) {
      setRequirementError("请先启动需求会话。");
      return;
    }
    setIsConfirmingRequirementSession(true);
    setRequirementError(null);
    try {
      const confirmed = await apiClient.confirmRequirementSession(requirementSession.session_id, {
        profile_name: confirmProfileName,
        profile_version: confirmProfileVersion,
        profile_description: confirmProfileDescription || null,
      });
      setRequirementSession(confirmed);
      if (confirmed.profile_draft) {
        const key = profileKey(confirmed.profile_draft.id, confirmed.profile_draft.version);
        setSelectedProfile(confirmed.profile_draft);
        setSelectedProfileKey(key);
        setProfileDraft(cloneProfile(confirmed.profile_draft));
        setProfileSaveMessage(`已保存并选中 ${confirmed.profile_draft.name} v${confirmed.profile_draft.version}`);
        await loadProfiles(key);
      }
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "确认 Profile 失败。");
    } finally {
      setIsConfirmingRequirementSession(false);
    }
  };

  const createJob = async () => {
    const firstInput = inputFileRecords[0];
    if (!firstInput) {
      setJobError("请先上传 Word 文件。");
      return;
    }
    setIsCreatingJob(true);
    setJobError(null);
    try {
      const profileRef =
        selectedProfile && selectedProfileKey
          ? { profile_id: selectedProfile.id, profile_version: selectedProfile.version }
          : undefined;
      const created = await apiClient.createJob(firstInput.file_id, profileRef);
      setJob(created);
      setBatchRun(null);
      setOutputFiles([]);
      setOutputError(null);
      setQualityReport(null);
      setQualityError(null);
      setFixPlan(null);
      setFixLoop(null);
      setFixPlanError(null);
      setSelectedFixIssueIds([]);
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "创建任务失败。");
    } finally {
      setIsCreatingJob(false);
    }
  };

  const refreshJob = async () => {
    if (!job) return;
    setIsRefreshingJob(true);
    setJobError(null);
    try {
      setJob(await apiClient.getJob(job.job_id));
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "刷新任务失败。");
    } finally {
      setIsRefreshingJob(false);
    }
  };

  const createBatch = async () => {
    if (inputFileRecords.length === 0) {
      setJobError("请先上传至少一个 Word 文件。");
      return;
    }
    if (!selectedProfile) {
      setJobError("请先选择 Profile。");
      return;
    }
    setIsCreatingBatch(true);
    setJobError(null);
    try {
      const created = await apiClient.createBatch({
        profile_id: selectedProfile.id,
        profile_version: selectedProfile.version,
        input_file_ids: inputFileRecords.map((record) => record.file_id),
        output_formats: ["docx", "pdf"],
        auto_quality: true,
        auto_fix: true,
      });
      setBatchRun(created);
      const firstJobId = created.job_ids[0];
      if (firstJobId) {
        setJob(await apiClient.getJob(firstJobId));
      }
      setOutputFiles([]);
      setOutputError(null);
      setQualityReport(null);
      setQualityError(null);
      setFixPlan(null);
      setFixLoop(null);
      setFixPlanError(null);
      setSelectedFixIssueIds([]);
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "创建批量任务失败。");
    } finally {
      setIsCreatingBatch(false);
    }
  };

  const refreshBatch = async () => {
    if (!batchRun) return;
    setIsRefreshingBatch(true);
    setJobError(null);
    try {
      setBatchRun(await apiClient.getBatch(batchRun.batch_id));
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "刷新批量任务失败。");
    } finally {
      setIsRefreshingBatch(false);
    }
  };

  const createQualityReport = async () => {
    if (!job?.profile_id || !job.profile_version) {
      setQualityError("当前任务缺少 profile 引用，无法生成质量报告。");
      return;
    }
    if (job.output_file_ids.length === 0) {
      setQualityError("当前任务还没有输出文件，无法生成质量报告。");
      return;
    }

    setIsCreatingQualityReport(true);
    setQualityError(null);
    try {
      const report = await apiClient.createQualityReport({
        profile_id: job.profile_id,
        profile_version: job.profile_version,
        output_file_ids: job.output_file_ids,
        job_id: job.job_id,
      });
      setQualityReport(report);
      setFixPlan(null);
      setFixLoop(null);
      setFixPlanError(null);
      setSelectedFixIssueIds([]);
    } catch (error) {
      setQualityError(error instanceof Error ? error.message : "质量报告生成失败。");
    } finally {
      setIsCreatingQualityReport(false);
    }
  };

  const refreshQualityReport = async () => {
    if (!qualityReport) return;
    setIsRefreshingQualityReport(true);
    setQualityError(null);
    try {
      setQualityReport(await apiClient.getQualityReport(qualityReport.report_id));
    } catch (error) {
      setQualityError(error instanceof Error ? error.message : "质量报告刷新失败。");
    } finally {
      setIsRefreshingQualityReport(false);
    }
  };

  const createFixPlan = async () => {
    if (!qualityReport) {
      setFixPlanError("请先生成质量报告。");
      return;
    }
    setIsCreatingFixPlan(true);
    setFixPlanError(null);
    setFixLoop(null);
    setSelectedFixIssueIds([]);
    try {
      setFixPlan(await apiClient.createFixPlan(qualityReport.report_id));
    } catch (error) {
      setFixPlanError(error instanceof Error ? error.message : "修复计划生成失败。");
    } finally {
      setIsCreatingFixPlan(false);
    }
  };

  const toggleSelectedFixIssue = (issueId: string) => {
    setSelectedFixIssueIds((current) =>
      current.includes(issueId) ? current.filter((item) => item !== issueId) : [...current, issueId],
    );
    setFixPlanError(null);
  };

  const selectAllFixableIssues = () => {
    if (!fixPlan) return;
    setSelectedFixIssueIds(Array.from(new Set(fixPlan.actions.flatMap((action) => action.target_issue_ids))));
    setFixPlanError(null);
  };

  const confirmFixLoop = async () => {
    if (!qualityReport || !fixPlan) {
      setFixPlanError("请先生成质量报告和修复计划。");
      return;
    }
    if (selectedFixIssueIds.length === 0) {
      setFixPlanError("请先选择至少一个可自动修复的问题。");
      return;
    }
    setIsConfirmingFixLoop(true);
    setIsExecutingFixLoop(false);
    setFixPlanError(null);
    try {
      const confirmed = await apiClient.confirmFixLoop(qualityReport.report_id, {
        fix_plan_id: fixPlan.fix_plan_id,
        selected_issue_ids: selectedFixIssueIds,
      });
      setFixLoop(confirmed);
      setIsExecutingFixLoop(true);
      const executed = await apiClient.executeFixLoop(qualityReport.report_id, confirmed.fix_loop_id);
      setFixLoop(executed);
      if (executed.new_job_id) {
        setJob(await apiClient.getJob(executed.new_job_id));
      }
      if (executed.updated_report_id) {
        setQualityReport(await apiClient.getQualityReport(executed.updated_report_id));
        setFixPlan(null);
        setSelectedFixIssueIds([]);
      }
      if (executed.status === "failed") {
        setFixPlanError(executed.error_message || "修复执行失败。");
      }
    } catch (error) {
      setFixPlanError(error instanceof Error ? error.message : "执行修复计划失败。");
    } finally {
      setIsConfirmingFixLoop(false);
      setIsExecutingFixLoop(false);
    }
  };

  const selectedProfileSummary = profiles.find((item) => profileKey(item.profile_id, item.current_version) === selectedProfileKey);
  const qualityReportReady = Boolean(job?.profile_id && job.profile_version && job.output_file_ids.length > 0);
  const qualityRemainingCount = qualityReport?.summary.remaining_issue_count ?? 0;
  const fixableIssueIds = fixPlan ? Array.from(new Set(fixPlan.actions.flatMap((action) => action.target_issue_ids))) : [];
  const qualityVerdict =
    qualityReport && qualityRemainingCount === 0 && qualityReport.summary.all_compliant
      ? "全部合规"
      : qualityReport
        ? `仍有 ${qualityRemainingCount} 项待处理`
        : "待生成质量报告";
  const manualReviewIssues =
    qualityReport?.issues.filter((issue) => issue.status === "warning" || issue.status === "fail" || issue.status === "unsupported") ?? [];
  const boundaryIssues =
    qualityReport?.issues.filter((issue) =>
      [
        "docx.toc.fields",
        "docx.notes",
        "docx.visuals.caption_pairing",
        "docx.fields.update_policy",
        "pdf.text_extractability",
        "pdf.blank_pages",
      ].includes(issue.check_key),
    ) ?? [];
  const readinessItems = [
    {
      label: "LLM Agent",
      ok: Boolean(health?.services.llm_configured),
      detail: health?.services.llm_configured ? "可读取对话/格式文档" : "未配置时会停止分析",
    },
    {
      label: "Profile",
      ok: Boolean(selectedProfile),
      detail: selectedProfile
        ? `${selectedProfile.name} v${selectedProfile.version}`
        : requirementSession?.profile_draft
          ? "已有草案，仍需确认保存"
          : "等待 Agent 生成或手动选择",
    },
    {
      label: "Word 输入",
      ok: inputFileRecords.length > 0,
      detail: inputFileRecords.length > 0 ? `${inputFileRecords.length} 份文档已上传` : "等待上传 .doc/.docx",
    },
    {
      label: "导出质检",
      ok: Boolean(qualityReport?.summary.all_compliant),
      detail: qualityReport
        ? qualityReport.summary.all_compliant
          ? "质量报告已通过"
          : `${qualityReport.summary.remaining_issue_count} 项待处理`
        : batchRun
          ? "已导出，等待查看报告"
          : "等待导出后生成报告",
    },
  ];

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <LayoutDashboard size={22} aria-hidden="true" />
          <span>Word Format Agent</span>
        </div>
        <div className={`service-pill ${health ? "ok" : "warn"}`} aria-live="polite">
          {health ? <CheckCircle2 size={16} aria-hidden="true" /> : <AlertTriangle size={16} aria-hidden="true" />}
          <span>
            {health
              ? `${health.app_name} · LLM ${health.services.llm_configured ? "已配置" : "未配置"} · PDF ${
                  health.services.soffice_configured ? "可导出" : "未配置"
                }`
              : healthError || "正在连接后端"}
          </span>
        </div>
      </header>

      <section className="workspace-title">
        <p className="eyebrow">Production workflow</p>
        <h1>一键按自定义规则输出 Word / PDF</h1>
        <p>先由 Agent 读懂格式要求并沉淀为 Profile，再用这套 Profile 处理你的报告，最后下载规范化文件和质量报告。</p>
      </section>

      <section className="readiness-strip" aria-label="运行准备状态">
        {readinessItems.map((item) => (
          <article className={`readiness-item ${item.ok ? "ready" : "pending"}`} key={item.label}>
            {item.ok ? <CheckCircle2 size={18} aria-hidden="true" /> : <AlertTriangle size={18} aria-hidden="true" />}
            <div>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </div>
          </article>
        ))}
      </section>

      <section className="capability-panel always-visible" aria-label="生产能力边界">
        <div>
          <strong>自动保证范围</strong>
          <p>页面、页边距、正文/标题样式、基础页眉页脚、页码、表格线、题注、目录域、DOCX/PDF 下载和质量报告。</p>
        </div>
        <div>
          <strong>安全边界</strong>
          <p>复杂脚注尾注、浮动图片、PDF 文本不可抽取、无法确认的规则不会被显示成合规，会进入复核状态。</p>
        </div>
      </section>

      <nav className="workflow-nav" aria-label="工作流导航">
        {workflowAreas.map((area, index) => {
          const Icon = area.icon;
          return (
            <a href={`#${area.anchor}`} key={area.title}>
              <span>{index + 1}</span>
              <Icon size={18} aria-hidden="true" />
              <strong>{area.title}</strong>
              <small>{area.description}</small>
            </a>
          );
        })}
      </nav>

      <section className="workflow-step" id="intake" aria-labelledby="intake-title">
        <div className="step-heading">
          <span className="step-index">1</span>
          <div>
            <p className="eyebrow">Agent intake</p>
            <h2 id="intake-title">获取格式需求</h2>
          </div>
        </div>

        <div className="intake-switch" role="tablist" aria-label="格式需求入口">
          <button
            type="button"
            className={intakeMode === "conversation" ? "selected" : ""}
            onClick={() => {
              setIntakeMode("conversation");
              setRequirementError(null);
            }}
          >
            <MessageSquareText size={18} aria-hidden="true" />
            对话生成 Profile
          </button>
          <button
            type="button"
            className={intakeMode === "document" ? "selected" : ""}
            onClick={() => {
              setIntakeMode("document");
              setRequirementError(null);
            }}
          >
            <FileSearch size={18} aria-hidden="true" />
            上传格式文档生成 Profile
          </button>
        </div>

        {intakeMode === "conversation" ? (
          <div className="intake-panel">
            <label className="field-block">
              <span>格式要求描述</span>
              <textarea
                value={requirementText}
                onChange={(event) => {
                  setRequirementText(event.target.value);
                  setRequirementError(null);
                }}
                placeholder="例如：A4，正文宋体小四，英文 Times New Roman，1.5 倍行距，首行缩进 2 字符，一级标题黑体三号居中。"
              />
            </label>
            <div className="action-row">
              <button
                type="button"
                onClick={() => void createRequirementSession()}
                disabled={isCreatingRequirementSession || !requirementText.trim()}
              >
                <ClipboardCheck size={18} aria-hidden="true" />
                {isCreatingRequirementSession ? "分析中" : "让 Agent 拆解并追问"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={refreshRequirementSession}
                disabled={!requirementSession || isRefreshingRequirementSession}
              >
                <RefreshCcw size={18} aria-hidden="true" />
                {isRefreshingRequirementSession ? "刷新中" : "刷新会话"}
              </button>
            </div>
          </div>
        ) : (
          <div className="intake-panel split">
            <form className="upload-box" onSubmit={uploadRuleFile}>
              <label className="file-picker">
                <Upload size={18} aria-hidden="true" />
                <span>{selectedRuleFile ? selectedRuleFile.name : "选择格式要求 .doc/.docx"}</span>
                <input
                  type="file"
                  accept=".doc,.docx"
                  onChange={(event) => {
                    setSelectedRuleFile(event.target.files?.[0] ?? null);
                    setRuleUploadError(null);
                  }}
                />
              </label>
              <button type="submit" disabled={isUploadingRuleFile}>
                <Upload size={18} aria-hidden="true" />
                {isUploadingRuleFile || isCreatingRequirementSession ? "上传/分析中" : "上传并分析规则文档"}
              </button>
              {ruleFileRecord && <p className="record-line">{ruleFileRecord.filename} · {ruleFileRecord.file_id}</p>}
              {ruleUploadError && <p className="error-text">{ruleUploadError}</p>}
            </form>
            <div className="analysis-box">
              <strong>{ruleFileRecord ? ruleFileRecord.filename : "等待规则文档"}</strong>
              <p>
                {ruleFileRecord
                  ? "文档已登记；若需要重新分析，可再次启动 Agent。"
                  : "上传学校模板、期刊格式说明或自定义规则文档；上传后会立即调用 LLM Agent 分析。"}
              </p>
              <button type="button" onClick={() => void createRequirementSession()} disabled={isCreatingRequirementSession || !ruleFileRecord}>
                <FileSearch size={18} aria-hidden="true" />
                {isCreatingRequirementSession ? "抽取中" : "分析格式文档"}
              </button>
            </div>
          </div>
        )}

        {(requirementSession || requirementError) && (
          <section className="agent-result" aria-live="polite">
            <div className="result-heading">
              <div>
                <p className="eyebrow">Agent summary</p>
                <h3>规则拆解结果</h3>
              </div>
              {requirementSession && <span className={`status-badge ${requirementSession.status}`}>{requirementSession.status}</span>}
            </div>
            {requirementError && <p className="error-text">{requirementError}</p>}
            {requirementSession && (
              <>
                <dl className="compact-meta">
                  <div>
                    <dt>session_id</dt>
                    <dd>{requirementSession.session_id}</dd>
                  </div>
                  <div>
                    <dt>source</dt>
                    <dd>{requirementSession.source_type}{requirementSession.file_id ? ` · ${requirementSession.file_id}` : ""}</dd>
                  </div>
                  <div>
                    <dt>profile_draft</dt>
                    <dd>
                      {requirementSession.profile_draft
                        ? `${requirementSession.profile_draft.name} v${requirementSession.profile_draft.version}`
                        : "N/A"}
                    </dd>
                  </div>
                  <div>
                    <dt>missing</dt>
                    <dd>{requirementSession.missing_fields.length}</dd>
                  </div>
                </dl>
                {requirementSession.status !== "confirmed" && (
                  <p className="warning-note">这只是 Agent 草案，尚未保存为当前 Profile；未确认前不会用于导出。</p>
                )}
                {requirementSession.error_message && <p className="error-text">{requirementSession.error_message}</p>}
                {requirementSession.messages.length > 0 && (
                  <div className="chat-transcript" aria-label="Agent 对话">
                    {requirementSession.messages.slice(-4).map((message) => (
                      <article className={`chat-bubble ${message.role}`} key={`${message.role}-${message.created_at}-${message.content}`}>
                        <strong>{message.role}</strong>
                        <p>{message.content}</p>
                      </article>
                    ))}
                  </div>
                )}
                {requirementSession.requirement_summary?.items.length ? (
                  <div className="review-grid">
                    {requirementSession.requirement_summary.items.map((item) => (
                      <article
                        className={`review-card ${item.needs_confirmation ? "needs-confirmation" : ""}`}
                        key={`${item.field_path}-${item.value}`}
                      >
                        <div className="rule-card-heading">
                          <strong>{item.label}</strong>
                          <span className={`rule-source ${item.source}`}>{item.source}</span>
                        </div>
                        <p>{item.value}</p>
                        <small>
                          {item.field_path} · {Math.round(item.confidence * 100)}% · {item.supported ? "支持" : "暂不支持"}
                          {item.needs_confirmation ? " · 待确认" : ""}
                        </small>
                      </article>
                    ))}
                  </div>
                ) : null}
                {requirementSession.uncertain_items.length > 0 && (
                  <div className="review-grid">
                    {requirementSession.uncertain_items.map((item) => (
                      <article className="review-card warning-card" key={`${item.field_path}-${item.message}`}>
                        <strong>{item.field_path}</strong>
                        <p>{item.message}</p>
                        <small>{item.suggestion}</small>
                      </article>
                    ))}
                  </div>
                )}
                {requirementSession.evidence.length > 0 && (
                  <div className="review-grid">
                    {requirementSession.evidence.map((item) => (
                      <article className="review-card" key={`${item.field_path}-${item.quote ?? item.note ?? item.confidence}`}>
                        <strong>{item.field_path}</strong>
                        <p>{item.quote || item.note || "No direct quote"}</p>
                        <small>{Math.round(item.confidence * 100)}% · {item.source}</small>
                      </article>
                    ))}
                  </div>
                )}
                <div className="intake-panel">
                  <label className="field-block">
                    <span>补充回答 / 修正规则</span>
                    <textarea
                      value={requirementFollowUp}
                      onChange={(event) => setRequirementFollowUp(event.target.value)}
                      placeholder="例如：页眉居中写学校名称，页码页脚居中；二级标题左对齐黑体小四。"
                    />
                  </label>
                  <div className="action-row">
                    <button type="button" onClick={sendRequirementMessage} disabled={isSendingRequirementMessage || !requirementFollowUp.trim()}>
                      <MessageSquareText size={18} aria-hidden="true" />
                      {isSendingRequirementMessage ? "提交中" : "提交给 Agent 继续拆解"}
                    </button>
                    {requirementSession.profile_draft && (
                      <button type="button" className="secondary-button" onClick={loadRequirementDraft}>
                        <Save size={18} aria-hidden="true" />
                        载入为 Profile 草案
                      </button>
                    )}
                  </div>
                </div>
                {requirementSession.profile_draft && (
                  <div className="confirm-profile-panel">
                    <label>
                      <span>Profile 名称</span>
                      <input value={confirmProfileName} onChange={(event) => setConfirmProfileName(event.target.value)} />
                    </label>
                    <label>
                      <span>版本</span>
                      <input value={confirmProfileVersion} onChange={(event) => setConfirmProfileVersion(event.target.value)} />
                    </label>
                    <label>
                      <span>用途说明</span>
                      <input value={confirmProfileDescription} onChange={(event) => setConfirmProfileDescription(event.target.value)} />
                    </label>
                    <button
                      type="button"
                      onClick={confirmRequirementProfile}
                      disabled={isConfirmingRequirementSession || !confirmProfileName.trim() || !confirmProfileVersion.trim()}
                    >
                      <ShieldCheck size={18} aria-hidden="true" />
                      {isConfirmingRequirementSession ? "保存中" : "确认并保存 Profile"}
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </section>

      <section className="workflow-step" id="profile" aria-labelledby="profile-title">
        <div className="step-heading with-action">
          <div className="step-title">
            <span className="step-index">2</span>
            <div>
              <p className="eyebrow">Profile library</p>
              <h2 id="profile-title">确认并命名 Profile</h2>
            </div>
          </div>
          <button type="button" className="secondary-button" onClick={() => void loadProfiles()} disabled={isLoadingProfiles}>
            <RefreshCcw size={18} aria-hidden="true" />
            {isLoadingProfiles ? "加载中" : "刷新 Profile"}
          </button>
        </div>
        {profileError && <p className="error-text">{profileError}</p>}

        <div className="profile-workspace">
          <aside className="profile-library" aria-label="Profile 列表">
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
                    <small>{profile.status} · v{profile.current_version} · {profile.source}</small>
                  </button>
                );
              })
            )}
          </aside>

          <section className="profile-current" aria-live="polite">
            <div className="result-heading">
              <div>
                <p className="eyebrow">{selectedProfile?.id || "No profile selected"}</p>
                <h3>{selectedProfile?.name || "选择或载入一个 Profile"}</h3>
              </div>
              {selectedProfile && <span className={`status-badge ${selectedProfile.status}`}>{selectedProfile.status}</span>}
            </div>
            {selectedProfile ? (
              <dl className="compact-meta">
                <div>
                  <dt>版本</dt>
                  <dd>{selectedProfile.version}</dd>
                </div>
                <div>
                  <dt>页面</dt>
                  <dd>{selectedProfile.page.size} · {selectedProfile.page.orientation}</dd>
                </div>
                <div>
                  <dt>正文</dt>
                  <dd>
                    {selectedProfile.body.font.chinese} / {selectedProfile.body.font.latin} · {selectedProfile.body.font.size_pt}pt · #
                    {selectedProfile.body.font.color}
                  </dd>
                </div>
                <div>
                  <dt>更新时间</dt>
                  <dd>{selectedProfileSummary?.updated_at || "N/A"}</dd>
                </div>
              </dl>
            ) : (
              <p className="muted">可从左侧选择内置 Profile，也可在上一步载入 Agent 草案。</p>
            )}
          </section>

          {profileDraft && (
            <form className="profile-editor" onSubmit={(event) => event.preventDefault()}>
              <div className="editor-header">
                <div>
                  <p className="eyebrow">Profile editor</p>
                  <h3>关键规则</h3>
                </div>
                <div className="action-row">
                  <button type="button" className="secondary-button" onClick={createDraftFromSelected}>
                    <Plus size={18} aria-hidden="true" />
                    新建 Draft
                  </button>
                  <button type="button" onClick={saveProfileDraft} disabled={isSavingProfile}>
                    <Save size={18} aria-hidden="true" />
                    {isSavingProfile ? "保存中" : "保存 Profile"}
                  </button>
                </div>
              </div>
              {(profileSaveError || profileSaveMessage) && (
                <p className={profileSaveError ? "error-text" : "success-text"}>{profileSaveError || profileSaveMessage}</p>
              )}
              <div className="editor-grid">
                <label>
                  <span>Profile ID</span>
                  <input value={profileDraft.id} onChange={(event) => updateProfileDraft((draft) => void (draft.id = event.target.value))} />
                </label>
                <label>
                  <span>名称</span>
                  <input value={profileDraft.name} onChange={(event) => updateProfileDraft((draft) => void (draft.name = event.target.value))} />
                </label>
                <label>
                  <span>版本</span>
                  <input value={profileDraft.version} onChange={(event) => updateProfileDraft((draft) => void (draft.version = event.target.value))} />
                </label>
                <label>
                  <span>状态</span>
                  <select
                    value={profileDraft.status}
                    onChange={(event) => updateProfileDraft((draft) => void (draft.status = event.target.value as FormatProfile["status"]))}
                  >
                    <option value="draft">draft</option>
                    <option value="active">active</option>
                    <option value="archived">archived</option>
                  </select>
                </label>
                <label>
                  <span>纸张</span>
                  <select
                    value={profileDraft.page.size}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.page.size = event.target.value as FormatProfile["page"]["size"]))
                    }
                  >
                    <option value="A4">A4</option>
                    <option value="Letter">Letter</option>
                  </select>
                </label>
                <label>
                  <span>方向</span>
                  <select
                    value={profileDraft.page.orientation}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) => void (draft.page.orientation = event.target.value as FormatProfile["page"]["orientation"]),
                      )
                    }
                  >
                    <option value="portrait">portrait</option>
                    <option value="landscape">landscape</option>
                  </select>
                </label>
                <label>
                  <span>上边距 cm</span>
                  <input type="number" step="0.1" value={profileDraft.page.margins_cm.top} onChange={(event) => updateProfileDraft((draft) => void (draft.page.margins_cm.top = Number(event.target.value)))} />
                </label>
                <label>
                  <span>下边距 cm</span>
                  <input type="number" step="0.1" value={profileDraft.page.margins_cm.bottom} onChange={(event) => updateProfileDraft((draft) => void (draft.page.margins_cm.bottom = Number(event.target.value)))} />
                </label>
                <label>
                  <span>左边距 cm</span>
                  <input type="number" step="0.1" value={profileDraft.page.margins_cm.left} onChange={(event) => updateProfileDraft((draft) => void (draft.page.margins_cm.left = Number(event.target.value)))} />
                </label>
                <label>
                  <span>右边距 cm</span>
                  <input type="number" step="0.1" value={profileDraft.page.margins_cm.right} onChange={(event) => updateProfileDraft((draft) => void (draft.page.margins_cm.right = Number(event.target.value)))} />
                </label>
                <label>
                  <span>中文正文字体</span>
                  <input value={profileDraft.body.font.chinese} onChange={(event) => updateProfileDraft((draft) => void (draft.body.font.chinese = event.target.value))} />
                </label>
                <label>
                  <span>英文字体</span>
                  <input value={profileDraft.body.font.latin} onChange={(event) => updateProfileDraft((draft) => void (draft.body.font.latin = event.target.value))} />
                </label>
                <label>
                  <span>正文字号 pt</span>
                  <input type="number" step="0.5" value={profileDraft.body.font.size_pt} onChange={(event) => updateProfileDraft((draft) => void (draft.body.font.size_pt = Number(event.target.value)))} />
                </label>
                <label className="color-field">
                  <span>正文字色</span>
                  <input
                    type="color"
                    value={colorInputValue(profileDraft.body.font.color)}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.font.color = profileColorValue(event.target.value)))
                    }
                  />
                </label>
                <label className="color-field">
                  <span>标题字色</span>
                  <input
                    type="color"
                    value={colorInputValue(profileDraft.headings[0]?.font.color)}
                    onChange={(event) =>
                      updateProfileDraft((draft) => {
                        const nextColor = profileColorValue(event.target.value);
                        draft.headings.forEach((heading) => {
                          heading.font.color = nextColor;
                        });
                      })
                    }
                  />
                </label>
                <label>
                  <span>行距</span>
                  <input type="number" step="0.1" value={profileDraft.body.line_spacing} onChange={(event) => updateProfileDraft((draft) => void (draft.body.line_spacing = Number(event.target.value)))} />
                </label>
                <label>
                  <span>首行缩进字符</span>
                  <input
                    type="number"
                    step="0.5"
                    value={profileDraft.body.first_line_indent_chars}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.first_line_indent_chars = Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>正文对齐</span>
                  <select
                    value={profileDraft.body.alignment}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.body.alignment = event.target.value as FormatProfile["body"]["alignment"]))
                    }
                  >
                    <option value="justified">justified</option>
                    <option value="left">left</option>
                    <option value="center">center</option>
                    <option value="right">right</option>
                  </select>
                </label>
                <label>
                  <span>页眉文字</span>
                  <input
                    value={profileDraft.header_footer.header_text ?? ""}
                    placeholder="留空表示不写页眉"
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) => void (draft.header_footer.header_text = event.target.value.trim() || null),
                      )
                    }
                  />
                </label>
                <label className="color-field">
                  <span>页眉/页脚字色</span>
                  <input
                    type="color"
                    value={colorInputValue(profileDraft.header_footer.font.color)}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.header_footer.font.color = profileColorValue(event.target.value)))
                    }
                  />
                </label>
                <label>
                  <span>页眉对齐</span>
                  <select
                    value={profileDraft.header_footer.header_alignment}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) =>
                          void (draft.header_footer.header_alignment = event.target.value as FormatProfile["header_footer"]["header_alignment"]),
                      )
                    }
                  >
                    <option value="center">center</option>
                    <option value="left">left</option>
                    <option value="right">right</option>
                  </select>
                </label>
                <label className="toggle-field">
                  <span>页脚页码</span>
                  <input
                    type="checkbox"
                    checked={profileDraft.header_footer.footer_page_number}
                    onChange={(event) =>
                      updateProfileDraft((draft) => void (draft.header_footer.footer_page_number = event.target.checked))
                    }
                  />
                </label>
                <label>
                  <span>页码对齐</span>
                  <select
                    value={profileDraft.header_footer.footer_alignment}
                    onChange={(event) =>
                      updateProfileDraft(
                        (draft) =>
                          void (draft.header_footer.footer_alignment = event.target.value as FormatProfile["header_footer"]["footer_alignment"]),
                      )
                    }
                  >
                    <option value="center">center</option>
                    <option value="left">left</option>
                    <option value="right">right</option>
                  </select>
                </label>
              </div>
              <details className="advanced-panel">
                <summary>YAML 导入 / 导出</summary>
                <div className="action-row">
                  <button type="button" className="secondary-button" onClick={exportYaml} disabled={isExportingYaml}>
                    {isExportingYaml ? "导出中" : "导出 YAML"}
                  </button>
                  <button type="button" onClick={importYaml} disabled={isImportingYaml}>
                    {isImportingYaml ? "导入中" : "导入 YAML"}
                  </button>
                </div>
                {(yamlError || yamlMessage) && <p className={yamlError ? "error-text" : "success-text"}>{yamlError || yamlMessage}</p>}
                <textarea value={yamlText} onChange={(event) => setYamlText(event.target.value)} spellCheck={false} aria-label="Profile YAML" />
              </details>
            </form>
          )}
        </div>
      </section>

      <section className="workflow-step" id="process" aria-labelledby="process-title">
        <div className="step-heading">
          <span className="step-index">3</span>
          <div>
            <p className="eyebrow">Format run</p>
            <h2 id="process-title">选择 Profile 并上传 Word</h2>
          </div>
        </div>

        <div className="process-grid">
          <div className="run-context">
            <article>
              <span>Profile</span>
              <strong>{selectedProfile ? `${selectedProfile.name} v${selectedProfile.version}` : "未选择"}</strong>
              <small>
                {selectedProfile
                  ? selectedProfile.id
                  : requirementSession?.profile_draft
                    ? "Agent 已生成草案，但必须先确认保存为 Profile"
                    : "需要先在第 1/2 步生成并确认 Profile"}
              </small>
            </article>
            <article>
              <span>Input</span>
              <strong>{inputFileRecords.length > 0 ? `${inputFileRecords.length} 份文档已上传` : "未上传"}</strong>
              <small>{inputFileRecords.length > 0 ? inputFileRecords.map((record) => record.file_id).join(", ") : "支持 .doc / .docx"}</small>
            </article>
          </div>

          <form className="upload-box" onSubmit={uploadInputFile}>
            <label className="file-picker">
              <Upload size={18} aria-hidden="true" />
              <span>
                {selectedInputFiles.length > 0
                  ? selectedInputFiles.map((file) => file.name).join(", ")
                  : "选择一份或多份要规范化的 Word 文档"}
              </span>
              <input
                type="file"
                accept=".doc,.docx"
                multiple
                onChange={(event) => {
                  setSelectedInputFiles(Array.from(event.target.files ?? []));
                  setInputUploadError(null);
                }}
              />
            </label>
            <button type="submit" disabled={isUploadingInputFile}>
              <Upload size={18} aria-hidden="true" />
              {isUploadingInputFile ? "上传中" : "上传待处理文档"}
            </button>
            {inputUploadError && <p className="error-text">{inputUploadError}</p>}
            {inputFileRecords.length > 0 && (
              <div className="batch-file-list" aria-label="已上传文档">
                {inputFileRecords.map((record) => (
                  <article key={record.file_id}>
                    <strong>{record.filename}</strong>
                    <small>{record.file_id}</small>
                  </article>
                ))}
              </div>
            )}
          </form>
        </div>

        <div className="action-row">
          <button
            type="button"
            onClick={createBatch}
            disabled={inputFileRecords.length === 0 || !selectedProfile || isCreatingBatch}
          >
            <ListChecks size={18} aria-hidden="true" />
            {isCreatingBatch ? "批量处理中" : "开始批量规范化"}
          </button>
          <button type="button" className="secondary-button" onClick={createJob} disabled={inputFileRecords.length === 0 || !selectedProfile || isCreatingJob}>
            <ListChecks size={18} aria-hidden="true" />
            {isCreatingJob ? "处理中" : "仅处理第一份"}
          </button>
          <button type="button" className="secondary-button" onClick={refreshJob} disabled={!job || isRefreshingJob}>
            <RefreshCcw size={18} aria-hidden="true" />
            {isRefreshingJob ? "刷新中" : "刷新任务"}
          </button>
          <button type="button" className="secondary-button" onClick={refreshBatch} disabled={!batchRun || isRefreshingBatch}>
            <RefreshCcw size={18} aria-hidden="true" />
            {isRefreshingBatch ? "刷新中" : "刷新批量"}
          </button>
        </div>
        {jobError && <p className="error-text">{jobError}</p>}
        {batchRun && (
          <section className="job-strip" aria-label="批量任务状态">
            <span className={`status-badge ${batchRun.status}`}>{batchRun.status}</span>
            <dl className="compact-meta">
              <div>
                <dt>batch_id</dt>
                <dd>{batchRun.batch_id}</dd>
              </div>
              <div>
                <dt>jobs</dt>
                <dd>{batchRun.job_ids.length}</dd>
              </div>
              <div>
                <dt>profile</dt>
                <dd>{batchRun.profile_id} v{batchRun.profile_version}</dd>
              </div>
              <div>
                <dt>quality</dt>
                <dd>{batchRun.items.filter((item) => item.delivery_status === "manual_review_required").length} 份需复核</dd>
              </div>
            </dl>
            {batchRun.error_message && <p className="error-text">{batchRun.error_message}</p>}
          </section>
        )}
        {job && (
          <section className="job-strip" aria-live="polite">
            <span className={`status-badge ${job.status}`}>{job.status}</span>
            <dl className="compact-meta">
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
                <dt>outputs</dt>
                <dd>{job.output_file_ids.length}</dd>
              </div>
            </dl>
            {job.error_message && <p className="error-text">{job.error_message}</p>}
          </section>
        )}
      </section>

      <section className="workflow-step" id="delivery" aria-labelledby="delivery-title">
        <div className="step-heading with-action">
          <div className="step-title">
            <span className="step-index">4</span>
            <div>
              <p className="eyebrow">Delivery</p>
              <h2 id="delivery-title">下载规范化文件与质检报告</h2>
            </div>
          </div>
          {qualityReport && (
            <span className={`quality-gate ${qualityRemainingCount === 0 && qualityReport.summary.all_compliant ? "clear" : "blocked"}`}>
              <ShieldCheck size={16} aria-hidden="true" />
              {qualityVerdict}
            </span>
          )}
        </div>

        <section className="delivery-table" aria-label="输出文件">
          {batchRun && batchRun.items.length > 0 && (
            <div className="batch-delivery-list" aria-label="批量输出清单">
              <div className="batch-delivery-toolbar">
                <strong>批量交付清单</strong>
                <a className="download-link secondary-download" href={apiClient.downloadBatchManifestUrl(batchRun.batch_id)} download>
                  <Download size={16} aria-hidden="true" />
                  下载 Manifest
                </a>
              </div>
              {batchRun.items.map((item, index) => (
                <article className="batch-delivery-row" key={`${item.input_file_id}-${item.job_id}`}>
                  <span className={`status-badge ${item.delivery_status}`}>{item.delivery_status}</span>
                  <div>
                    <strong>文档 {index + 1}</strong>
                    <small>{item.input_file_id} · {item.job_id}</small>
                    <small>
                      {deliveryStatusLabel(item)} · {deliveryStatusDetail(item)}
                      {item.fix_loop_ids.length > 0 ? ` · fix-loop ${item.fix_loop_ids.join(", ")}` : ""}
                    </small>
                  </div>
                  <div className="batch-downloads">
                    {item.final_docx_file_id && (
                      <a className="download-link" href={apiClient.downloadFileUrl(item.final_docx_file_id)} download>
                        <Download size={16} aria-hidden="true" />
                        下载 DOCX
                      </a>
                    )}
                    {item.final_pdf_file_id && (
                      <a className="download-link" href={apiClient.downloadFileUrl(item.final_pdf_file_id)} download>
                        <Download size={16} aria-hidden="true" />
                        下载 PDF
                      </a>
                    )}
                    {item.quality_report_id && (
                      <>
                        <a className="download-link secondary-download" href={apiClient.downloadQualityReportUrl(item.quality_report_id, "json")} download>
                          <Download size={16} aria-hidden="true" />
                          Report JSON
                        </a>
                        <a
                          className="download-link secondary-download"
                          href={apiClient.downloadQualityReportUrl(item.quality_report_id, "markdown")}
                          download
                        >
                          <Download size={16} aria-hidden="true" />
                          Report MD
                        </a>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
          {isLoadingOutputs && <p className="muted">正在读取输出文件元数据。</p>}
          {outputError && <p className="error-text">{outputError}</p>}
          {outputFiles.length === 0 && !isLoadingOutputs && !batchRun ? (
            <p className="muted">规范化任务完成后，DOCX / PDF 会出现在这里。</p>
          ) : (
            outputFiles.map((file) => (
              <article className="delivery-row" key={file.file_id}>
                <span className={`output-kind ${outputKind(file).toLowerCase()}`}>{outputKind(file)}</span>
                <strong>{file.filename}</strong>
                <small>{formatFileSize(file.size)} · {file.mime_type}</small>
                <a className="download-link" href={apiClient.downloadFileUrl(file.file_id)} download={file.filename}>
                  <Download size={16} aria-hidden="true" />
                  下载{outputKind(file)}
                </a>
              </article>
            ))
          )}
        </section>

        <section className="quality-panel" aria-label="质量报告">
          <div className="result-heading">
            <div>
              <p className="eyebrow">Quality gate</p>
              <h3>格式质量报告</h3>
            </div>
            <div className="action-row">
              <button type="button" onClick={createQualityReport} disabled={!qualityReportReady || isCreatingQualityReport}>
                <ClipboardCheck size={18} aria-hidden="true" />
                {isCreatingQualityReport ? "生成中" : "生成质量报告"}
              </button>
              <button type="button" className="secondary-button" onClick={refreshQualityReport} disabled={!qualityReport || isRefreshingQualityReport}>
                <RefreshCcw size={18} aria-hidden="true" />
                {isRefreshingQualityReport ? "刷新中" : "刷新报告"}
              </button>
            </div>
          </div>
          {!qualityReportReady && <p className="muted">需要已完成输出文件和 profile 引用后才能生成质量报告。</p>}
          {qualityError && <p className="error-text">{qualityError}</p>}
          {qualityReport && (
            <div className="quality-report" aria-live="polite">
              <dl className="compact-meta">
                <div>
                  <dt>report_id</dt>
                  <dd>{qualityReport.report_id}</dd>
                </div>
                <div>
                  <dt>profile</dt>
                  <dd>{qualityReport.profile_id} v{qualityReport.profile_version}</dd>
                </div>
                <div>
                  <dt>输出文件</dt>
                  <dd>{qualityReport.output_file_ids.length}</dd>
                </div>
                <div>
                  <dt>生成时间</dt>
                  <dd>{qualityReport.created_at}</dd>
                </div>
              </dl>
              <div className="quality-counts" aria-label="质量状态计数">
                {qualityStatusOrder.map((status) => (
                  <div className={`quality-count ${status}`} key={status}>
                    <span>{qualityStatusLabels[status]}</span>
                    <strong>{qualityReport.summary.counts[status] ?? 0}</strong>
                  </div>
                ))}
              </div>
              <div className={`remaining-summary ${qualityRemainingCount === 0 && qualityReport.summary.all_compliant ? "clear" : "attention"}`}>
                <strong>{qualityVerdict}</strong>
                <p>
                  {qualityRemainingCount === 0 && qualityReport.summary.all_compliant
                    ? "当前报告没有 warning、fail 或 unsupported 项。"
                    : "仍存在 warning、fail 或 unsupported 项时，系统不会把输出标记为完全合规。"}
                </p>
              </div>
              <section className="capability-panel" aria-label="能力边界">
                <div>
                  <strong>自动保证范围</strong>
                  <p>页面尺寸、页边距、正文/标题字体、行距、首行缩进、基础页眉页脚、页码、表格线、题注居中和 PDF 可读性。</p>
                </div>
                <div>
                  <strong>复核边界</strong>
                  <p>
                    {manualReviewIssues.length === 0
                      ? "当前没有需要复核的 warning、fail 或 unsupported 项。"
                      : `当前有 ${manualReviewIssues.length} 项需要处理；脚注尾注、浮动图片、手写目录或 PDF 文本不可抽取不会被伪装成合规。`}
                  </p>
                </div>
                {boundaryIssues.length > 0 && (
                  <div className="boundary-list">
                    {boundaryIssues.map((issue) => (
                      <span className={`boundary-pill ${issue.status}`} key={issue.issue_id}>
                        {issue.check_key}: {qualityStatusLabels[issue.status]}
                      </span>
                    ))}
                  </div>
                )}
              </section>
              <div className="action-row">
                <a className="download-link secondary-download" href={apiClient.downloadQualityReportUrl(qualityReport.report_id, "json")} download>
                  <Download size={16} aria-hidden="true" />
                  下载 JSON 报告
                </a>
                <a className="download-link secondary-download" href={apiClient.downloadQualityReportUrl(qualityReport.report_id, "markdown")} download>
                  <Download size={16} aria-hidden="true" />
                  下载 Markdown 报告
                </a>
              </div>
              <div className="quality-groups">
                {qualityStatusOrder.map((status) => {
                  const issues =
                    qualityReport.issues_by_status[status] ??
                    qualityReport.issues.filter((issue) => issue.status === status);
                  return (
                    <section className="quality-group" key={status}>
                      <div className="quality-group-heading">
                        <h4>{qualityStatusLabels[status]}</h4>
                        <span>{issues.length}</span>
                      </div>
                      {issues.length === 0 ? (
                        <p className="muted">暂无该状态的检查项。</p>
                      ) : (
                        issues.map((issue) => (
                          <article className="quality-issue" key={issue.issue_id}>
                            <div>
                              <strong>{issue.title}</strong>
                              <span className={`severity-badge ${issue.severity}`}>{issue.severity}</span>
                            </div>
                            <p>{issue.description || "无补充说明。"}</p>
                            <small>{issue.profile_rule_ref || "profile rule N/A"} · {issue.location || "location N/A"}</small>
                            {issue.recommendation && <small>{issue.recommendation}</small>}
                          </article>
                        ))
                      )}
                    </section>
                  );
                })}
              </div>

              <section className="fix-plan-panel" aria-label="Agent 修复执行">
                <div className="result-heading">
                  <div>
                    <p className="eyebrow">Fix loop</p>
                    <h3>修复执行</h3>
                  </div>
                  {fixLoop && <span className={`status-badge ${fixLoop.status}`}>{fixLoop.status}</span>}
                </div>
                <div className="action-row">
                  <button type="button" onClick={createFixPlan} disabled={!qualityReport || isCreatingFixPlan}>
                    <ClipboardCheck size={18} aria-hidden="true" />
                    {isCreatingFixPlan ? "生成中" : "生成修复建议"}
                  </button>
                  <button type="button" className="secondary-button" onClick={selectAllFixableIssues} disabled={!fixPlan || fixableIssueIds.length === 0}>
                    选择可修复项
                  </button>
                  <button
                    type="button"
                    onClick={confirmFixLoop}
                    disabled={!fixPlan || selectedFixIssueIds.length === 0 || isConfirmingFixLoop || isExecutingFixLoop}
                  >
                    <Save size={18} aria-hidden="true" />
                    {isExecutingFixLoop ? "执行中" : isConfirmingFixLoop ? "确认中" : "执行所选修复"}
                  </button>
                </div>
                {fixPlanError && <p className="error-text">{fixPlanError}</p>}
                {fixPlan && (
                  <div className="fix-plan-detail">
                    <dl className="compact-meta">
                      <div>
                        <dt>fix_plan_id</dt>
                        <dd>{fixPlan.fix_plan_id}</dd>
                      </div>
                      <div>
                        <dt>自动动作</dt>
                        <dd>{fixPlan.actions.length}</dd>
                      </div>
                      <div>
                        <dt>人工复核</dt>
                        <dd>{fixPlan.manual_review_issue_ids.length}</dd>
                      </div>
                      <div>
                        <dt>已选择</dt>
                        <dd>{selectedFixIssueIds.length}</dd>
                      </div>
                    </dl>
                    <div className="fix-action-list">
                      {fixPlan.actions.length === 0 ? (
                        <p className="muted">没有可自动修复动作，需要人工复核。</p>
                      ) : (
                        fixPlan.actions.map((action) => (
                          <label className="fix-action-row" key={`${action.action}-${action.target_issue_ids.join("-")}`}>
                            <input
                              type="checkbox"
                              checked={action.target_issue_ids.every((issueId) => selectedFixIssueIds.includes(issueId))}
                              onChange={() => action.target_issue_ids.forEach(toggleSelectedFixIssue)}
                            />
                            <span>
                              <strong>{action.action}</strong>
                              <small>{action.target_issue_ids.join(", ")}</small>
                            </span>
                          </label>
                        ))
                      )}
                    </div>
                    {fixPlan.manual_review_issue_ids.length > 0 && (
                      <section className="manual-review-box">
                        <strong>人工复核项</strong>
                        <p>{fixPlan.manual_review_issue_ids.join(", ")}</p>
                      </section>
                    )}
                  </div>
                )}
                {fixLoop && (
                  <section className="fix-loop-record">
                    <strong>已创建 fix-loop 记录</strong>
                    <dl className="compact-meta">
                      <div>
                        <dt>fix_loop_id</dt>
                        <dd>{fixLoop.fix_loop_id}</dd>
                      </div>
                      <div>
                        <dt>selected</dt>
                        <dd>{fixLoop.selected_issue_ids.length}</dd>
                      </div>
                      <div>
                        <dt>new_job</dt>
                        <dd>{fixLoop.new_job_id || "pending"}</dd>
                      </div>
                      <div>
                        <dt>updated_report</dt>
                        <dd>{fixLoop.updated_report_id || "pending"}</dd>
                      </div>
                    </dl>
                  </section>
                )}
              </section>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default App;
