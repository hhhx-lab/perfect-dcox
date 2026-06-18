import {
  AlertCircle,
  Braces,
  CheckCircle2,
  Download,
  FileText,
  FolderOpen,
  Layers3,
  ListChecks,
  MessageSquareText,
  PencilRuler,
  RefreshCcw,
  Save,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  apiClient,
  BatchFormatRun,
  DeliveryManifestItem,
  FileRecord,
  FormatProfile,
  JobRecord,
  LLMHealth,
  ProfileSummary,
  RequirementSession,
  ServiceHealth,
  TextFont,
  RequirementAttachmentSourceKind,
} from "./api/client";

type IntakeMode = "conversation" | "document" | "visual";
type OutputFormat = "docx" | "pdf";
type CoverageFilter = "all" | "supported" | "partial" | "unsupported" | "locked" | "missing" | "evidence";

const steps = [
  { id: "profile", label: "Profile", icon: PencilRuler },
  { id: "template", label: "Template", icon: Layers3 },
  { id: "source", label: "Source", icon: Upload },
  { id: "delivery", label: "Delivery", icon: Download },
];

function profileKey(profileId: string, version: string) {
  return `${profileId}@${version}`;
}

function bumpPatchVersion(version: string) {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)(.*)$/);
  if (!match) return `${version}.1`;
  return `${match[1]}.${match[2]}.${Number(match[3]) + 1}`;
}

async function nextAvailableProfileVersion(profileId: string, requestedVersion: string) {
  let version = requestedVersion || "1.0.0";
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      await apiClient.getProfile(profileId, version);
      version = bumpPatchVersion(version);
    } catch (error) {
      const message = error instanceof Error ? error.message.toLowerCase() : "";
      if (message.includes("not found")) return version;
      throw error;
    }
  }
  return `${version}.${Date.now()}`;
}

function defaultTextFont(size = 12, weight: TextFont["weight"] = "normal"): TextFont {
  return {
    chinese: "SimSun",
    latin: "Times New Roman",
    size_pt: size,
    weight,
    color: "000000",
  };
}

function withProfileDefaults(profile: FormatProfile): FormatProfile {
  profile.schema_version = profile.schema_version || "2.0.0";
  profile.body.space_before_pt ??= 0;
  profile.body.space_after_pt ??= 0;
  profile.headings = (profile.headings || []).map((heading) => ({
    ...heading,
    line_spacing: heading.line_spacing ?? null,
    space_before_pt: heading.space_before_pt ?? 0,
    space_after_pt: heading.space_after_pt ?? 0,
    first_line_indent_chars: heading.first_line_indent_chars ?? 0,
    keep_with_next: heading.keep_with_next ?? false,
    page_break_before: heading.page_break_before ?? false,
  }));
  profile.table.caption.bilingual ??= false;
  profile.table.caption.english_prefix ??= "Table";
  profile.table.caption.separator ??= " ";
  profile.table.caption.numbering ??= "chapter";
  profile.table.border_style ??= "three_line";
  profile.table.header_repeat ??= true;
  profile.table.autofit ??= true;
  profile.table.notes_position ??= "below";
  profile.table.enforce_caption_above ??= true;
  profile.figure.caption.bilingual ??= false;
  profile.figure.caption.english_prefix ??= "Figure";
  profile.figure.caption.separator ??= " ";
  profile.figure.caption.numbering ??= "chapter";
  profile.figure.placement ??= "inline";
  profile.figure.half_column_max_mm ??= 60;
  profile.figure.full_width_min_mm ??= 100;
  profile.figure.full_width_max_mm ??= 130;
  profile.figure.enforce_caption_below ??= true;
  profile.header_footer.footer_text ??= null;
  profile.header_footer.different_first_page ??= false;
  profile.header_footer.different_odd_even ??= false;
  profile.header_footer.page_number_format ??= "arabic";
  profile.header_footer.page_number_start ??= 1;
  profile.document_grid ??= {
    enabled: false,
    type: "none",
    characters_per_line: null,
    lines_per_page: null,
    snap_to_grid: false,
  };
  profile.toc ??= {
    enabled: true,
    title: "目录",
    include_levels: 3,
    show_page_numbers: true,
    right_align_page_numbers: true,
    use_hyperlinks: true,
    update_fields_on_open: true,
  };
  profile.list_numbering ??= {
    ordered_pattern: "1.",
    unordered_marker: "·",
    multilevel_enabled: true,
    restart_per_section: false,
  };
  profile.numbering ??= {
    enabled: true,
    heading_pattern: null,
    restart_per_section: false,
  };
  profile.unit_rules ??= {
    enforce_consistency: true,
    measurement_units: ["mm", "cm", "m", "kg", "s"],
    currency_units: ["元", "万元", "CNY", "USD"],
    unit_spacing: "preserve",
    use_si_symbols: true,
    normalize_fullwidth_numbers: true,
  };
  profile.notes ??= {
    font: defaultTextFont(9),
    line_spacing: 1,
    space_before_pt: 0,
    space_after_pt: 0,
  };
  profile.notes.font ??= defaultTextFont(9);
  profile.notes.line_spacing ??= 1;
  profile.notes.space_before_pt ??= 0;
  profile.notes.space_after_pt ??= 0;
  profile.appendix ??= {
    title_font: {
      ...defaultTextFont(12, "bold"),
      chinese: "SimHei",
    },
    body_font: defaultTextFont(12),
    title_alignment: "left",
    body_alignment: "justified",
    body_line_spacing: 1.5,
    body_first_line_indent_chars: 2,
  };
  profile.appendix.title_font ??= {
    ...defaultTextFont(12, "bold"),
    chinese: "SimHei",
  };
  profile.appendix.body_font ??= defaultTextFont(12);
  profile.appendix.title_alignment ??= "left";
  profile.appendix.body_alignment ??= "justified";
  profile.appendix.body_line_spacing ??= 1.5;
  profile.appendix.body_first_line_indent_chars ??= 2;
  profile.source_documents ??= [];
  profile.capability_coverage ??= [];
  profile.manual_overrides ??= [];
  profile.locked_fields ??= [];
  profile.llm_final_review ??= {
    enabled: true,
    required: true,
    check_garbled_text: true,
    check_blank_pages: true,
    check_overlap: true,
    check_table_figure_overflow: true,
  };
  profile.delivery_gate.fail_on_unsupported_rules ??= true;
  return profile;
}

function cloneProfile(profile: FormatProfile): FormatProfile {
  return withProfileDefaults(JSON.parse(JSON.stringify(profile)) as FormatProfile);
}

function profileNeedsV2Defaults(profile: FormatProfile): boolean {
  return (
    !profile.document_grid ||
    !profile.toc ||
    !profile.list_numbering ||
    !profile.unit_rules ||
    !profile.notes ||
    !profile.appendix ||
    !profile.table.border_style ||
    !profile.figure.placement ||
    profile.body.space_before_pt === undefined
  );
}

function defaultHeading(profile: FormatProfile, level: number): FormatProfile["headings"][number] {
  const sizeByLevel: Record<number, number> = { 1: 16, 2: 14, 3: 12 };
  return {
    level,
    font: {
      ...defaultTextFont(sizeByLevel[level] ?? profile.body.font.size_pt, "bold"),
      chinese: profile.headings[0]?.font.chinese || "SimHei",
      latin: profile.headings[0]?.font.latin || profile.body.font.latin,
    },
    alignment: level === 1 ? "center" : "left",
    numbering: level === 1 ? "chapter" : "decimal",
    line_spacing: profile.body.line_spacing,
    space_before_pt: level === 1 ? 12 : 6,
    space_after_pt: 6,
    first_line_indent_chars: 0,
    keep_with_next: true,
    page_break_before: false,
  };
}

function ensureHeading(profile: FormatProfile, level: number): FormatProfile["headings"][number] {
  const existing = profile.headings.find((heading) => heading.level === level);
  if (existing) return existing;
  const created = defaultHeading(profile, level);
  profile.headings.push(created);
  profile.headings.sort((a, b) => a.level - b.level);
  return created;
}

function colorInputValue(color?: string): string {
  return `#${(color || "000000").replace("#", "").padStart(6, "0").slice(0, 6)}`;
}

function profileColorValue(color: string): string {
  return color.replace("#", "").toUpperCase();
}

