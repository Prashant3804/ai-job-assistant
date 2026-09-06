const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (netErr: any) {
    const currentOrigin = typeof window !== 'undefined' ? window.location.origin : 'client';
    throw new Error(
      `Unable to connect to backend server at ${API_BASE}. Please verify that the backend is running and CORS is configured for ${currentOrigin}. Error: ${netErr?.message || 'Network connection failed'}`
    );
  }

  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const err = await res.json();
      errorMsg = err.detail || err.message || errorMsg;
    } catch (_) {}

    if (res.status === 401) {
      errorMsg = 'Authentication required. Please log in or refresh your session.';
    } else if (res.status === 403) {
      errorMsg = 'Access forbidden. You do not have permission for this resource.';
    } else if (res.status === 404) {
      errorMsg = `Resource not found at ${endpoint}.`;
    } else if (res.status === 429) {
      errorMsg = 'Rate limit exceeded. Please try again in a few moments.';
    } else if (res.status >= 500) {
      errorMsg = `Backend server error (${res.status}): ${errorMsg}`;
    }

    throw new Error(errorMsg);
  }

  return res.json();
}

// API Service Functions
export const api = {
  // Auth
  getMe: () => fetchApi<any>('/auth/me'),
  updatePreferences: (data: any) => fetchApi<any>('/auth/preferences', { method: 'PUT', body: JSON.stringify(data) }),

  // Dashboard & Analytics
  getDashboard: () => fetchApi<any>('/analytics/dashboard'),
  getPlatformStats: () => fetchApi<any>('/auto-apply/platforms/stats'),

  // Jobs & Discovery Engine (Phase 3)
  getJobs: (params?: Record<string, string>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any>(`/jobs${query ? `?${query}` : ''}`);
  },
  getJobById: (id: string) => fetchApi<any>(`/jobs/${id}`),
  getConnectorsStatus: () => fetchApi<any>('/jobs/connectors'),
  triggerJobSync: () => fetchApi<any>('/jobs/sync', { method: 'POST' }),

  // AI Matching Engine (Phase 4)
  getMatchingHealth: () => fetchApi<any>('/matching/health'),
  getRecommendations: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any>(`/matching/recommended${query ? `?${query}` : ''}`);
  },
  getRecommendedJobs: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any>(`/matching/recommended${query ? `?${query}` : ''}`);
  },
  getMatchHistory: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any>(`/matching/matches${query ? `?${query}` : ''}`);
  },
  getJobMatch: (jobId: string) => fetchApi<any>(`/matching/jobs/${jobId}`),
  matchJob: (jobId: string, payload?: any) =>
    fetchApi<any>(`/matching/jobs/${jobId}`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  batchMatch: (payload?: any) =>
    fetchApi<any>('/matching/batch', { method: 'POST', body: JSON.stringify(payload || {}) }),
  toggleBookmark: (jobId: string) => fetchApi<any>(`/matching/jobs/${jobId}/bookmark`, { method: 'POST' }),

  // Applications & Automated Application Engine (Phase 6)
  getApplications: (params?: string | { status?: string; source?: string; time_range?: string; limit?: number; offset?: number }) => {
    if (typeof params === 'string') {
      return fetchApi<any>(`/applications?status=${params}`);
    }
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.source) query.append('source', params.source);
    if (params?.time_range) query.append('time_range', params.time_range);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));
    const qs = query.toString();
    return fetchApi<any>(`/applications${qs ? `?${qs}` : ''}`);
  },
  getApplicationDetails: (id: string) => fetchApi<any>(`/applications/${id}`),
  getApplicationStatistics: () => fetchApi<any>('/applications/statistics'),
  getApplicationEvents: (id: string) => fetchApi<any>(`/applications/${id}/events`),
  getApplicationAttempts: (id: string) => fetchApi<any>(`/applications/${id}/attempts`),
  createApplication: (data: any) => fetchApi<any>('/applications', { method: 'POST', body: JSON.stringify(data) }),
  updateApplicationStatus: (id: string, status: string, notes?: string) =>
    fetchApi<any>(`/applications/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status, notes }) }),

  // Auto-Apply Engine (Phase 6)
  getAutoApplyPolicy: () => fetchApi<any>('/auto-apply/policy'),
  updateAutoApplyPolicy: (data: any) => fetchApi<any>('/auto-apply/policy', { method: 'PUT', body: JSON.stringify(data) }),
  getAutoApplyStatus: () => fetchApi<any>('/auto-apply/status'),
  getAutoApplyQueue: (status?: string) => fetchApi<any>(`/auto-apply/queue${status ? `?status=${status}` : ''}`),
  triggerAutoApplyForJob: (jobId: string, immediate = true) =>
    fetchApi<any>(`/auto-apply/jobs/${jobId}?immediate=${immediate}`, { method: 'POST' }),
  processApplicationQueue: (batchSize = 5) =>
    fetchApi<any>(`/auto-apply/process-queue?batch_size=${batchSize}`, { method: 'POST' }),
  getAutoApplyDailyRoutine: () => fetchApi<any>('/auto-apply/daily-routine'),
  getAutoApplyDailyHistory: (limit = 10) => fetchApi<any[]>(`/auto-apply/daily-routine/history?limit=${limit}`),
  toggleAutoApplyRoutine: (enabled: boolean) =>
    fetchApi<any>(`/auto-apply/daily-routine/toggle?enabled=${enabled}`, { method: 'POST' }),
  triggerAutoApplyDailyRoutineNow: () =>
    fetchApi<any>('/auto-apply/daily-routine/trigger-now', { method: 'POST' }),

  // Resume Intelligence (Phase 2)
  getProfile: () => fetchApi<any>('/resume/profile'),
  getResumes: () => fetchApi<any>('/resume'),
  getResumeDetail: (resumeId: string) => fetchApi<any>(`/resume/${resumeId}`),
  uploadResumeFile: async (file: File | null, rawText?: string, title: string = 'Master Resume') => {
    const formData = new FormData();
    formData.append('title', title);
    if (file) {
      formData.append('file', file);
    }
    if (rawText) {
      formData.append('raw_text', rawText);
    }
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const res = await fetch(`${API_BASE}/resume/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed with status ${res.status}`);
    }
    return res.json();
  },
  reanalyzeResume: (resumeId: string) =>
    fetchApi<any>(`/resume/reanalyze/${resumeId}`, { method: 'POST' }),
  saveApprovedProfile: (payload: any) =>
    fetchApi<any>('/resume/save-profile', { method: 'POST', body: JSON.stringify(payload) }),
  createResumeVersion: (payload: any) =>
    fetchApi<any>('/resume/versions', { method: 'POST', body: JSON.stringify(payload) }),
  getResumeVersions: (resumeId: string) =>
    fetchApi<any>(`/resume/versions/${resumeId}`),

  // Email
  getEmails: () => fetchApi<any>('/email/messages'),
  classifyEmail: (data: any) => fetchApi<any>('/email/classify', { method: 'POST', body: JSON.stringify(data) }),
  getRecruiters: () => fetchApi<any>('/email/recruiters'),

  // Chat (Phase 5)
  createConversation: (data?: { title?: string }) =>
    fetchApi<any>('/chat/conversations', { method: 'POST', body: JSON.stringify(data || {}) }),
  getConversations: (status?: string) =>
    fetchApi<any>(`/chat/conversations${status ? `?status=${status}` : ''}`),
  getConversation: (id: string) =>
    fetchApi<any>(`/chat/conversations/${id}`),
  deleteConversation: (id: string) =>
    fetchApi<any>(`/chat/conversations/${id}`, { method: 'DELETE' }),
  sendMessageToConversation: (conversationId: string, message: string) =>
    fetchApi<any>(`/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  sendMessage: (message: string, contextType = 'GENERAL', conversationId?: string) =>
    fetchApi<any>('/chat/messages', {
      method: 'POST',
      body: JSON.stringify({ message, context_type: contextType, conversation_id: conversationId }),
    }),

  // Mailbox & Recruiter Intelligence (Phase 7)
  getGmailConnectUrl: () => fetchApi<any>('/mailbox/connect/gmail'),
  getOutlookConnectUrl: () => fetchApi<any>('/mailbox/connect/outlook'),
  handleOAuthCallback: (payload: any) =>
    fetchApi<any>('/mailbox/callback', { method: 'POST', body: JSON.stringify(payload) }),
  getMailboxConnections: () => fetchApi<any[]>('/mailbox/connections'),
  disconnectMailbox: (connectionId: string) =>
    fetchApi<any>(`/mailbox/connections/${connectionId}`, { method: 'DELETE' }),
  triggerMailboxSync: (payload?: { connection_id?: string; full_sync?: boolean }) =>
    fetchApi<any[]>('/mailbox/sync', { method: 'POST', body: JSON.stringify(payload || {}) }),
  getMailboxMessages: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any[]>(`/mailbox/messages${query ? `?${query}` : ''}`);
  },
  getMailboxMessageDetail: (id: string) => fetchApi<any>(`/mailbox/messages/${id}`),
  reclassifyMailboxMessage: (id: string, payload: any) =>
    fetchApi<any>(`/mailbox/messages/${id}/reclassify`, { method: 'POST', body: JSON.stringify(payload) }),
  getMailboxThreads: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any[]>(`/mailbox/threads${query ? `?${query}` : ''}`);
  },
  getMailboxThreadDetail: (id: string) => fetchApi<any>(`/mailbox/threads/${id}`),
  getMailboxStats: () => fetchApi<any>('/mailbox/stats'),
  getMailboxNotifications: (unreadOnly = false) =>
    fetchApi<any[]>(`/mailbox/notifications?unread_only=${unreadOnly}`),
  markMailboxNotificationRead: (id: string) =>
    fetchApi<any>(`/mailbox/notifications/${id}/read`, { method: 'POST' }),
  getMailboxRecruiters: () => fetchApi<any[]>('/mailbox/recruiters'),

  // Recruiter AI & Communication Intelligence (Phase 8)
  getRecruitersList: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any[]>(`/communication/recruiters${query ? `?${query}` : ''}`);
  },
  createRecruiterContact: (data: any) =>
    fetchApi<any>('/communication/recruiters', { method: 'POST', body: JSON.stringify(data) }),
  getRecruiterContact: (id: string) =>
    fetchApi<any>(`/communication/recruiters/${id}`),
  updateRecruiterContact: (id: string, data: any) =>
    fetchApi<any>(`/communication/recruiters/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRecruiterContact: (id: string) =>
    fetchApi<any>(`/communication/recruiters/${id}`, { method: 'DELETE' }),

  generateResponseDraft: (payload: any) =>
    fetchApi<any>('/communication/drafts/generate', { method: 'POST', body: JSON.stringify(payload) }),
  getDrafts: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any[]>(`/communication/drafts${query ? `?${query}` : ''}`);
  },
  getDraft: (id: string) =>
    fetchApi<any>(`/communication/drafts/${id}`),
  updateDraft: (id: string, data: any) =>
    fetchApi<any>(`/communication/drafts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  approveDraft: (id: string) =>
    fetchApi<any>(`/communication/drafts/${id}/approve`, { method: 'POST' }),
  deleteDraft: (id: string) =>
    fetchApi<any>(`/communication/drafts/${id}`, { method: 'DELETE' }),

  getInterviews: (status?: string) =>
    fetchApi<any[]>(`/communication/interviews${status ? `?status=${status}` : ''}`),
  createInterview: (data: any) =>
    fetchApi<any>('/communication/interviews', { method: 'POST', body: JSON.stringify(data) }),
  getInterview: (id: string) =>
    fetchApi<any>(`/communication/interviews/${id}`),
  updateInterview: (id: string, data: any) =>
    fetchApi<any>(`/communication/interviews/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteInterview: (id: string) =>
    fetchApi<any>(`/communication/interviews/${id}`, { method: 'DELETE' }),

  generateInterviewPrepBrief: (data: any) =>
    fetchApi<any>('/communication/interviews/prep-brief', { method: 'POST', body: JSON.stringify(data) }),
  getInterviewPrepBrief: (interviewId: string) =>
    fetchApi<any>(`/communication/interviews/${interviewId}/prep-brief`),

  getFollowUpRecommendations: () =>
    fetchApi<any[]>('/communication/follow-ups'),

  // Phase 9: Connectors, Health & Observability
  getConnectors: () =>
    fetchApi<any[]>('/connectors'),
  getConnectorHealth: (slug: string) =>
    fetchApi<any>(`/connectors/${slug}/health`),
  getDetailedHealth: () =>
    fetchApi<any>('/health/detailed'),
  getWorkerMetrics: () =>
    fetchApi<any>('/system/workers'),
  getAuditLogs: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params).toString();
    return fetchApi<any[]>(`/system/audit-logs${query ? `?${query}` : ''}`);
  },
  getDeadLetterQueue: () =>
    fetchApi<any[]>('/system/dead-letter-queue'),

  // Phase 10: Onboarding, Settings & System Status
  getOnboardingState: () =>
    fetchApi<any>('/onboarding/state'),
  updateOnboardingStep: (step: number, data?: any) =>
    fetchApi<any>('/onboarding/step', { method: 'POST', body: JSON.stringify({ step, data }) }),
  completeOnboarding: () =>
    fetchApi<any>('/onboarding/complete', { method: 'POST' }),

  getCandidateProfile: () =>
    fetchApi<any>('/resume/profile'),
  updateCandidateProfile: (data: any) =>
    fetchApi<any>('/resume/profile', { method: 'PUT', body: JSON.stringify(data) }),

  getJobPreferences: () =>
    fetchApi<any>('/settings/job-preferences'),
  updateJobPreferences: (data: any) =>
    fetchApi<any>('/settings/job-preferences', { method: 'PUT', body: JSON.stringify(data) }),

  getAutoApplySettings: () =>
    fetchApi<any>('/settings/auto-apply'),
  updateAutoApplySettings: (data: any) =>
    fetchApi<any>('/settings/auto-apply', { method: 'PUT', body: JSON.stringify(data) }),

  getAIConfig: () =>
    fetchApi<any>('/settings/ai'),
  updateAIConfig: (data: any) =>
    fetchApi<any>('/settings/ai', { method: 'PUT', body: JSON.stringify(data) }),
  testAIConnection: () =>
    fetchApi<any>('/settings/ai/test', { method: 'POST' }),

  getSystemStatus: () =>
    fetchApi<any>('/settings/status'),
  testConnector: (slug: string) =>
    fetchApi<any>(`/connectors/${slug}/test`, { method: 'POST' }),
};

export const apiClient = api;



