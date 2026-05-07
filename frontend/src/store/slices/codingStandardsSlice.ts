import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  AnalysisSummary,
  Branch,
  FileEntry,
  FixAllResponse,
  Language,
  Violation,
} from '@/types';

interface CodingStandardsState {
  // ── Editor state ──
  language: Language;
  code: string;

  // ── Analysis state ──
  analyzing: boolean;
  fixing: boolean;
  violations: Violation[] | null;
  summary: AnalysisSummary | null;

  // ── Fix-all result ──
  fixResult: FixAllResponse | null;
  showDiff: boolean;
  autoAnalyze: boolean;

  // ── Repo browser ──
  repoUrl: string;
  repoLoading: boolean;
  repoFiles: Record<string, FileEntry> | null;
  repoPath: string | null;
  activeRepoFile: string | null;

  // ── Branches ──
  branches: Branch[];
  selectedBranch: string;
  branchesLoading: boolean;

  // ── UI ──
  error: string | null;
}

const initialState: CodingStandardsState = {
  language: 'python',
  code: '',
  analyzing: false,
  fixing: false,
  violations: null,
  summary: null,
  fixResult: null,
  showDiff: false,
  autoAnalyze: false,
  repoUrl: '',
  repoLoading: false,
  repoFiles: null,
  repoPath: null,
  activeRepoFile: null,
  branches: [],
  selectedBranch: '',
  branchesLoading: false,
  error: null,
};

const slice = createSlice({
  name: 'codingStandards',
  initialState,
  reducers: {
    setLanguage(state, { payload }: PayloadAction<Language>) {
      state.language = payload;
    },
    setCode(state, { payload }: PayloadAction<string>) {
      state.code = payload;
    },
    setAutoAnalyze(state, { payload }: PayloadAction<boolean>) {
      state.autoAnalyze = payload;
    },

    // ── Analysis ──
    analyzeStart(state) {
      state.analyzing = true;
      state.fixResult = null;
      state.showDiff = false;
    },
    analyzeSuccess(
      state,
      {
        payload,
      }: PayloadAction<{ violations: Violation[]; summary: AnalysisSummary }>,
    ) {
      state.analyzing = false;
      state.violations = payload.violations;
      state.summary = payload.summary;
    },
    analyzeFailure(state, { payload }: PayloadAction<string>) {
      state.analyzing = false;
      state.error = payload;
    },
    clearAnalysis(state) {
      state.violations = null;
      state.summary = null;
      state.fixResult = null;
      state.showDiff = false;
    },

    // ── Fix-all ──
    fixStart(state) {
      state.fixing = true;
    },
    fixSuccess(state, { payload }: PayloadAction<FixAllResponse>) {
      state.fixing = false;
      state.fixResult = payload;
      state.showDiff = true;
    },
    fixFailure(state, { payload }: PayloadAction<string>) {
      state.fixing = false;
      state.error = payload;
    },
    applyFix(state) {
      if (state.fixResult?.fixed_code) {
        state.code = state.fixResult.fixed_code;
        state.violations = [];
        state.summary = null;
        state.fixResult = null;
        state.showDiff = false;
      }
    },
    setShowDiff(state, { payload }: PayloadAction<boolean>) {
      state.showDiff = payload;
    },

    // ── Repo ──
    setRepoUrl(state, { payload }: PayloadAction<string>) {
      state.repoUrl = payload;
    },
    repoLoadStart(state) {
      state.repoLoading = true;
      state.repoFiles = null;
      state.activeRepoFile = null;
    },
    repoLoadSuccess(
      state,
      {
        payload,
      }: PayloadAction<{
        files: Record<string, FileEntry>;
        repoPath: string;
      }>,
    ) {
      state.repoLoading = false;
      state.repoFiles = payload.files;
      state.repoPath = payload.repoPath;
    },
    repoLoadFailure(state, { payload }: PayloadAction<string>) {
      state.repoLoading = false;
      state.error = payload;
    },
    closeRepo(state) {
      state.repoFiles = null;
      state.activeRepoFile = null;
      state.repoPath = null;
      state.branches = [];
      state.selectedBranch = '';
    },
    openFile(
      state,
      {
        payload,
      }: PayloadAction<{ path: string; content: string; language: Language }>,
    ) {
      state.activeRepoFile = payload.path;
      state.code = payload.content;
      state.language = payload.language;
      state.violations = null;
      state.summary = null;
      state.fixResult = null;
      state.showDiff = false;
    },

    // ── Branches ──
    branchesLoadStart(state) {
      state.branchesLoading = true;
    },
    branchesLoaded(state, { payload }: PayloadAction<Branch[]>) {
      state.branchesLoading = false;
      state.branches = payload;
      if (!state.selectedBranch && payload.length > 0) {
        state.selectedBranch = payload[0].name;
      }
    },
    branchesFailed(state) {
      state.branchesLoading = false;
    },
    setSelectedBranch(state, { payload }: PayloadAction<string>) {
      state.selectedBranch = payload;
    },

    clearError(state) {
      state.error = null;
    },
  },
});

export const codingStandardsActions = slice.actions;
export default slice.reducer;