function splitCsv(value: string): string[] {
  return value
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function collectChangedPaths(before: unknown, after: unknown, prefix = ""): string[] {
  if (JSON.stringify(before) === JSON.stringify(after)) return [];
  if (!isPlainObject(before) && !Array.isArray(before)) return prefix ? [prefix] : [];
  if (!isPlainObject(after) && !Array.isArray(after)) return prefix ? [prefix] : [];
  const beforeObject = before as Record<string, unknown> | unknown[];
  const afterObject = after as Record<string, unknown> | unknown[];
  const keys = new Set([...Object.keys(beforeObject), ...Object.keys(afterObject)]);
  const paths: string[] = [];
  keys.forEach((key) => {
    const nextPrefix = Array.isArray(afterObject) || Array.isArray(beforeObject)
      ? `${prefix}[${key}]`
      : prefix
        ? `${prefix}.${key}`
        : key;
    paths.push(...collectChangedPaths((beforeObject as Record<string, unknown>)[key], (afterObject as Record<string, unknown>)[key], nextPrefix));
  });
  return paths;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function markLockedCoverage(profile: FormatProfile, changedPaths: string[]) {
  if (!changedPaths.length) return;
  profile.locked_fields = Array.from(new Set([...(profile.locked_fields ?? []), ...changedPaths]));
  profile.capability_coverage = (profile.capability_coverage ?? []).map((item) => ({
    ...item,
    locked_by_user: item.locked_by_user || profile.locked_fields.some((field) => field === item.field_path || field.startsWith(`${item.field_path}.`) || item.field_path.startsWith(`${field}.`)),
  }));
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
  const lower = file.filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "PDF";
  if (lower.endsWith(".docx")) return "DOCX";
  return "FILE";
}

function deliveryLabel(item: DeliveryManifestItem): string {
  if (item.delivery_status === "completed") return "内部校验通过";
  if (item.delivery_status === "manual_review_required") return "未放行";
  return "失败";
}

function gatePassed(summary: Record<string, unknown> | undefined): boolean {
  const docx = summary?.docx;
  return Boolean(docx && typeof docx === "object" && "passed" in docx && docx.passed === true);
}

function llmTone(status: LLMHealth | null | undefined): "ok" | "warn" | "bad" {
  if (!status?.configured) return "bad";
  if (status.reachable === true) return "ok";
  if (status.status === "configured_unverified") return "warn";
  return "bad";
}

function llmLabel(status: LLMHealth | null | undefined): string {
  if (!status?.configured) return "missing";
  if (status.reachable === true) return "reachable";
  if (status.status === "configured_unverified") return "unverified";
  return "failed";
}

function llmDetail(status: LLMHealth | null | undefined): string {
  if (!status) return "LLM 状态未加载。";
  if (!status.configured) return "未配置 LLM_API_KEY / LLM_MODEL。";
  if (status.reachable === true) return `${status.model ?? "model"} 可生成内容。`;
  if (status.status === "configured_unverified") return `${status.model ?? "model"} 已配置，尚未做真实生成检测。`;
  return status.error_message || "LLM 已配置，但真实生成检测失败。";
}

type CapabilityCoverageItem = FormatProfile["capability_coverage"][number];

function coverageStats(profile: FormatProfile | null) {
  const items = profile?.capability_coverage ?? [];
  const blocked = items.filter((item) => item.unsupported_behavior === "block" && (item.formatter === "unsupported" || item.qc === "unsupported"));
  return {
    total: items.length,
    supported: items.filter((item) => item.formatter === "supported" && item.qc === "supported").length,
    partial: items.filter((item) => item.formatter === "partial" || item.qc === "partial").length,
    delegated: items.filter((item) => item.formatter === "template_delegated" || item.qc === "template_delegated").length,
    unsupported: items.filter((item) => item.formatter === "unsupported" || item.qc === "unsupported").length,
    blocked: blocked.length,
    locked: items.filter((item) => item.locked_by_user).length,
    evidence: profile?.rule_evidence?.length ?? 0,
    missing: profile?.missing_fields?.length ?? 0,
  };
}

function statusRank(item: CapabilityCoverageItem): number {
  if (item.formatter === "unsupported" || item.qc === "unsupported") return 0;
  if (item.formatter === "partial" || item.qc === "partial") return 1;
  if (item.formatter === "template_delegated" || item.qc === "template_delegated") return 2;
  return 3;
}

function filterCoverageItems(profile: FormatProfile | null, query: string, filter: CoverageFilter): CapabilityCoverageItem[] {
  const normalizedQuery = query.trim().toLowerCase();
  const evidencePaths = new Set((profile?.rule_evidence ?? []).map((item) => item.field_path));
  const missingPaths = new Set(profile?.missing_fields ?? []);
  return [...(profile?.capability_coverage ?? [])]
    .filter((item) => {
      const tone = coverageTone(item);
      if (filter === "supported" && tone !== "supported") return false;
      if (filter === "partial" && tone !== "partial" && tone !== "delegated") return false;
      if (filter === "unsupported" && tone !== "unsupported") return false;
      if (filter === "locked" && !item.locked_by_user) return false;
      if (filter === "missing" && !missingPaths.has(item.field_path)) return false;
      if (filter === "evidence" && !evidencePaths.has(item.field_path)) return false;
      if (!normalizedQuery) return true;
      return [
        item.field_path,
        item.frontend,
        item.agent,
        item.formatter,
        item.qc,
        item.llm_final_review,
        item.source,
        item.note ?? "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    })
    .sort((a, b) => Number(b.locked_by_user) - Number(a.locked_by_user) || statusRank(a) - statusRank(b) || a.field_path.localeCompare(b.field_path));
}

function evidenceForField(profile: FormatProfile, fieldPath: string) {
  return (profile.rule_evidence ?? []).filter((item) => item.field_path === fieldPath || item.field_path.startsWith(`${fieldPath}.`) || fieldPath.startsWith(`${item.field_path}.`));
}

function unsupportedForField(profile: FormatProfile, fieldPath: string) {
  return (profile.unsupported_rules ?? []).filter((item) => item.field_path === fieldPath || item.field_path.startsWith(`${fieldPath}.`) || fieldPath.startsWith(`${item.field_path}.`));
}

function confidenceLabel(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

function coverageTone(item: CapabilityCoverageItem): "supported" | "partial" | "delegated" | "unsupported" {
  if (item.formatter === "unsupported" || item.qc === "unsupported") return "unsupported";
  if (item.formatter === "partial" || item.qc === "partial") return "partial";
  if (item.formatter === "template_delegated" || item.qc === "template_delegated") return "delegated";
  return "supported";
}

function coverageLabel(item: CapabilityCoverageItem): string {
  const tone = coverageTone(item);
  if (tone === "supported") return "supported";
  if (tone === "partial") return "partial";
  if (tone === "delegated") return "template";
  return item.unsupported_behavior === "block" ? "blocked" : "unsupported";
}

function App() {
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [llmHealth, setLlmHealth] = useState<LLMHealth | null>(null);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileKey, setSelectedProfileKey] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<FormatProfile | null>(null);
  const [profileDraft, setProfileDraft] = useState<FormatProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [intakeMode, setIntakeMode] = useState<IntakeMode>("conversation");
  const [requirementText, setRequirementText] = useState("");
  const [requirementFollowUp, setRequirementFollowUp] = useState("");
  const [requirementSession, setRequirementSession] = useState<RequirementSession | null>(null);
  const [requirementError, setRequirementError] = useState<string | null>(null);
  const [confirmProfileName, setConfirmProfileName] = useState("");
  const [confirmProfileVersion, setConfirmProfileVersion] = useState("1.0.0");
  const [confirmProfileDescription, setConfirmProfileDescription] = useState("");
  const [ruleFile, setRuleFile] = useState<File | null>(null);
  const [ruleFileKind, setRuleFileKind] = useState<RequirementAttachmentSourceKind>("rule_document");
  const [ruleFileRecord, setRuleFileRecord] = useState<FileRecord | null>(null);
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateFileRecord, setTemplateFileRecord] = useState<FileRecord | null>(null);
  const [inputFiles, setInputFiles] = useState<File[]>([]);
  const [inputFileRecords, setInputFileRecords] = useState<FileRecord[]>([]);
  const [job, setJob] = useState<JobRecord | null>(null);
  const [batchRun, setBatchRun] = useState<BatchFormatRun | null>(null);
  const [outputFiles, setOutputFiles] = useState<FileRecord[]>([]);
  const [outputError, setOutputError] = useState<string | null>(null);
  const [outputFormats, setOutputFormats] = useState<Record<OutputFormat, boolean>>({ docx: true, pdf: false });
  const [busy, setBusy] = useState<string | null>(null);
  const [ruleSearch, setRuleSearch] = useState("");
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all");

  const selectedProfileRef = useMemo(() => {
    if (!selectedProfile) return null;
    return { profile_id: selectedProfile.id, profile_version: selectedProfile.version };
  }, [selectedProfile]);

  const selectedOutputFormats = useMemo(
    () => (Object.entries(outputFormats).filter(([, enabled]) => enabled).map(([format]) => format) as OutputFormat[]),
    [outputFormats],
  );
  const stats = useMemo(() => coverageStats(profileDraft), [profileDraft]);
  const visibleCoverageItems = useMemo(
    () => filterCoverageItems(profileDraft, ruleSearch, coverageFilter),
    [profileDraft, ruleSearch, coverageFilter],
  );
  const activeLlmHealth = llmHealth ?? health?.services.llm_status ?? null;

  useEffect(() => {
    if (profileDraft && profileNeedsV2Defaults(profileDraft)) {
      setProfileDraft(cloneProfile(profileDraft));
    }
  }, [profileDraft]);

  useEffect(() => {
    apiClient
      .getHealth()
      .then((payload) => {
        setHealth(payload);
        setLlmHealth(payload.services.llm_status);
        setHealthError(null);
        if (payload.services.soffice_configured) setOutputFormats({ docx: true, pdf: true });
      })
      .catch((error: Error) => {
        setHealth(null);
        setHealthError(error.message);
      });
  }, []);

  const loadProfiles = async (nextKey?: string) => {
    setBusy("profiles");
    try {
      const summaries = await apiClient.listProfiles();
      setProfiles(summaries);
      setProfileError(null);
      const preferred = nextKey ?? selectedProfileKey ?? (summaries[0] ? profileKey(summaries[0].profile_id, summaries[0].current_version) : null);
      if (preferred) setSelectedProfileKey(preferred);
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile 加载失败。");
    } finally {
      setBusy(null);
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
        setConfirmProfileName(profile.name);
        setConfirmProfileVersion(profile.version);
        setConfirmProfileDescription(profile.description || "");
        setProfileError(null);
      })
      .catch((error: Error) => {
        setSelectedProfile(null);
        setProfileDraft(null);
        setProfileError(error.message);
      });
  }, [selectedProfileKey]);

  useEffect(() => {
    const ids = job?.output_file_ids ?? [];
    if (ids.length === 0) {
      setOutputFiles([]);
      return;
    }
    let cancelled = false;
    void Promise.allSettled(ids.map((id) => apiClient.getFile(id))).then((results) => {
      if (cancelled) return;
      const loaded: FileRecord[] = [];
      const failed: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "fulfilled") loaded.push(result.value);
        else failed.push(ids[index]);
      });
      setOutputFiles(loaded);
      setOutputError(failed.length ? `输出元数据加载失败：${failed.join(", ")}` : null);
    });
    return () => {
      cancelled = true;
    };
  }, [job?.output_file_ids]);

  const updateDraft = (mutator: (draft: FormatProfile) => void) => {
    setProfileDraft((current) => {
      if (!current) return current;
      const before = cloneProfile(current);
      const next = cloneProfile(current);
      mutator(next);
      next.schema_version = "2.0.0";
      markLockedCoverage(next, collectChangedPaths(before, next));
      return next;
    });
    setProfileMessage(null);
  };

  const createVisualDraft = () => {
    const source = selectedProfile ?? profileDraft;
    if (!source) {
      setProfileError("请先选择一个 Profile 作为起点。");
      return;
    }
    const draft = cloneProfile(source);
    draft.id = `profile_${Date.now()}`;
    draft.name = `${source.name} Copy`;
    draft.version = "0.1.0";
    draft.status = "draft";
    draft.source = "user";
    draft.schema_version = "2.0.0";
    draft.rule_evidence = [];
    draft.missing_fields = [];
    draft.unsupported_rules = [];
    setSelectedProfileKey(null);
    setSelectedProfile(null);
    setProfileDraft(draft);
    setConfirmProfileName(draft.name);
    setConfirmProfileVersion(draft.version);
    setConfirmProfileDescription(draft.description || "");
    setIntakeMode("visual");
    setProfileMessage("已创建可视化 Profile 草案。");
  };

  const createRequirementSession = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("requirement");
    setRequirementError(null);
    setProfileMessage(null);
    try {
      const session = await apiClient.createRequirementSession({
        source_type: "conversation",
        natural_language: requirementText,
        current_profile: profileDraft,
        locked_fields: profileDraft?.locked_fields ?? [],
      });
      applyRequirementSession(session);
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "Agent 分析失败。");
    } finally {
      setBusy(null);
    }
  };

  const uploadRuleAndAnalyze = async () => {
    if (!ruleFile) return;
    setBusy("rule-file");
    setRequirementError(null);
    try {
      const uploaded = await apiClient.uploadFile(ruleFile);
      setRuleFileRecord(uploaded);
      const session = await apiClient.createRequirementSession({
        source_type: "conversation",
        natural_language: requirementText || `请分析上传的${ruleFileKind === "style_sample_docx" ? "格式样本文档" : "格式规则文档"}，总结完整格式 JSON。`,
        attachments: [{ file_id: uploaded.file_id, source_kind: ruleFileKind, filename: uploaded.filename }],
        current_profile: profileDraft,
        locked_fields: profileDraft?.locked_fields ?? [],
      });
      applyRequirementSession(session);
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "格式文档分析失败。");
    } finally {
      setBusy(null);
    }
  };

  const sendRequirementMessage = async () => {
    if (!requirementSession || !requirementFollowUp.trim()) return;
    setBusy("requirement-message");
    setRequirementError(null);
    try {
      const session = await apiClient.addRequirementMessage(requirementSession.session_id, requirementFollowUp, {
        current_profile: profileDraft,
        locked_fields: profileDraft?.locked_fields ?? [],
      });
      setRequirementFollowUp("");
      applyRequirementSession(session);
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "补充规则失败。");
    } finally {
      setBusy(null);
    }
  };

  const applyRequirementSession = (session: RequirementSession) => {
    setRequirementSession(session);
    if (session.profile_draft) {
      setProfileDraft(cloneProfile(session.profile_draft));
      setConfirmProfileName(session.profile_draft.name);
      setConfirmProfileVersion(session.profile_draft.version);
      setConfirmProfileDescription(session.profile_draft.description || "");
    }
  };

  const confirmRequirementProfile = async () => {
    if (!requirementSession) return;
    setBusy("confirm-profile");
    setRequirementError(null);
    try {
      const session = await apiClient.confirmRequirementSession(requirementSession.session_id, {
        profile_name: confirmProfileName,
        profile_version: confirmProfileVersion,
        profile_description: confirmProfileDescription || null,
      });
      applyRequirementSession(session);
      const saved = session.profile_draft;
      if (saved) {
        setProfileMessage(`已保存 ${saved.name} v${saved.version}`);
        await loadProfiles(profileKey(saved.id, saved.version));
      }
    } catch (error) {
      setRequirementError(error instanceof Error ? error.message : "Profile 保存失败。");
    } finally {
      setBusy(null);
    }
  };

  const saveVisualProfile = async () => {
    if (!profileDraft) return;
    setBusy("save-profile");
    setProfileError(null);
    try {
      const draft = cloneProfile(profileDraft);
      draft.name = confirmProfileName || draft.name;
      draft.version = confirmProfileVersion || draft.version;
      draft.description = confirmProfileDescription || draft.description;
      draft.status = "active";
      draft.source = "user";
      draft.schema_version = "2.0.0";
      draft.version = await nextAvailableProfileVersion(draft.id, draft.version);
      const exists = profiles.some((profile) => profile.profile_id === draft.id);
      const saved = exists ? await apiClient.saveProfileVersion(draft) : await apiClient.saveProfile(draft);
      setProfileMessage(`已保存 ${saved.name} v${saved.version}`);
      await loadProfiles(profileKey(saved.id, saved.version));
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile 保存失败。");
    } finally {
      setBusy(null);
    }
  };

  const uploadTemplate = async () => {
    if (!templateFile) return;
    setBusy("template");
    try {
      const uploaded = await apiClient.uploadFile(templateFile);
      setTemplateFileRecord(uploaded);
      if (profileDraft) {
        updateDraft((draft) => {
          draft.template_binding.template_file_id = uploaded.file_id;
          draft.template_binding.template_name = uploaded.filename;
        });
      }
    } catch (error) {
      setOutputError(error instanceof Error ? error.message : "模板上传失败。");
    } finally {
      setBusy(null);
    }
  };

  const uploadInputs = async () => {
    if (inputFiles.length === 0) return;
    setBusy("inputs");
    setOutputError(null);
    try {
      const uploaded = await Promise.all(inputFiles.map((file) => apiClient.uploadFile(file)));
      setInputFileRecords(uploaded);
      setJob(null);
      setBatchRun(null);
      setOutputFiles([]);
    } catch (error) {
      setOutputError(error instanceof Error ? error.message : "待处理文档上传失败。");
    } finally {
      setBusy(null);
    }
  };

  const createJob = async () => {
    if (!selectedProfileRef || inputFileRecords.length === 0 || selectedOutputFormats.length === 0) return;
    setBusy("job");
    setOutputError(null);
    try {
      const created = await apiClient.createJob(inputFileRecords[0].file_id, selectedProfileRef, {
        template_file_id: templateFileRecord?.file_id ?? null,
        output_formats: selectedOutputFormats,
      });
      setJob(created);
      setBatchRun(null);
    } catch (error) {
      setOutputError(error instanceof Error ? error.message : "导出任务创建失败。");
    } finally {
      setBusy(null);
    }
  };

  const createBatch = async () => {
    if (!selectedProfileRef || inputFileRecords.length === 0 || selectedOutputFormats.length === 0) return;
    setBusy("batch");
    setOutputError(null);
    try {
      const created = await apiClient.createBatch({
        ...selectedProfileRef,
        template_file_id: templateFileRecord?.file_id ?? null,
        input_file_ids: inputFileRecords.map((file) => file.file_id),
        output_formats: selectedOutputFormats,
        auto_quality: true,
        auto_fix: true,
      });
      setBatchRun(created);
      setJob(null);
      setOutputFiles([]);
    } catch (error) {
      setOutputError(error instanceof Error ? error.message : "批量导出失败。");
    } finally {
      setBusy(null);
    }
  };

  const refreshJob = async () => {
    if (!job) return;
    setBusy("refresh-job");
    try {
      setJob(await apiClient.getJob(job.job_id));
    } finally {
      setBusy(null);
    }
  };

  const refreshBatch = async () => {
    if (!batchRun) return;
    setBusy("refresh-batch");
    try {
      setBatchRun(await apiClient.getBatch(batchRun.batch_id));
    } finally {
      setBusy(null);
    }
  };

  const checkLlmHealth = async () => {
    setBusy("llm-health");
    setHealthError(null);
    try {
      setLlmHealth(await apiClient.getLlmHealth());
    } catch (error) {
      setHealthError(error instanceof Error ? error.message : "LLM 检测失败。");
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="app-shell">
      <aside className="side-rail" aria-label="Perfect DOCX">
        <div className="brand-lockup">
          <div className="brand-mark"><FileText size={24} /></div>
          <div>
            <strong>Perfect DOCX</strong>
            <span>format compiler</span>
          </div>
        </div>

        <nav className="step-rail" aria-label="工作流">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <a href={`#${step.id}`} className="step-link" key={step.id}>
                <span>{index + 1}</span>
                <Icon size={18} />
                {step.label}
              </a>
            );
          })}
        </nav>

        <section className="runtime-panel">
          <div className="runtime-row">
            <span>API</span>
            <strong className={health ? "ok" : "bad"}>{health ? "online" : "offline"}</strong>
          </div>
          <div className="runtime-row">
            <span>LLM</span>
            <strong className={llmTone(activeLlmHealth)}>{llmLabel(activeLlmHealth)}</strong>
          </div>
          <button type="button" className="runtime-button" onClick={checkLlmHealth} disabled={busy === "llm-health"}>
            {busy === "llm-health" ? "checking..." : "检测 LLM"}
          </button>
          <p className={`runtime-note ${llmTone(activeLlmHealth)}`}>{llmDetail(activeLlmHealth)}</p>
          <div className="runtime-row">
            <span>PDF</span>
            <strong className={health?.services.soffice_configured ? "ok" : "bad"}>{health?.services.soffice_configured ? "ready" : "docx only"}</strong>
          </div>
          {healthError && <p className="rail-error">{healthError}</p>}
        </section>
      </aside>

      <section className="workbench">
        <header className="topbar">
          <div>
            <p className="eyebrow">Custom Word/PDF Export</p>
            <h1>自定义格式导出工作台</h1>
          </div>
          <button type="button" className="icon-button" onClick={() => void loadProfiles()} title="刷新 Profile">
            <RefreshCcw size={18} />
          </button>
        </header>

        <section className="command-center" aria-label="工作台总览">
          <article className="command-tile accent-agent">
            <div>
              <span>Agent Intake</span>
              <strong>LLM {llmLabel(activeLlmHealth)}</strong>
            </div>
            <small>{requirementSession ? `${requirementSession.status} · ${requirementSession.requirement_summary?.items.length ?? 0} rules` : llmDetail(activeLlmHealth)}</small>
          </article>
          <article className="command-tile">
            <div>
              <span>Profile JSON</span>
              <strong>{profileDraft ? `${profileDraft.name} v${profileDraft.version}` : "未选择"}</strong>
            </div>
            <small>{stats.locked} locked · {stats.evidence} evidence · {stats.missing} missing</small>
          </article>
          <article className="command-tile">
            <div>
              <span>Rule Coverage</span>
              <strong>{stats.total ? `${stats.supported}/${stats.total} supported` : "等待 Profile"}</strong>
            </div>
            <small>{stats.partial} partial · {stats.delegated} template · {stats.blocked} blocked</small>
          </article>
          <article className="command-tile accent-delivery">
            <div>
              <span>Export Gate</span>
              <strong>{job ? job.status : batchRun ? batchRun.status : "待导出"}</strong>
            </div>
            <small>{inputFileRecords.length} source · {selectedOutputFormats.join("+").toUpperCase() || "no output"} · {gatePassed(job?.delivery_gate_summary) ? "QC passed" : "QC pending"}</small>
          </article>
        </section>

        <section id="profile" className="workspace-grid profile-grid">
          <div className="panel primary-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Step 1</p>
                <h2>Profile 创建与选择</h2>
              </div>
              <button type="button" className="secondary-button" onClick={createVisualDraft}>
                <PencilRuler size={17} /> 新建草案
              </button>
            </div>

            <div className="segmented-control" aria-label="Profile 输入方式">
              <button type="button" className={intakeMode === "conversation" ? "active" : ""} onClick={() => setIntakeMode("conversation")}>
                <MessageSquareText size={16} /> 对话
              </button>
              <button type="button" className={intakeMode === "document" ? "active" : ""} onClick={() => setIntakeMode("document")}>
                <Upload size={16} /> 格式文档
              </button>
              <button type="button" className={intakeMode === "visual" ? "active" : ""} onClick={() => setIntakeMode("visual")}>
                <PencilRuler size={16} /> 可视化
              </button>
            </div>

            {intakeMode === "conversation" && (
              <form className="intake-form" onSubmit={createRequirementSession}>
                <textarea
                  value={requirementText}
                  onChange={(event) => setRequirementText(event.target.value)}
                  placeholder="正文宋体小四，英文 Times New Roman，字色黑色，1.5 倍行距，标题黑体三号居中..."
                />
                <div className="actions-row">
                  <button type="submit" disabled={busy === "requirement" || !requirementText.trim()}>
                    <MessageSquareText size={17} /> 让 Agent 拆解
                  </button>
                </div>
              </form>
            )}

            {intakeMode === "document" && (
              <div className="document-intake">
                <div className="source-kind-switch" aria-label="格式文档类型">
                  <label className={ruleFileKind === "rule_document" ? "selected" : ""}>
                    <input
                      type="radio"
                      name="rule-file-kind"
                      checked={ruleFileKind === "rule_document"}
                      onChange={() => setRuleFileKind("rule_document")}
                    />
                    <span>格式规则文档</span>
                    <small>学校/期刊的文字要求</small>
                  </label>
                  <label className={ruleFileKind === "style_sample_docx" ? "selected" : ""}>
                    <input
                      type="radio"
                      name="rule-file-kind"
                      checked={ruleFileKind === "style_sample_docx"}
                      onChange={() => setRuleFileKind("style_sample_docx")}
                    />
                    <span>格式样本文档</span>
                    <small>已经排好格式的 Word</small>
                  </label>
                </div>
                <textarea
                  value={requirementText}
                  onChange={(event) => setRequirementText(event.target.value)}
                  placeholder="可选补充：例如以正文格式为准，但页眉改为学院名称；或者要求 Agent 重点关注标题、页眉页脚、图表题注。"
                />
                <div className="file-strip">
                  <input type="file" accept=".doc,.docx" onChange={(event) => setRuleFile(event.target.files?.[0] ?? null)} />
                  <button type="button" onClick={uploadRuleAndAnalyze} disabled={!ruleFile || busy === "rule-file"}>
                    <Upload size={17} /> 分析并更新 Profile JSON
                  </button>
                  {ruleFileRecord && <span>{ruleFileRecord.filename}</span>}
                </div>
              </div>
            )}

            {intakeMode === "visual" && profileDraft && (
              <div className="visual-editor expanded">
                <section className="editor-section span-2">
                  <div className="editor-section-heading">
                    <span>Profile</span>
                    <strong>命名与版本</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      Profile 名称
                      <input value={confirmProfileName} onChange={(event) => setConfirmProfileName(event.target.value)} />
                    </label>
                    <label>
                      版本
                      <input value={confirmProfileVersion} onChange={(event) => setConfirmProfileVersion(event.target.value)} />
                    </label>
                    <label className="span-2">
                      描述
                      <input value={confirmProfileDescription} onChange={(event) => setConfirmProfileDescription(event.target.value)} placeholder="例如：华东师范大学本科毕业论文 v2026" />
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Page</span>
                    <strong>纸张、页边距与网格</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      纸张
                      <select value={profileDraft.page.size} onChange={(event) => updateDraft((draft) => { draft.page.size = event.target.value as "A4" | "Letter"; })}>
                        <option value="A4">A4</option>
                        <option value="Letter">Letter</option>
                      </select>
                    </label>
                    <label>
                      方向
                      <select value={profileDraft.page.orientation} onChange={(event) => updateDraft((draft) => { draft.page.orientation = event.target.value as "portrait" | "landscape"; })}>
                        <option value="portrait">纵向</option>
                        <option value="landscape">横向</option>
                      </select>
                    </label>
                    <label>
                      上边距 cm
                      <input type="number" step="0.1" value={profileDraft.page.margins_cm.top} onChange={(event) => updateDraft((draft) => { draft.page.margins_cm.top = Number(event.target.value); })} />
                    </label>
                    <label>
                      下边距 cm
                      <input type="number" step="0.1" value={profileDraft.page.margins_cm.bottom} onChange={(event) => updateDraft((draft) => { draft.page.margins_cm.bottom = Number(event.target.value); })} />
                    </label>
                    <label>
                      左边距 cm
                      <input type="number" step="0.1" value={profileDraft.page.margins_cm.left} onChange={(event) => updateDraft((draft) => { draft.page.margins_cm.left = Number(event.target.value); })} />
                    </label>
                    <label>
                      右边距 cm
                      <input type="number" step="0.1" value={profileDraft.page.margins_cm.right} onChange={(event) => updateDraft((draft) => { draft.page.margins_cm.right = Number(event.target.value); })} />
                    </label>
                    <label>
                      装订线 cm
                      <input type="number" step="0.1" value={profileDraft.page.margins_cm.gutter} onChange={(event) => updateDraft((draft) => { draft.page.margins_cm.gutter = Number(event.target.value); })} />
                    </label>
                    <label>
                      网格类型
                      <select value={profileDraft.document_grid.type} onChange={(event) => updateDraft((draft) => { draft.document_grid.type = event.target.value as "none" | "line" | "line_and_character"; draft.document_grid.enabled = event.target.value !== "none"; })}>
                        <option value="none">不启用</option>
                        <option value="line">只指定行网格</option>
                        <option value="line_and_character">行和字符网格</option>
                      </select>
                    </label>
                    <label>
                      每行字符
                      <input type="number" value={profileDraft.document_grid.characters_per_line ?? ""} onChange={(event) => updateDraft((draft) => { draft.document_grid.characters_per_line = event.target.value ? Number(event.target.value) : null; })} />
                    </label>
                    <label>
                      每页行数
                      <input type="number" value={profileDraft.document_grid.lines_per_page ?? ""} onChange={(event) => updateDraft((draft) => { draft.document_grid.lines_per_page = event.target.value ? Number(event.target.value) : null; })} />
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.document_grid.snap_to_grid} onChange={(event) => updateDraft((draft) => { draft.document_grid.snap_to_grid = event.target.checked; })} />
                      段落贴齐文档网格
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Body</span>
                    <strong>正文中英文格式</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      中文字体
                      <input value={profileDraft.body.font.chinese} onChange={(event) => updateDraft((draft) => { draft.body.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      英文字体
                      <input value={profileDraft.body.font.latin} onChange={(event) => updateDraft((draft) => { draft.body.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      字号 pt
                      <input type="number" step="0.5" value={profileDraft.body.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.body.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      字重
                      <select value={profileDraft.body.font.weight} onChange={(event) => updateDraft((draft) => { draft.body.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      字色
                      <input type="color" value={colorInputValue(profileDraft.body.font.color)} onChange={(event) => updateDraft((draft) => { draft.body.font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      对齐
                      <select value={profileDraft.body.alignment} onChange={(event) => updateDraft((draft) => { draft.body.alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="justified">两端对齐</option>
                        <option value="left">左对齐</option>
                        <option value="center">居中</option>
                        <option value="right">右对齐</option>
                      </select>
                    </label>
                    <label>
                      首行缩进 字符
                      <input type="number" step="0.5" value={profileDraft.body.first_line_indent_chars} onChange={(event) => updateDraft((draft) => { draft.body.first_line_indent_chars = Number(event.target.value); })} />
                    </label>
                    <label>
                      行距
                      <input type="number" step="0.1" value={profileDraft.body.line_spacing} onChange={(event) => updateDraft((draft) => { draft.body.line_spacing = Number(event.target.value); })} />
                    </label>
                    <label>
                      段前 pt
                      <input type="number" step="0.5" value={profileDraft.body.space_before_pt} onChange={(event) => updateDraft((draft) => { draft.body.space_before_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      段后 pt
                      <input type="number" step="0.5" value={profileDraft.body.space_after_pt} onChange={(event) => updateDraft((draft) => { draft.body.space_after_pt = Number(event.target.value); })} />
                    </label>
                  </div>
                </section>

                <section className="editor-section span-2">
                  <div className="editor-section-heading">
                    <span>Headings</span>
                    <strong>一级、二级、三级标题</strong>
                  </div>
                  <div className="heading-editor-list">
                    {[1, 2, 3].map((level) => {
                      const heading = profileDraft.headings.find((item) => item.level === level) ?? defaultHeading(profileDraft, level);
                      return (
                        <article className="heading-rule" key={level}>
                          <div className="heading-rule-title">
                            <strong>{level} 级标题</strong>
                            <span>{heading.numbering}</span>
                          </div>
                          <div className="editor-grid compact-grid">
                            <label>
                              中文字体
                              <input value={heading.font.chinese} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).font.chinese = event.target.value; })} />
                            </label>
                            <label>
                              英文字体
                              <input value={heading.font.latin} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).font.latin = event.target.value; })} />
                            </label>
                            <label>
                              字号 pt
                              <input type="number" step="0.5" value={heading.font.size_pt} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).font.size_pt = Number(event.target.value); })} />
                            </label>
                            <label>
                              字重
                              <select value={heading.font.weight} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).font.weight = event.target.value as TextFont["weight"]; })}>
                                <option value="normal">常规</option>
                                <option value="bold">加粗</option>
                              </select>
                            </label>
                            <label>
                              字色
                              <input type="color" value={colorInputValue(heading.font.color)} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).font.color = profileColorValue(event.target.value); })} />
                            </label>
                            <label>
                              对齐
                              <select value={heading.alignment} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                                <option value="left">左对齐</option>
                                <option value="center">居中</option>
                                <option value="right">右对齐</option>
                                <option value="justified">两端对齐</option>
                              </select>
                            </label>
                            <label>
                              编号样式
                              <input value={heading.numbering} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).numbering = event.target.value; })} placeholder="chapter / decimal / none" />
                            </label>
                            <label>
                              行距
                              <input type="number" step="0.1" value={heading.line_spacing ?? ""} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).line_spacing = event.target.value ? Number(event.target.value) : null; })} />
                            </label>
                            <label>
                              段前 pt
                              <input type="number" step="0.5" value={heading.space_before_pt} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).space_before_pt = Number(event.target.value); })} />
                            </label>
                            <label>
                              段后 pt
                              <input type="number" step="0.5" value={heading.space_after_pt} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).space_after_pt = Number(event.target.value); })} />
                            </label>
                            <label>
                              首行缩进 字符
                              <input type="number" step="0.5" value={heading.first_line_indent_chars} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).first_line_indent_chars = Number(event.target.value); })} />
                            </label>
                            <label className="switch-row">
                              <input type="checkbox" checked={heading.keep_with_next} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).keep_with_next = event.target.checked; })} />
                              与下段同页
                            </label>
                            <label className="switch-row">
                              <input type="checkbox" checked={heading.page_break_before} onChange={(event) => updateDraft((draft) => { ensureHeading(draft, level).page_break_before = event.target.checked; })} />
                              标题前分页
                            </label>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>TOC & List</span>
                    <strong>目录与序号</strong>
                  </div>
                  <div className="editor-grid">
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.toc.enabled} onChange={(event) => updateDraft((draft) => { draft.toc.enabled = event.target.checked; })} />
                      生成目录
                    </label>
                    <label>
                      目录标题
                      <input value={profileDraft.toc.title} onChange={(event) => updateDraft((draft) => { draft.toc.title = event.target.value; })} />
                    </label>
                    <label>
                      目录层级
                      <input type="number" value={profileDraft.toc.include_levels} onChange={(event) => updateDraft((draft) => { draft.toc.include_levels = Number(event.target.value); })} />
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.toc.show_page_numbers} onChange={(event) => updateDraft((draft) => { draft.toc.show_page_numbers = event.target.checked; })} />
                      显示页码
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.toc.right_align_page_numbers} onChange={(event) => updateDraft((draft) => { draft.toc.right_align_page_numbers = event.target.checked; })} />
                      页码右对齐
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.toc.update_fields_on_open} onChange={(event) => updateDraft((draft) => { draft.toc.update_fields_on_open = event.target.checked; })} />
                      打开时更新域
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.toc.use_hyperlinks} onChange={(event) => updateDraft((draft) => { draft.toc.use_hyperlinks = event.target.checked; })} />
                      目录超链接
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.numbering.enabled} onChange={(event) => updateDraft((draft) => { draft.numbering.enabled = event.target.checked; })} />
                      启用标题编号
                    </label>
                    <label>
                      标题编号模式
                      <input value={profileDraft.numbering.heading_pattern ?? ""} onChange={(event) => updateDraft((draft) => { draft.numbering.heading_pattern = event.target.value || null; })} placeholder="第%1章 / %1.%2" />
                    </label>
                    <label>
                      有序列表样式
                      <input value={profileDraft.list_numbering.ordered_pattern} onChange={(event) => updateDraft((draft) => { draft.list_numbering.ordered_pattern = event.target.value; })} placeholder="1. / (1) / 一、" />
                    </label>
                    <label>
                      无序列表符号
                      <input value={profileDraft.list_numbering.unordered_marker} onChange={(event) => updateDraft((draft) => { draft.list_numbering.unordered_marker = event.target.value; })} />
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.list_numbering.multilevel_enabled} onChange={(event) => updateDraft((draft) => { draft.list_numbering.multilevel_enabled = event.target.checked; })} />
                      多级列表
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.list_numbering.restart_per_section} onChange={(event) => updateDraft((draft) => { draft.list_numbering.restart_per_section = event.target.checked; })} />
                      列表按节重启
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.numbering.restart_per_section} onChange={(event) => updateDraft((draft) => { draft.numbering.restart_per_section = event.target.checked; })} />
                      标题按节重启
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Header</span>
                    <strong>页眉、页脚与页码</strong>
                  </div>
                  <div className="editor-grid">
                    <label className="span-2">
                      页眉文本
                      <input value={profileDraft.header_footer.header_text ?? ""} onChange={(event) => updateDraft((draft) => { draft.header_footer.header_text = event.target.value || null; })} />
                    </label>
                    <label className="span-2">
                      页脚文本
                      <input value={profileDraft.header_footer.footer_text ?? ""} onChange={(event) => updateDraft((draft) => { draft.header_footer.footer_text = event.target.value || null; })} />
                    </label>
                    <label>
                      页眉对齐
                      <select value={profileDraft.header_footer.header_alignment} onChange={(event) => updateDraft((draft) => { draft.header_footer.header_alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="left">左</option>
                        <option value="center">居中</option>
                        <option value="right">右</option>
                        <option value="justified">两端</option>
                      </select>
                    </label>
                    <label>
                      页脚对齐
                      <select value={profileDraft.header_footer.footer_alignment} onChange={(event) => updateDraft((draft) => { draft.header_footer.footer_alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="left">左</option>
                        <option value="center">居中</option>
                        <option value="right">右</option>
                        <option value="justified">两端</option>
                      </select>
                    </label>
                    <label>
                      页码格式
                      <select value={profileDraft.header_footer.page_number_format} onChange={(event) => updateDraft((draft) => { draft.header_footer.page_number_format = event.target.value as "arabic" | "roman_lower" | "roman_upper" | "none"; })}>
                        <option value="arabic">1, 2, 3</option>
                        <option value="roman_lower">i, ii, iii</option>
                        <option value="roman_upper">I, II, III</option>
                        <option value="none">无页码</option>
                      </select>
                    </label>
                    <label>
                      起始页码
                      <input type="number" value={profileDraft.header_footer.page_number_start} onChange={(event) => updateDraft((draft) => { draft.header_footer.page_number_start = Number(event.target.value); })} />
                    </label>
                    <label>
                      页眉页脚字体
                      <input value={profileDraft.header_footer.font.chinese} onChange={(event) => updateDraft((draft) => { draft.header_footer.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      页眉页脚英文字体
                      <input value={profileDraft.header_footer.font.latin} onChange={(event) => updateDraft((draft) => { draft.header_footer.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      字号 pt
                      <input type="number" step="0.5" value={profileDraft.header_footer.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.header_footer.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      字重
                      <select value={profileDraft.header_footer.font.weight} onChange={(event) => updateDraft((draft) => { draft.header_footer.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      字色
                      <input type="color" value={colorInputValue(profileDraft.header_footer.font.color)} onChange={(event) => updateDraft((draft) => { draft.header_footer.font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.header_footer.footer_page_number} onChange={(event) => updateDraft((draft) => { draft.header_footer.footer_page_number = event.target.checked; })} />
                      页脚显示页码
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.header_footer.different_first_page} onChange={(event) => updateDraft((draft) => { draft.header_footer.different_first_page = event.target.checked; })} />
                      首页不同
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.header_footer.different_odd_even} onChange={(event) => updateDraft((draft) => { draft.header_footer.different_odd_even = event.target.checked; })} />
                      奇偶页不同
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Tables</span>
                    <strong>表格与表名</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      表名位置
                      <select value={profileDraft.table.caption.position} onChange={(event) => updateDraft((draft) => { draft.table.caption.position = event.target.value as "above" | "below"; draft.table.enforce_caption_above = event.target.value === "above"; })}>
                        <option value="above">表格正上方</option>
                        <option value="below">表格下方</option>
                      </select>
                    </label>
                    <label>
                      中文前缀
                      <input value={profileDraft.table.caption.prefix} onChange={(event) => updateDraft((draft) => { draft.table.caption.prefix = event.target.value; })} />
                    </label>
                    <label>
                      英文前缀
                      <input value={profileDraft.table.caption.english_prefix ?? ""} onChange={(event) => updateDraft((draft) => { draft.table.caption.english_prefix = event.target.value || null; })} />
                    </label>
                    <label>
                      题注分隔符
                      <input value={profileDraft.table.caption.separator} onChange={(event) => updateDraft((draft) => { draft.table.caption.separator = event.target.value; })} placeholder="空格 / ： / -" />
                    </label>
                    <label>
                      编号范围
                      <select value={profileDraft.table.caption.numbering} onChange={(event) => updateDraft((draft) => { draft.table.caption.numbering = event.target.value as "continuous" | "chapter" | "section"; })}>
                        <option value="continuous">全文连续</option>
                        <option value="chapter">按章</option>
                        <option value="section">按节</option>
                      </select>
                    </label>
                    <label>
                      表名中文字体
                      <input value={profileDraft.table.caption.font.chinese} onChange={(event) => updateDraft((draft) => { draft.table.caption.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      表名英文字体
                      <input value={profileDraft.table.caption.font.latin} onChange={(event) => updateDraft((draft) => { draft.table.caption.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      表名字号 pt
                      <input type="number" step="0.5" value={profileDraft.table.caption.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.table.caption.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      表名字重
                      <select value={profileDraft.table.caption.font.weight} onChange={(event) => updateDraft((draft) => { draft.table.caption.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      表名字色
                      <input type="color" value={colorInputValue(profileDraft.table.caption.font.color)} onChange={(event) => updateDraft((draft) => { draft.table.caption.font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      表格线型
                      <select value={profileDraft.table.border_style} onChange={(event) => updateDraft((draft) => { draft.table.border_style = event.target.value as "three_line" | "full_grid" | "minimal" | "custom"; })}>
                        <option value="three_line">三线表</option>
                        <option value="full_grid">全框线</option>
                        <option value="minimal">极简线</option>
                        <option value="custom">自定义</option>
                      </select>
                    </label>
                    <label>
                      表注位置
                      <select value={profileDraft.table.notes_position} onChange={(event) => updateDraft((draft) => { draft.table.notes_position = event.target.value as "none" | "below" | "above"; })}>
                        <option value="none">无表注</option>
                        <option value="below">表格下方</option>
                        <option value="above">表格上方</option>
                      </select>
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.table.caption.bilingual} onChange={(event) => updateDraft((draft) => { draft.table.caption.bilingual = event.target.checked; })} />
                      中外文对照表名
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.table.header_repeat} onChange={(event) => updateDraft((draft) => { draft.table.header_repeat = event.target.checked; })} />
                      跨页重复表头
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.table.autofit} onChange={(event) => updateDraft((draft) => { draft.table.autofit = event.target.checked; })} />
                      自动适配页宽
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Figures</span>
                    <strong>插图与图名</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      图名位置
                      <select value={profileDraft.figure.caption.position} onChange={(event) => updateDraft((draft) => { draft.figure.caption.position = event.target.value as "above" | "below"; draft.figure.enforce_caption_below = event.target.value === "below"; })}>
                        <option value="below">图件正下方</option>
                        <option value="above">图件上方</option>
                      </select>
                    </label>
                    <label>
                      插图放置
                      <select value={profileDraft.figure.placement} onChange={(event) => updateDraft((draft) => { draft.figure.placement = event.target.value as "inline" | "floating" | "anchored"; })}>
                        <option value="inline">文中相应处直接给出</option>
                        <option value="anchored">锚定段落</option>
                        <option value="floating">浮动环绕</option>
                      </select>
                    </label>
                    <label>
                      中文前缀
                      <input value={profileDraft.figure.caption.prefix} onChange={(event) => updateDraft((draft) => { draft.figure.caption.prefix = event.target.value; })} />
                    </label>
                    <label>
                      英文前缀
                      <input value={profileDraft.figure.caption.english_prefix ?? ""} onChange={(event) => updateDraft((draft) => { draft.figure.caption.english_prefix = event.target.value || null; })} />
                    </label>
                    <label>
                      题注分隔符
                      <input value={profileDraft.figure.caption.separator} onChange={(event) => updateDraft((draft) => { draft.figure.caption.separator = event.target.value; })} placeholder="空格 / ： / -" />
                    </label>
                    <label>
                      编号范围
                      <select value={profileDraft.figure.caption.numbering} onChange={(event) => updateDraft((draft) => { draft.figure.caption.numbering = event.target.value as "continuous" | "chapter" | "section"; })}>
                        <option value="continuous">全文连续</option>
                        <option value="chapter">按章</option>
                        <option value="section">按节</option>
                      </select>
                    </label>
                    <label>
                      半栏图最大 mm
                      <input type="number" value={profileDraft.figure.half_column_max_mm} onChange={(event) => updateDraft((draft) => { draft.figure.half_column_max_mm = Number(event.target.value); })} />
                    </label>
                    <label>
                      通栏图最小 mm
                      <input type="number" value={profileDraft.figure.full_width_min_mm} onChange={(event) => updateDraft((draft) => { draft.figure.full_width_min_mm = Number(event.target.value); })} />
                    </label>
                    <label>
                      通栏图最大 mm
                      <input type="number" value={profileDraft.figure.full_width_max_mm} onChange={(event) => updateDraft((draft) => { draft.figure.full_width_max_mm = Number(event.target.value); })} />
                    </label>
                    <label>
                      图名中文字体
                      <input value={profileDraft.figure.caption.font.chinese} onChange={(event) => updateDraft((draft) => { draft.figure.caption.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      图名英文字体
                      <input value={profileDraft.figure.caption.font.latin} onChange={(event) => updateDraft((draft) => { draft.figure.caption.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      图名字号 pt
                      <input type="number" step="0.5" value={profileDraft.figure.caption.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.figure.caption.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      图名字重
                      <select value={profileDraft.figure.caption.font.weight} onChange={(event) => updateDraft((draft) => { draft.figure.caption.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      图名字色
                      <input type="color" value={colorInputValue(profileDraft.figure.caption.font.color)} onChange={(event) => updateDraft((draft) => { draft.figure.caption.font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.figure.caption.bilingual} onChange={(event) => updateDraft((draft) => { draft.figure.caption.bilingual = event.target.checked; })} />
                      中外文对照图名
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Academic</span>
                    <strong>摘要、公式、参考文献</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      摘要最少字数
                      <input type="number" value={profileDraft.abstract.length_range_chars.min} onChange={(event) => updateDraft((draft) => { draft.abstract.length_range_chars.min = Number(event.target.value); })} />
                    </label>
                    <label>
                      摘要最多字数
                      <input type="number" value={profileDraft.abstract.length_range_chars.max} onChange={(event) => updateDraft((draft) => { draft.abstract.length_range_chars.max = Number(event.target.value); })} />
                    </label>
                    <label>
                      摘要标题中文字体
                      <input value={profileDraft.abstract.title_font.chinese} onChange={(event) => updateDraft((draft) => { draft.abstract.title_font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      摘要标题英文字体
                      <input value={profileDraft.abstract.title_font.latin} onChange={(event) => updateDraft((draft) => { draft.abstract.title_font.latin = event.target.value; })} />
                    </label>
                    <label>
                      摘要标题字号 pt
                      <input type="number" step="0.5" value={profileDraft.abstract.title_font.size_pt} onChange={(event) => updateDraft((draft) => { draft.abstract.title_font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      摘要标题字重
                      <select value={profileDraft.abstract.title_font.weight} onChange={(event) => updateDraft((draft) => { draft.abstract.title_font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      摘要标题字色
                      <input type="color" value={colorInputValue(profileDraft.abstract.title_font.color)} onChange={(event) => updateDraft((draft) => { draft.abstract.title_font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      摘要正文中文字体
                      <input value={profileDraft.abstract.body_font.chinese} onChange={(event) => updateDraft((draft) => { draft.abstract.body_font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      摘要正文英文字体
                      <input value={profileDraft.abstract.body_font.latin} onChange={(event) => updateDraft((draft) => { draft.abstract.body_font.latin = event.target.value; })} />
                    </label>
                    <label>
                      摘要正文字号 pt
                      <input type="number" step="0.5" value={profileDraft.abstract.body_font.size_pt} onChange={(event) => updateDraft((draft) => { draft.abstract.body_font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      摘要正文字重
                      <select value={profileDraft.abstract.body_font.weight} onChange={(event) => updateDraft((draft) => { draft.abstract.body_font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      摘要正文字色
                      <input type="color" value={colorInputValue(profileDraft.abstract.body_font.color)} onChange={(event) => updateDraft((draft) => { draft.abstract.body_font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      公式字体
                      <input value={profileDraft.equations.font} onChange={(event) => updateDraft((draft) => { draft.equations.font = event.target.value; })} />
                    </label>
                    <label>
                      公式对齐
                      <select value={profileDraft.equations.alignment} onChange={(event) => updateDraft((draft) => { draft.equations.alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="center">居中</option>
                        <option value="left">左对齐</option>
                        <option value="right">右对齐</option>
                        <option value="justified">两端对齐</option>
                      </select>
                    </label>
                    <label>
                      公式编号
                      <select value={profileDraft.equations.numbering} onChange={(event) => updateDraft((draft) => { draft.equations.numbering = event.target.value as "none" | "left" | "right"; })}>
                        <option value="right">右侧编号</option>
                        <option value="left">左侧编号</option>
                        <option value="none">不编号</option>
                      </select>
                    </label>
                    <label>
                      参考文献格式
                      <input value={profileDraft.references.style} onChange={(event) => updateDraft((draft) => { draft.references.style = event.target.value; })} />
                    </label>
                    <label>
                      参考文献悬挂缩进
                      <input type="number" step="0.5" value={profileDraft.references.hanging_indent_chars} onChange={(event) => updateDraft((draft) => { draft.references.hanging_indent_chars = Number(event.target.value); })} />
                    </label>
                    <label>
                      参考文献中文字体
                      <input value={profileDraft.references.font.chinese} onChange={(event) => updateDraft((draft) => { draft.references.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      参考文献英文字体
                      <input value={profileDraft.references.font.latin} onChange={(event) => updateDraft((draft) => { draft.references.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      参考文献字号 pt
                      <input type="number" step="0.5" value={profileDraft.references.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.references.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      参考文献字重
                      <select value={profileDraft.references.font.weight} onChange={(event) => updateDraft((draft) => { draft.references.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      参考文献字色
                      <input type="color" value={colorInputValue(profileDraft.references.font.color)} onChange={(event) => updateDraft((draft) => { draft.references.font.color = profileColorValue(event.target.value); })} />
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Units</span>
                    <strong>计量、计价与一致性</strong>
                  </div>
                  <div className="editor-grid">
                    <label className="span-2">
                      计量单位
                      <input value={profileDraft.unit_rules.measurement_units.join("，")} onChange={(event) => updateDraft((draft) => { draft.unit_rules.measurement_units = splitCsv(event.target.value); })} placeholder="mm，cm，m，kg，s" />
                    </label>
                    <label className="span-2">
                      计价单位
                      <input value={profileDraft.unit_rules.currency_units.join("，")} onChange={(event) => updateDraft((draft) => { draft.unit_rules.currency_units = splitCsv(event.target.value); })} placeholder="元，万元，CNY，USD" />
                    </label>
                    <label>
                      数字与单位空格
                      <select value={profileDraft.unit_rules.unit_spacing} onChange={(event) => updateDraft((draft) => { draft.unit_rules.unit_spacing = event.target.value as "preserve" | "space" | "no_space"; })}>
                        <option value="preserve">保持原文</option>
                        <option value="space">统一加空格</option>
                        <option value="no_space">统一不加空格</option>
                      </select>
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.unit_rules.enforce_consistency} onChange={(event) => updateDraft((draft) => { draft.unit_rules.enforce_consistency = event.target.checked; })} />
                      检查单位一致性
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.unit_rules.use_si_symbols} onChange={(event) => updateDraft((draft) => { draft.unit_rules.use_si_symbols = event.target.checked; })} />
                      优先 SI 符号
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.unit_rules.normalize_fullwidth_numbers} onChange={(event) => updateDraft((draft) => { draft.unit_rules.normalize_fullwidth_numbers = event.target.checked; })} />
                      规范全角数字
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Notes</span>
                    <strong>脚注、尾注</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      中文字体
                      <input value={profileDraft.notes.font.chinese} onChange={(event) => updateDraft((draft) => { draft.notes.font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      英文字体
                      <input value={profileDraft.notes.font.latin} onChange={(event) => updateDraft((draft) => { draft.notes.font.latin = event.target.value; })} />
                    </label>
                    <label>
                      字号 pt
                      <input type="number" step="0.5" value={profileDraft.notes.font.size_pt} onChange={(event) => updateDraft((draft) => { draft.notes.font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      字重
                      <select value={profileDraft.notes.font.weight} onChange={(event) => updateDraft((draft) => { draft.notes.font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      字色
                      <input type="color" value={colorInputValue(profileDraft.notes.font.color)} onChange={(event) => updateDraft((draft) => { draft.notes.font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      行距
                      <input type="number" step="0.1" value={profileDraft.notes.line_spacing} onChange={(event) => updateDraft((draft) => { draft.notes.line_spacing = Number(event.target.value); })} />
                    </label>
                    <label>
                      段前 pt
                      <input type="number" step="0.5" value={profileDraft.notes.space_before_pt} onChange={(event) => updateDraft((draft) => { draft.notes.space_before_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      段后 pt
                      <input type="number" step="0.5" value={profileDraft.notes.space_after_pt} onChange={(event) => updateDraft((draft) => { draft.notes.space_after_pt = Number(event.target.value); })} />
                    </label>
                  </div>
                </section>

                <section className="editor-section">
                  <div className="editor-section-heading">
                    <span>Appendix</span>
                    <strong>附录标题与正文</strong>
                  </div>
                  <div className="editor-grid">
                    <label>
                      附录标题中文字体
                      <input value={profileDraft.appendix.title_font.chinese} onChange={(event) => updateDraft((draft) => { draft.appendix.title_font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      附录标题英文字体
                      <input value={profileDraft.appendix.title_font.latin} onChange={(event) => updateDraft((draft) => { draft.appendix.title_font.latin = event.target.value; })} />
                    </label>
                    <label>
                      标题字号 pt
                      <input type="number" step="0.5" value={profileDraft.appendix.title_font.size_pt} onChange={(event) => updateDraft((draft) => { draft.appendix.title_font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      标题字重
                      <select value={profileDraft.appendix.title_font.weight} onChange={(event) => updateDraft((draft) => { draft.appendix.title_font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      标题字色
                      <input type="color" value={colorInputValue(profileDraft.appendix.title_font.color)} onChange={(event) => updateDraft((draft) => { draft.appendix.title_font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      标题对齐
                      <select value={profileDraft.appendix.title_alignment} onChange={(event) => updateDraft((draft) => { draft.appendix.title_alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="left">左对齐</option>
                        <option value="center">居中</option>
                        <option value="right">右对齐</option>
                        <option value="justified">两端对齐</option>
                      </select>
                    </label>
                    <label>
                      附录正文中文字体
                      <input value={profileDraft.appendix.body_font.chinese} onChange={(event) => updateDraft((draft) => { draft.appendix.body_font.chinese = event.target.value; })} />
                    </label>
                    <label>
                      附录正文英文字体
                      <input value={profileDraft.appendix.body_font.latin} onChange={(event) => updateDraft((draft) => { draft.appendix.body_font.latin = event.target.value; })} />
                    </label>
                    <label>
                      正文字号 pt
                      <input type="number" step="0.5" value={profileDraft.appendix.body_font.size_pt} onChange={(event) => updateDraft((draft) => { draft.appendix.body_font.size_pt = Number(event.target.value); })} />
                    </label>
                    <label>
                      正文字重
                      <select value={profileDraft.appendix.body_font.weight} onChange={(event) => updateDraft((draft) => { draft.appendix.body_font.weight = event.target.value as TextFont["weight"]; })}>
                        <option value="normal">常规</option>
                        <option value="bold">加粗</option>
                      </select>
                    </label>
                    <label>
                      正文字色
                      <input type="color" value={colorInputValue(profileDraft.appendix.body_font.color)} onChange={(event) => updateDraft((draft) => { draft.appendix.body_font.color = profileColorValue(event.target.value); })} />
                    </label>
                    <label>
                      正文对齐
                      <select value={profileDraft.appendix.body_alignment} onChange={(event) => updateDraft((draft) => { draft.appendix.body_alignment = event.target.value as "left" | "center" | "right" | "justified"; })}>
                        <option value="justified">两端对齐</option>
                        <option value="left">左对齐</option>
                        <option value="center">居中</option>
                        <option value="right">右对齐</option>
                      </select>
                    </label>
                    <label>
                      正文行距
                      <input type="number" step="0.1" value={profileDraft.appendix.body_line_spacing} onChange={(event) => updateDraft((draft) => { draft.appendix.body_line_spacing = Number(event.target.value); })} />
                    </label>
                    <label>
                      正文首行缩进 字符
                      <input type="number" step="0.5" value={profileDraft.appendix.body_first_line_indent_chars} onChange={(event) => updateDraft((draft) => { draft.appendix.body_first_line_indent_chars = Number(event.target.value); })} />
                    </label>
                  </div>
                </section>

                <section className="editor-section span-2">
                  <div className="editor-section-heading">
                    <span>Gate</span>
                    <strong>内部校验与模板适配</strong>
                  </div>
                  <div className="editor-grid gate-grid">
                    <label>
                      模板正文槽位
                      <input value={profileDraft.template_binding.body_slot ?? ""} onChange={(event) => updateDraft((draft) => { draft.template_binding.body_slot = event.target.value || null; })} placeholder="{{BODY}}" />
                    </label>
                    <label>
                      占位符策略
                      <select value={profileDraft.template_binding.placeholder_policy} onChange={(event) => updateDraft((draft) => { draft.template_binding.placeholder_policy = event.target.value as "fail" | "preserve" | "remove"; })}>
                        <option value="fail">缺失则失败</option>
                        <option value="preserve">保留占位符</option>
                        <option value="remove">删除占位符</option>
                      </select>
                    </label>
                    <label>
                      校验严格度
                      <select value={profileDraft.quality.strictness} onChange={(event) => updateDraft((draft) => { draft.quality.strictness = event.target.value as "lenient" | "standard" | "strict"; })}>
                        <option value="lenient">宽松</option>
                        <option value="standard">标准</option>
                        <option value="strict">严格</option>
                      </select>
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.template_binding.inherit_header_footer} onChange={(event) => updateDraft((draft) => { draft.template_binding.inherit_header_footer = event.target.checked; })} />
                      继承模板页眉页脚
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.delivery_gate.require_internal_qc} onChange={(event) => updateDraft((draft) => { draft.delivery_gate.require_internal_qc = event.target.checked; })} />
                      导出前内部校验
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.delivery_gate.allow_auto_fix} onChange={(event) => updateDraft((draft) => { draft.delivery_gate.allow_auto_fix = event.target.checked; })} />
                      允许自动二次修复
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.delivery_gate.require_pdf_inspection} onChange={(event) => updateDraft((draft) => { draft.delivery_gate.require_pdf_inspection = event.target.checked; })} />
                      PDF 产物检查
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.delivery_gate.fail_on_unsupported_rules} onChange={(event) => updateDraft((draft) => { draft.delivery_gate.fail_on_unsupported_rules = event.target.checked; })} />
                      不支持规则时阻断导出
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.enabled} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.enabled = event.target.checked; })} />
                      最终 LLM 版面检查
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.required} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.required = event.target.checked; })} />
                      LLM 不可用时阻断
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.check_garbled_text} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.check_garbled_text = event.target.checked; })} />
                      检查乱码
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.check_blank_pages} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.check_blank_pages = event.target.checked; })} />
                      检查异常空白页
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.check_overlap} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.check_overlap = event.target.checked; })} />
                      检查重叠错位
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.llm_final_review.check_table_figure_overflow} onChange={(event) => updateDraft((draft) => { draft.llm_final_review.check_table_figure_overflow = event.target.checked; })} />
                      检查图表出界
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.quality.check_margins} onChange={(event) => updateDraft((draft) => { draft.quality.check_margins = event.target.checked; })} />
                      检查页边距
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.quality.check_fonts} onChange={(event) => updateDraft((draft) => { draft.quality.check_fonts = event.target.checked; })} />
                      检查字体
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.quality.check_line_spacing} onChange={(event) => updateDraft((draft) => { draft.quality.check_line_spacing = event.target.checked; })} />
                      检查行距
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.quality.check_headings} onChange={(event) => updateDraft((draft) => { draft.quality.check_headings = event.target.checked; })} />
                      检查标题
                    </label>
                    <label className="switch-row">
                      <input type="checkbox" checked={profileDraft.quality.check_references} onChange={(event) => updateDraft((draft) => { draft.quality.check_references = event.target.checked; })} />
                      检查参考文献
                    </label>
                  </div>
                </section>
              </div>
            )}

            {requirementSession && (
              <section className="agent-result" aria-live="polite">
                <div className="result-heading">
                  <strong>{requirementSession.status}</strong>
                  <span>{requirementSession.requirement_summary?.items.length ?? 0} rules</span>
                  <span>{requirementSession.missing_fields.length} missing</span>
                  <span>{requirementSession.uncertain_items.length} uncertain</span>
                </div>
                <div className="rule-list">
                  {(requirementSession.requirement_summary?.items ?? []).map((item) => (
                    <article className="rule-row" key={`${item.field_path}-${item.value}`}>
                      <span>{item.field_path}</span>
                      <strong>{item.value}</strong>
                    </article>
                  ))}
                </div>
                <textarea
                  className="followup-box"
                  value={requirementFollowUp}
                  onChange={(event) => setRequirementFollowUp(event.target.value)}
                  placeholder="补充缺失规则，例如：页眉为学校名称，页码底端居中。"
                />
                <div className="actions-row">
                  <button type="button" className="secondary-button" onClick={sendRequirementMessage} disabled={!requirementFollowUp.trim() || busy === "requirement-message"}>
                    继续补充
                  </button>
                  <button type="button" onClick={confirmRequirementProfile} disabled={!requirementSession.profile_draft || busy === "confirm-profile"}>
                    <Save size={17} /> 保存 Profile
                  </button>
                </div>
              </section>
            )}

            {requirementError && <p className="error-text"><AlertCircle size={16} /> {requirementError}</p>}
            {profileError && <p className="error-text"><AlertCircle size={16} /> {profileError}</p>}
            {profileMessage && <p className="success-text"><CheckCircle2 size={16} /> {profileMessage}</p>}
          </div>

          <aside className="panel profile-panel">
            <div className="panel-heading compact">
              <h3>当前 Profile</h3>
              <span>{busy === "profiles" ? "loading" : `${profiles.length} profiles`}</span>
            </div>
            <select value={selectedProfileKey ?? ""} onChange={(event) => setSelectedProfileKey(event.target.value || null)}>
              <option value="">选择 Profile</option>
              {profiles.map((profile) => (
                <option value={profileKey(profile.profile_id, profile.current_version)} key={profileKey(profile.profile_id, profile.current_version)}>
                  {profile.name} v{profile.current_version}
                </option>
              ))}
            </select>
            {profileDraft && (
              <div className="profile-snapshot">
                <h3>{profileDraft.name}</h3>
                <dl>
                  <div><dt>schema</dt><dd>{profileDraft.schema_version}</dd></div>
                  <div><dt>paper</dt><dd>{profileDraft.page.size} / {profileDraft.page.orientation}</dd></div>
                  <div><dt>body</dt><dd>{profileDraft.body.font.chinese} {profileDraft.body.font.size_pt}pt</dd></div>
                  <div><dt>color</dt><dd>#{profileDraft.body.font.color}</dd></div>
                  <div><dt>gate</dt><dd>{profileDraft.delivery_gate.require_internal_qc ? "internal" : "off"}</dd></div>
                </dl>
                <textarea value={confirmProfileDescription} onChange={(event) => setConfirmProfileDescription(event.target.value)} placeholder="Profile 描述" />
                <button type="button" onClick={saveVisualProfile} disabled={busy === "save-profile"}>
                  <Save size={17} /> 保存当前草案
                </button>
              </div>
            )}
            {profileDraft && (
              <section className="coverage-panel">
                <div className="panel-heading compact inspector-heading">
                  <div>
                    <h3><ListChecks size={16} /> 规则检查器</h3>
                    <span>{visibleCoverageItems.length}/{stats.total} fields · {stats.evidence} evidence</span>
                  </div>
                  <b className={stats.blocked ? "inspector-badge blocked" : "inspector-badge"}>{stats.blocked ? `${stats.blocked} blocked` : "ready"}</b>
                </div>
                <div className="coverage-meter" aria-label="规则支持度">
                  <span style={{ width: stats.total ? `${Math.max(4, (stats.supported / stats.total) * 100)}%` : "0%" }} />
                </div>
                <label className="rule-search">
                  <Search size={15} />
                  <input value={ruleSearch} onChange={(event) => setRuleSearch(event.target.value)} placeholder="搜索字段、状态、来源，例如 body.font.color" />
                </label>
                <div className="coverage-filter-tabs" aria-label="规则过滤">
                  {(["all", "supported", "partial", "unsupported", "locked", "missing", "evidence"] as CoverageFilter[]).map((filter) => (
                    <button
                      type="button"
                      className={coverageFilter === filter ? "active" : ""}
                      onClick={() => setCoverageFilter(filter)}
                      key={filter}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
                <div className="coverage-breakdown">
                  <span>{stats.supported} supported</span>
                  <span>{stats.partial} partial</span>
                  <span>{stats.delegated} template</span>
                  <span>{stats.unsupported} unsupported</span>
                  <span>{stats.locked} locked</span>
                  <span>{stats.missing} missing</span>
                </div>
                <div className="coverage-list inspector-list">
                  {visibleCoverageItems.length === 0 ? (
                    <span className="empty-hint">没有匹配的规则。Profile 保存或 Agent 分析后会显示字段级支持状态。</span>
                  ) : (
                    visibleCoverageItems.map((item) => {
                      const evidence = evidenceForField(profileDraft, item.field_path);
                      const unsupported = unsupportedForField(profileDraft, item.field_path);
                      return (
                        <article className="coverage-row inspector-row" key={item.field_path}>
                          <div className="inspector-row-main">
                            <div className="inspector-title-line">
                              <strong>{item.field_path}</strong>
                              <div className="coverage-tags">
                                {item.locked_by_user && <em>locked</em>}
                                <b className={`coverage-pill ${coverageTone(item)}`}>{coverageLabel(item)}</b>
                              </div>
                            </div>
                            <div className="rule-status-grid">
                              <span>Agent <b>{item.agent}</b></span>
                              <span>Formatter <b>{item.formatter}</b></span>
                              <span>QC <b>{item.qc}</b></span>
                              <span>LLM <b>{item.llm_final_review}</b></span>
                            </div>
                            <p>{item.note || `来源：${item.source}；不支持策略：${item.unsupported_behavior}`}</p>
                            {evidence.length > 0 && (
                              <div className="evidence-list">
                                {evidence.slice(0, 3).map((entry, index) => (
                                  <span key={`${entry.field_path}-${index}`}>
                                    {entry.source} · {confidenceLabel(entry.confidence)}
                                    {entry.quote ? ` · ${entry.quote}` : entry.note ? ` · ${entry.note}` : ""}
                                  </span>
                                ))}
                              </div>
                            )}
                            {unsupported.length > 0 && (
                              <div className="unsupported-list">
                                {unsupported.map((entry, index) => (
                                  <span key={`${entry.field_path}-${index}`}>{entry.field_path}: {entry.message}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </article>
                      );
                    })
                  )}
                </div>
                {profileDraft.missing_fields.length > 0 && (
                  <details className="inspector-details">
                    <summary>缺失字段 · {profileDraft.missing_fields.length}</summary>
                    <div className="field-chip-list">
                      {profileDraft.missing_fields.map((field) => <span key={field}>{field}</span>)}
                    </div>
                  </details>
                )}
                {profileDraft.unsupported_rules.length > 0 && (
                  <details className="inspector-details" open={stats.blocked > 0}>
                    <summary>不支持/不确定规则 · {profileDraft.unsupported_rules.length}</summary>
                    <div className="unsupported-list">
                      {profileDraft.unsupported_rules.map((rule, index) => (
                        <span key={`${rule.field_path}-${index}`}>{rule.field_path}: {rule.message}{rule.suggestion ? `；建议：${rule.suggestion}` : ""}</span>
                      ))}
                    </div>
                  </details>
                )}
                {profileDraft.source_documents.length > 0 && (
                  <details className="inspector-details">
                    <summary>来源文档 · {profileDraft.source_documents.length}</summary>
                    <div className="source-doc-list">
                      {profileDraft.source_documents.map((source, index) => (
                        <span key={`${source.file_id ?? source.filename}-${index}`}>
                          {source.source_kind} · {source.filename || source.note || "unnamed"}
                        </span>
                      ))}
                    </div>
                  </details>
                )}
                <details className="json-inspector">
                  <summary><Braces size={15} /> Profile JSON</summary>
                  <pre>{JSON.stringify(profileDraft, null, 2)}</pre>
                </details>
              </section>
            )}
          </aside>
        </section>

        <section id="template" className="panel strip-panel">
          <div>
            <p className="eyebrow">Step 2</p>
            <h2>模板绑定</h2>
          </div>
          <div className="file-strip">
            <input type="file" accept=".doc,.docx" onChange={(event) => setTemplateFile(event.target.files?.[0] ?? null)} />
            <button type="button" className="secondary-button" onClick={uploadTemplate} disabled={!templateFile || busy === "template"}>
              <Layers3 size={17} /> 上传模板
            </button>
            {templateFileRecord ? <span>{templateFileRecord.filename}</span> : <span>无模板</span>}
          </div>
        </section>

        <section id="source" className="panel strip-panel">
          <div>
            <p className="eyebrow">Step 3</p>
            <h2>待处理文档</h2>
          </div>
          <div className="file-strip">
            <input type="file" multiple accept=".doc,.docx" onChange={(event) => setInputFiles(Array.from(event.target.files ?? []))} />
            <button type="button" onClick={uploadInputs} disabled={inputFiles.length === 0 || busy === "inputs"}>
              <Upload size={17} /> 上传文档
            </button>
            <span>{inputFileRecords.length ? `${inputFileRecords.length} files ready` : "未上传"}</span>
          </div>
        </section>

        <section id="delivery" className="workspace-grid delivery-grid">
          <div className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Step 4</p>
                <h2>导出</h2>
              </div>
              <ShieldCheck className={gatePassed(job?.delivery_gate_summary) ? "gate-ok" : "gate-idle"} size={24} />
            </div>

            <div className="format-toggles">
              <label>
                <input
                  type="checkbox"
                  checked={outputFormats.docx}
                  onChange={(event) => setOutputFormats((current) => ({ ...current, docx: event.target.checked }))}
                />
                DOCX
              </label>
              <label className={!health?.services.soffice_configured ? "disabled" : ""}>
                <input
                  type="checkbox"
                  checked={outputFormats.pdf}
                  disabled={!health?.services.soffice_configured}
                  onChange={(event) => setOutputFormats((current) => ({ ...current, pdf: event.target.checked }))}
                />
                PDF
              </label>
            </div>

            <div className="actions-row">
              <button type="button" onClick={createBatch} disabled={!selectedProfileRef || inputFileRecords.length === 0 || busy === "batch"}>
                <FolderOpen size={17} /> 批量导出
              </button>
              <button type="button" className="secondary-button" onClick={createJob} disabled={!selectedProfileRef || inputFileRecords.length === 0 || busy === "job"}>
                <FileText size={17} /> 单文件导出
              </button>
            </div>

            {job && (
              <section className="status-block">
                <div>
                  <strong>{job.status}</strong>
                  <span>{job.current_step}</span>
                </div>
                <button type="button" className="icon-button" onClick={refreshJob} title="刷新任务">
                  <RefreshCcw size={16} />
                </button>
                {job.error_message && <p className="error-text"><AlertCircle size={16} /> {job.error_message}</p>}
                {outputFiles.length > 0 && (
                  <div className="download-list">
                    {outputFiles.map((file) => (
                      <a className="download-link" href={apiClient.downloadFileUrl(file.file_id)} key={file.file_id} download>
                        <Download size={16} /> {outputKind(file)} · {file.filename}
                      </a>
                    ))}
                  </div>
                )}
              </section>
            )}

            {batchRun && (
              <section className="status-block">
                <div>
                  <strong>{batchRun.status}</strong>
                  <span>{batchRun.batch_id}</span>
                </div>
                <button type="button" className="icon-button" onClick={refreshBatch} title="刷新批量任务">
                  <RefreshCcw size={16} />
                </button>
                <div className="delivery-list">
                  {batchRun.items.map((item) => (
                    <DeliveryItem item={item} key={item.job_id} />
                  ))}
                </div>
                {batchRun.manifest_download_url && (
                  <a className="download-link secondary-download" href={apiClient.downloadBatchManifestUrl(batchRun.batch_id)} download>
                    <Download size={16} /> manifest
                  </a>
                )}
              </section>
            )}

            {outputError && <p className="error-text"><AlertCircle size={16} /> {outputError}</p>}
          </div>

          <aside className="panel inventory-panel">
            <h3>上传队列</h3>
            <div className="mini-list">
              {inputFileRecords.length === 0 ? (
                <span>empty</span>
              ) : (
                inputFileRecords.map((file) => (
                  <div className="mini-row" key={file.file_id}>
                    <FileText size={15} />
                    <span>{file.filename}</span>
                    <small>{formatFileSize(file.size)}</small>
                  </div>
                ))
              )}
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}

function DeliveryItem({ item }: { item: DeliveryManifestItem }) {
  return (
    <article className={`delivery-item ${item.delivery_status}`}>
      <div>
        <strong>{deliveryLabel(item)}</strong>
        <span>{item.failure_reason || item.job_id}</span>
      </div>
      <div className="download-list compact-downloads">
        {item.final_docx_file_id && (
          <a className="download-link" href={apiClient.downloadFileUrl(item.final_docx_file_id)} download>
            <Download size={15} /> DOCX
          </a>
        )}
        {item.final_pdf_file_id && (
          <a className="download-link" href={apiClient.downloadFileUrl(item.final_pdf_file_id)} download>
            <Download size={15} /> PDF
          </a>
        )}
      </div>
    </article>
  );
}

export default App;
