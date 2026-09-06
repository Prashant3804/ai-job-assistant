export type ConnectorCapabilityStatus =
  | 'SUPPORTED_AUTO_APPLY'
  | 'SUPPORTED_JOB_DISCOVERY_ONLY'
  | 'EXTERNAL_APPLICATION_REQUIRED'
  | 'NOT_SUPPORTED';

export type JobCapability =
  | 'JOB_DISCOVERY'
  | 'AUTO_APPLY'
  | 'EXTERNAL_APPLICATION'
  | 'UNSUPPORTED';

export type ApplicationStatus =
  | 'DISCOVERED'
  | 'POLICY_PENDING'
  | 'QUEUED'
  | 'PREPARING'
  | 'VALIDATING'
  | 'SUBMITTING'
  | 'APPLIED'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'OA_RECEIVED'
  | 'INTERVIEW_SCHEDULED'
  | 'OFFER_RECEIVED'
  | 'REJECTED'
  | 'WITHDRAWN'
  | 'ARCHIVED'
  | 'FAILED'
  | 'RETRYING'
  | 'BLOCKED'
  | 'DUPLICATE'
  | 'AUTO_APPLY_UNSUPPORTED'
  | 'MISSING_INFORMATION'
  | 'DRAFT';

export type PolicyDecision =
  | 'AUTO_APPLY'
  | 'SKIP_LOW_MATCH'
  | 'SKIP_INELIGIBLE'
  | 'SKIP_BLOCKED_COMPANY'
  | 'SKIP_BLOCKED_KEYWORD'
  | 'SKIP_SALARY'
  | 'SKIP_EXPERIENCE'
  | 'SKIP_LOCATION'
  | 'SKIP_DAILY_LIMIT'
  | 'REQUIRES_USER_REVIEW';

export type SubmissionMethod =
  | 'MANUAL'
  | 'DIRECT_API'
  | 'PARTNER_CONNECTOR'
  | 'EXTERNAL_PORTAL';

export type QueueStatus =
  | 'QUEUED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'RETRYING'
  | 'CANCELLED';

export type EmailClassification =
  | 'INTERVIEW_INVITATION'
  | 'REJECTION'
  | 'OA_REQUEST'
  | 'OFFER'
  | 'GENERAL_INQUIRY'
  | 'SPAM'
  | 'UNCLASSIFIED';

export interface NormalizedJob {
  job_id?: string;
  source: string;
  external_job_id: string;
  company: string;
  title: string;
  description: string;
  requirements: string[];
  skills: string[];
  experience_required: string;
  education_required?: string;
  location: string;
  remote_type: string;
  salary_min?: number;
  salary_max?: number;
  currency: string;
  employment_type: string;
  application_url: string;
  posted_at?: string;
  deadline?: string;
  source_metadata?: Record<string, any>;
}

export interface ConnectorInfo {
  name: string;
  slug: string;
  base_url?: string;
  capability: JobCapability;
  status: {
    status: string;
    rate_limit_remaining?: number;
    connector_mode?: string;
    auth_type?: string;
  };
}

export interface PersonalDetails {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  headline?: string;
  summary?: string;
  is_uncertain?: boolean;
  uncertain_fields?: string[];
}

export interface EducationItem {
  id?: string;
  degree: string;
  institution: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  graduation_year?: string;
  cgpa?: string;
  description?: string;
  is_uncertain?: boolean;
}

export interface CategorizedSkills {
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  cloud: string[];
  tools: string[];
  soft_skills: string[];
}

export interface ExperienceItem {
  id?: string;
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  is_current?: boolean;
  responsibilities: string[];
  technologies: string[];
  is_uncertain?: boolean;
}

export interface ProjectItem {
  id?: string;
  name: string;
  description?: string;
  technologies: string[];
  links: string[];
  is_uncertain?: boolean;
}

export interface CertificationItem {
  id?: string;
  name: string;
  issuer?: string;
  date?: string;
  is_uncertain?: boolean;
}

export interface StructuredResumeData {
  personal: PersonalDetails;
  education: EducationItem[];
  skills: CategorizedSkills;
  experience: ExperienceItem[];
  projects: ProjectItem[];
  certifications: CertificationItem[];
  raw_text?: string;
  extraction_timestamp?: string;
  total_years_experience?: number;
}

export interface ResumeVersionResponse {
  id: string;
  resume_id: string;
  version_number: number;
  tailored_for_job_id?: string;
  tailored_content?: any;
  file_url?: string;
  created_at: string;
}

export interface Skill {
  id?: string;
  name: string;
  category: string;
  proficiency_level: string;
  years_experience: number;
  is_verified: boolean;
}

export interface Education {
  id?: string;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date?: string;
  end_date?: string;
  gpa?: string;
  description?: string;
}

export interface Experience {
  id?: string;
  company_name: string;
  title: string;
  location?: string;
  employment_type: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
  bullet_points?: string[];
  technologies?: string[];
}

export interface Project {
  id?: string;
  title: string;
  description?: string;
  url?: string;
  github_url?: string;
  technologies?: string[];
  start_date?: string;
  end_date?: string;
}

export interface UserProfile {
  id: string;
  headline?: string;
  summary?: string;
  location?: string;
  remote_preference: string;
  target_roles: string[];
  years_of_experience: number;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  skills: Skill[];
  educations: Education[];
  experiences: Experience[];
  projects: Project[];
}

export interface JobPreference {
  id: string;
  desired_titles: string[];
  desired_locations: string[];
  remote_types: string[];
  min_base_salary?: number;
  max_base_salary?: number;
  currency: string;
  target_industries: string[];
  sponsorship_required: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  role: string;
  profile?: UserProfile;
  job_preferences?: JobPreference;
}

export interface JobSource {
  id: string;
  name: string;
  slug: string;
  base_url?: string;
  connector_type: string;
  capability_status: ConnectorCapabilityStatus;
  is_active: boolean;
}

export interface Job {
  id: string;
  job_source_id?: string;
  external_id?: string;
  title: string;
  company_name: string;
  location?: string;
  remote_type: string;
  employment_type: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency: string;
  description: string;
  requirements_summary?: string;
  required_skills: string[];
  preferred_skills: string[];
  experience_level: string;
  apply_url?: string;
  posted_at?: string;
  job_source?: JobSource;
}

export type EligibilityStatus =
  | 'ELIGIBLE'
  | 'LIKELY_ELIGIBLE'
  | 'REVIEW'
  | 'NOT_ELIGIBLE'
  | 'INSUFFICIENT_DATA';

export type RecommendationStatus =
  | 'STRONG_MATCH'
  | 'GOOD_MATCH'
  | 'POSSIBLE_MATCH'
  | 'WEAK_MATCH'
  | 'NOT_RECOMMENDED';

export interface DimensionScore {
  score: number;
  weight: number;
  contribution: number;
  status: string;
  details?: Record<string, any>;
  rationale: string;
}

export interface ScoreBreakdown {
  overall_score: number;
  semantic_score: number;
  skill_score?: number;
  skills_score: number;
  experience_score: number;
  education_score?: number;
  location_score?: number;
  role_score?: number;
  salary_score?: number;
  preference_score: number;
  matched_skills: string[];
  missing_required_skills?: string[];
  missing_preferred_skills?: string[];
  missing_skills: string[];
  dimensions?: Record<string, DimensionScore>;
  eligibility_status?: EligibilityStatus;
  recommendation?: RecommendationStatus;
  explanation?: string;
  strengths?: string[];
  gaps?: string[];
  match_reasons?: string[];
  risk_factors?: string[];
}

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  resume_id?: string;
  resume_version_id?: string;
  overall_score: number;
  skill_score?: number;
  skills_score?: number;
  experience_score?: number;
  education_score?: number;
  location_score?: number;
  role_score?: number;
  salary_score?: number;
  semantic_score?: number;
  preference_score?: number;
  matched_skills?: string[];
  missing_required_skills?: string[];
  missing_preferred_skills?: string[];
  eligibility_status?: EligibilityStatus;
  recommendation?: RecommendationStatus;
  explanation?: string;
  confidence?: number;
  scoring_version?: string;
  embedding_model?: string;
  score_breakdown?: ScoreBreakdown;
  match_reasons?: string[];
  is_bookmarked: boolean;
  is_dismissed: boolean;
  created_at: string;
  job: Job;
}

export interface MatchingEngineHealth {
  engine_status: string;
  omniroute_configured: boolean;
  omniroute_reachable: boolean;
  omniroute_status: string;
  chat_model: string;
  embedding_model: string;
  deterministic_matching_available: boolean;
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  scoring_version: string;
}

export interface ApplicationEvent {
  id: string;
  application_id: string;
  event_type: string;
  old_status?: string;
  new_status?: string;
  title: string;
  description?: string;
  created_at: string;
}

export interface ApplicationAttempt {
  id: string;
  application_id: string;
  attempt_number: number;
  status: string;
  submission_method: string;
  response_code?: number;
  external_application_id?: string;
  error_code?: string;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

export interface ApplicationAnswer {
  id: string;
  question_key: string;
  question_text: string;
  answer_text: string;
  is_sensitive: boolean;
  confidence_source: string;
}

export interface ApplicationDocument {
  id: string;
  document_type: string;
  file_url: string;
  file_name: string;
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  resume_id?: string;
  resume_version_id?: string;
  source?: string;
  external_job_id?: string;
  status: ApplicationStatus;
  match_score?: number;
  eligibility_status?: string;
  policy_decision?: PolicyDecision | string;
  applied_date?: string;
  submitted_at?: string;
  last_attempt_at?: string;
  submission_method: string;
  external_application_id?: string;
  failure_reason?: string;
  notes?: string;
  follow_up_date?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
  job: Job;
  events?: ApplicationEvent[];
  attempts?: ApplicationAttempt[];
  answers?: ApplicationAnswer[];
  documents?: ApplicationDocument[];
}

export interface ApplicationPolicy {
  id: string;
  user_id: string;
  auto_apply_enabled: boolean;
  minimum_match_score: number;
  minimum_salary?: number;
  maximum_experience?: number;
  preferred_roles: string[];
  blocked_roles: string[];
  preferred_locations: string[];
  blocked_locations: string[];
  blocked_companies: string[];
  blocked_keywords: string[];
  allowed_employment_types: string[];
  daily_application_limit?: number | null;
  per_source_daily_limit?: number | null;
  duplicate_protection: boolean;
  allow_entry_level: boolean;
  allow_internships: boolean;
  allow_remote: boolean;
  allow_hybrid: boolean;
  allow_onsite: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApplicationPolicyUpdate {
  auto_apply_enabled?: boolean;
  minimum_match_score?: number;
  minimum_salary?: number | null;
  maximum_experience?: number | null;
  preferred_roles?: string[];
  blocked_roles?: string[];
  preferred_locations?: string[];
  blocked_locations?: string[];
  blocked_companies?: string[];
  blocked_keywords?: string[];
  allowed_employment_types?: string[];
  daily_application_limit?: number | null;
  per_source_daily_limit?: number | null;
  duplicate_protection?: boolean;
  allow_entry_level?: boolean;
  allow_internships?: boolean;
  allow_remote?: boolean;
  allow_hybrid?: boolean;
  allow_onsite?: boolean;
}

export interface AutoApplyStatus {
  auto_apply_enabled: boolean;
  minimum_match_score?: number;
  daily_application_limit?: number | null;
  daily_limit_enabled?: boolean;
  daily_limit_label?: string;
  applications_submitted_today?: number;
  today_applications_count: number;
  remaining_daily_quota?: number | null;
  pending_queue_count: number;
  total_applied: number;
  total_failed: number;
  system_mode: string;
}

export interface ApplicationQueueItem {
  id: string;
  user_id: string;
  application_id: string;
  job_id: string;
  priority: number;
  status: QueueStatus;
  attempt_count: number;
  max_attempts: number;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  idempotency_key?: string;
  application?: Application;
  job?: Job;
  created_at: string;
}

export interface ApplicationStatistics {
  total_applications: number;
  applied_count: number;
  failed_count: number;
  in_progress_count: number;
  interview_count: number;
  offer_count: number;
  rejected_count: number;
  skipped_count: number;
  unsupported_count: number;
  missing_information_count: number;
  queued_count: number;
  by_status: Record<string, number>;
}

export interface EmailMessage {
  id: string;
  email_account_id: string;
  sender_email: string;
  sender_name?: string;
  recipient_email: string;
  subject: string;
  body_text?: string;
  received_at: string;
  is_recruiter: boolean;
  classification: EmailClassification;
  confidence_score: number;
  application_id?: string;
}

export interface ChatToolCall {
  id: string;
  tool_name: string;
  arguments?: Record<string, any>;
  result_summary?: string;
  result_data?: Record<string, any>;
  status: string;
  duration_ms?: number;
  created_at: string;
}

export interface ChatJobCard {
  job_id: string;
  title: string;
  company: string;
  location: string;
  remote_type: string;
  source: string;
  source_slug?: string;
  salary_range?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  experience_level?: string;
  required_skills?: string[];
  preferred_skills?: string[];
  apply_url?: string;
  description_snippet?: string;
  overall_score?: number;
  recommendation?: string;
  eligibility_status?: string;
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface ChatMatchScorecard {
  job_id?: string;
  job_title?: string;
  company?: string;
  overall_score: number;
  recommendation: string;
  eligibility_status: string;
  dimension_scores: {
    skills_score: number;
    experience_score: number;
    role_relevance_score: number;
    location_remote_score: number;
    salary_score: number;
    education_score: number;
  };
  matched_skills: string[];
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  key_strengths: string[];
  risks_or_gaps: string[];
  ai_explanation?: string;
}

export interface ChatMissingSkillsData {
  job_id?: string;
  job_title?: string;
  company?: string;
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  candidate_skills: string[];
  skills_gap_percentage: number;
  upskilling_recommendation?: string;
}

export interface ChatStructuredPayload {
  suggestions?: string[];
  executed_tools?: string[];
  job_cards?: ChatJobCard[];
  match_scorecard?: ChatMatchScorecard;
  missing_skills_analysis?: ChatMissingSkillsData;
  [key: string]: any;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  sender_type: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  structured_payload?: ChatStructuredPayload;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  user_id: string;
  title: string;
  status: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationDetail extends ChatConversation {
  messages: ChatMessage[];
}

export interface DashboardSummaryMetrics {
  jobs_found: number;
  recommended_jobs: number;
  applications_total: number;
  interviews: number;
  offers: number;
  pending_applications: number;
}

export interface AutoApplyDailyRun {
  id: string;
  user_id: string;
  scheduled_for: string;
  started_at: string;
  completed_at?: string;
  status: string;
  jobs_found: number;
  matching_jobs: number;
  applied_count: number;
  already_applied_count: number;
  manual_required_count: number;
  failed_count: number;
  skipped_count: number;
  error_message?: string;
  run_summary_json?: Record<string, any>;
  created_at: string;
}

export interface AutoApplyDailyRoutineInfo {
  schedule_time_display: string;
  schedule_timezone: string;
  auto_apply_enabled: boolean;
  enabled?: boolean;
  status: 'Active' | 'Disabled' | string;
  next_run_at: string;
  next_run_display: string;
  next_run_ist?: string;
  last_run?: AutoApplyDailyRun | null;
  total_runs_count: number;
  daily_total_applied?: number;
  daily_max_capacity?: number;
  source_counters?: Record<string, number>;
  source_limits?: Record<string, number>;
  ai_provider_status?: {
    primary_configured?: boolean;
    primary_provider?: string;
    fallback_configured?: boolean;
    fallback_provider?: string;
    last_provider_used?: string;
    last_fallback_occurred?: boolean;
    active_display?: string;
  };
}

export interface RecentAutoApplyApplication {
  id: string;
  company_name: string;
  job_title: string;
  role_title?: string;
  status: string;
  match_score?: number | null;
  applied_at?: string;
  applied_at_display: string;
  applied_at_ist?: string;
  submission_method: string;
}

export interface DashboardAnalytics {
  metrics: DashboardSummaryMetrics;
  funnel: Record<string, number>;
  top_skills_in_demand: { skill: string; count: number }[];
  recent_activities: { id: string; title: string; description: string; created_at: string; event_type: string }[];
  top_recommendations: JobMatch[];
  auto_apply_routine?: AutoApplyDailyRoutineInfo;
  recent_auto_apply_applications?: RecentAutoApplyApplication[];
}

export type MailboxProvider = 'GMAIL' | 'OUTLOOK' | 'MOCK';
export type MailboxConnStatus = 'CONNECTED' | 'TOKEN_EXPIRED' | 'REFRESH_REQUIRED' | 'NEEDS_REAUTH' | 'REVOKED' | 'DISCONNECTED' | 'ERROR' | 'SYNCING';

export interface OAuthAuthorizeUrlResponse {
  authorization_url: string;
  state: string;
  provider: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
  provider?: string;
}

export interface MailboxConnection {
  id: string;
  user_id: string;
  provider: string;
  email_address: string;
  status: string;
  last_sync_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MailboxMessage {
  id: string;
  user_id: string;
  connection_id: string;
  provider: string;
  external_message_id: string;
  external_thread_id?: string;
  sender_email: string;
  sender_name?: string;
  recipient_email: string;
  subject: string;
  snippet?: string;
  body_text?: string;
  body_html?: string;
  received_at: string;
  has_attachments: boolean;
  attachments_metadata?: any[];
  is_read: boolean;
  is_recruiter: boolean;
  recruiter_status: string;
  is_job_related: boolean;
  classification: string;
  confidence_score: number;
  classification_reason?: string;
  detected_company?: string;
  detected_job_title?: string;
  application_id?: string;
  created_at: string;
}

export interface MailboxThread {
  id: string;
  connection_id: string;
  external_thread_id: string;
  subject: string;
  last_message_at: string;
  message_count: number;
  is_recruiter_thread: boolean;
  application_id?: string;
  messages: MailboxMessage[];
}

export interface MailboxStats {
  total_connections: number;
  total_messages: number;
  job_related_messages: number;
  interview_invitations: number;
  rejections: number;
  offers: number;
  recruiter_messages: number;
  unlinked_messages: number;
}

export interface MailboxNotification {
  id: string;
  user_id: string;
  message_id?: string;
  application_id?: string;
  notification_type: string;
  title: string;
  content: string;
  is_read: boolean;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface RecruiterContact {
  id: string;
  user_id: string;
  name: string;
  email: string;
  company_name?: string;
  title?: string;
  linkedin_url?: string;
  phone?: string;
  relationship_stage?: string;
  responsiveness_rating?: number;
  last_interaction_at?: string;
  interaction_count?: number;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface ManualClassificationPayload {
  classification: string;
  recruiter_status?: string;
  detected_company?: string;
  detected_job_title?: string;
  application_id?: string;
}

// ==========================================
// Phase 8: Recruiter AI & Communication Types
// ==========================================

export type DraftIntent =
  | 'SCHEDULE_INTERVIEW'
  | 'THANK_YOU'
  | 'NEGOTIATE_OFFER'
  | 'FOLLOW_UP'
  | 'ACCEPT_OFFER'
  | 'DECLINE_OFFER'
  | 'COLD_REPLY'
  | 'GENERAL';

export type DraftTone =
  | 'PROFESSIONAL'
  | 'CONFIDENT'
  | 'ENTHUSIASTIC'
  | 'ASSERTIVE'
  | 'CONCISE';

export type DraftStatus =
  | 'DRAFT'
  | 'APPROVED'
  | 'COPIED'
  | 'SENT'
  | 'DISCARDED';

export type RecruiterRelationshipStage =
  | 'INITIAL_CONTACT'
  | 'SCREEN_SCHEDULED'
  | 'IN_PROCESS'
  | 'OFFER_STAGE'
  | 'GHOSTED'
  | 'REJECTED'
  | 'ARCHIVED';

export type InterviewRoundType =
  | 'TECHNICAL_SCREEN'
  | 'SYSTEM_DESIGN'
  | 'BEHAVIORAL'
  | 'HIRING_MANAGER'
  | 'CODING_OA'
  | 'PANEL'
  | 'FINAL';

export type InterviewStatus =
  | 'SCHEDULED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'RESCHEDULED';

export interface CommunicationDraft {
  id: string;
  user_id: string;
  recruiter_id?: string;
  application_id?: string;
  message_id?: string;
  intent: DraftIntent;
  tone: DraftTone;
  subject: string;
  body_text: string;
  status: DraftStatus;
  key_points_addressed: string[];
  candidate_availability_used: string[];
  is_approved: boolean;
  approved_at?: string;
  sent_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DraftGenerationRequest {
  recruiter_id?: string;
  recruiter_name?: string;
  recruiter_email?: string;
  company_name?: string;
  job_title?: string;
  application_id?: string;
  message_id?: string;
  intent?: DraftIntent;
  tone?: DraftTone;
  candidate_availability?: string[];
  custom_instructions?: string;
  salary_expectation?: string;
  offer_details?: string;
  incoming_email_snippet?: string;
}

export interface InterviewSession {
  id: string;
  user_id: string;
  application_id?: string;
  recruiter_id?: string;
  round_type: InterviewRoundType;
  title: string;
  company_name: string;
  job_title?: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_url?: string;
  meeting_platform?: string;
  interviewers?: Array<{ name: string; title?: string; linkedin?: string }>;
  status: InterviewStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface StarStoryItem {
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  relevant_skills?: string[];
}

export interface ExpectedQuestionItem {
  question: string;
  category: string;
  suggested_talking_points: string[];
}

export interface InterviewPrepBrief {
  id: string;
  user_id: string;
  interview_id?: string;
  application_id?: string;
  company_name: string;
  job_title: string;
  company_overview?: string;
  role_summary?: string;
  technical_focus_areas: string[];
  expected_questions: ExpectedQuestionItem[];
  star_stories: StarStoryItem[];
  reverse_questions_to_ask: string[];
  cheat_sheet_markdown?: string;
  created_at: string;
}

export interface FollowUpRecommendation {
  application_id?: string;
  company_name: string;
  job_title: string;
  recruiter_name?: string;
  recruiter_email?: string;
  last_contact_date?: string;
  days_inactive: number;
  nudge_priority: 'HIGH' | 'MEDIUM' | 'LOW';
  suggested_action: string;
  recommended_intent: DraftIntent;
  suggested_draft_subject: string;
  suggested_draft_body: string;
}

// ==========================================
// Phase 9: Production & Connector Types
// ==========================================

export interface ConnectorCapabilityInfo {
  slug: string;
  name: string;
  supported_capabilities: string[];
  status: string;
  authorization_type: string;
  api_version: string;
  terms_reference: string;
  rate_limit_policy: string;
  is_auto_apply_supported: boolean;
  is_external_application_required: boolean;
  notes: string;
}

export interface ConnectorHealthInfo {
  slug: string;
  name: string;
  status: string;
  latency_ms: number;
  success_count: number;
  failure_count: number;
  error_rate_percent: number;
  rate_limit_events: number;
  last_success_at?: string;
  last_failure_at?: string;
  last_error_message?: string;
}

export interface SystemHealthDetailed {
  status: string;
  environment: string;
  database: Record<string, any>;
  queue: Record<string, number>;
  workers: {
    active_count: number;
    dead_letter_count: number;
  };
  connectors: ConnectorHealthInfo[];
  ai_provider: Record<string, any>;
  timestamp: string;
}

export interface AuditEventItem {
  id: string;
  user_id?: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface WorkerMetrics {
  active_workers_count: number;
  total_workers: Array<{
    worker_id: string;
    status: string;
    started_at: string;
    last_heartbeat_at: string;
    jobs_processed: number;
    jobs_failed: number;
    current_job_id?: string;
  }>;
  queue_depth: Record<string, number>;
  dead_letter_count: number;
  recovery_events_count: number;
}

export interface DeadLetterItem {
  id: string;
  application_id: string;
  job_id: string;
  failure_reason: string;
  attempt_count: number;
  last_error?: string;
  resolved: boolean;
  created_at: string;
}

// Phase 10 Production & Onboarding Types
export interface OnboardingState {
  user_id: string;
  email: string;
  full_name: string;
  current_step: number;
  is_completed: boolean;
  profile_configured: boolean;
  resume_uploaded: boolean;
  preferences_configured: boolean;
  policy_configured: boolean;
  mailbox_connected: boolean;
  ai_configured: boolean;
}

export interface CandidateProfileDetailed {
  id: string;
  headline?: string;
  summary?: string;
  location?: string;
  country?: string;
  phone?: string;
  remote_preference: string;
  target_roles: string[];
  preferred_roles: string[];
  preferred_locations: string[];
  preferred_work_arrangement?: string;
  years_of_experience: number;
  work_authorization?: string;
  notice_period?: string;
  salary_expectation?: number;
  source: string; // 'RESUME' | 'USER_CONFIRMED'
  onboarding_step: number;
  onboarding_completed: boolean;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  skills: Array<{
    id?: string;
    name: string;
    category: string;
    proficiency_level: string;
    years_experience: number;
    is_verified: boolean;
  }>;
  educations: Array<{
    id?: string;
    institution: string;
    degree: string;
    field_of_study: string;
    start_date?: string;
    end_date?: string;
    gpa?: string;
    description?: string;
  }>;
  experiences: Array<{
    id?: string;
    company_name: string;
    title: string;
    location?: string;
    employment_type: string;
    start_date?: string;
    end_date?: string;
    is_current: boolean;
    description?: string;
    bullet_points: string[];
    technologies: string[];
  }>;
  projects: Array<{
    id?: string;
    title: string;
    description?: string;
    url?: string;
    github_url?: string;
    technologies: string[];
    start_date?: string;
    end_date?: string;
  }>;
}

export interface JobPreferencesConfig {
  id?: string;
  user_id?: string;
  desired_titles: string[];
  desired_locations: string[];
  remote_types: string[];
  min_base_salary?: number;
  max_base_salary?: number;
  currency: string;
  employment_types: string[];
  preferred_industries: string[];
  excluded_industries: string[];
  preferred_companies: string[];
  blocked_companies: string[];
  blocked_keywords: string[];
  experience_min_years?: number;
  experience_max_years?: number;
  job_freshness_days: number;
  minimum_match_score: number;
  target_industries: string[];
  sponsorship_required: boolean;
}

export interface AutoApplyPolicyConfig {
  id?: string;
  user_id?: string;
  auto_apply_enabled: boolean;
  minimum_match_score: number;
  minimum_salary?: number;
  maximum_experience?: number;
  preferred_roles: string[];
  blocked_roles: string[];
  preferred_locations: string[];
  blocked_locations: string[];
  blocked_companies: string[];
  blocked_keywords: string[];
  allowed_employment_types: string[];
  daily_application_limit?: number | null;
  per_source_daily_limit?: number | null;
  per_company_limit: number;
  duplicate_protection: boolean;
  require_complete_profile: boolean;
  allow_entry_level: boolean;
  allow_internships: boolean;
  allow_remote: boolean;
  allow_hybrid: boolean;
  allow_onsite: boolean;
}

export interface AIConfigInfo {
  provider: string;
  model: string;
  is_configured: boolean;
  api_key_masked?: string;
  timeout_seconds: number;
  max_retries: number;
  fallback_provider: string;
  supports_structured: boolean;
}

export interface AIConnectionTestResult {
  status: 'CONNECTED' | 'AUTH_FAILED' | 'RATE_LIMITED' | 'TIMEOUT' | 'UNAVAILABLE' | 'NOT_CONFIGURED';
  provider: string;
  latency_ms?: number;
  model?: string;
  message: string;
}

export interface SystemComponentStatusItem {
  name: string;
  slug: string;
  status: 'HEALTHY' | 'DEGRADED' | 'NOT_CONFIGURED' | 'AUTH_REQUIRED' | 'DOWN';
  details?: string;
  last_checked: string;
}

export interface SystemStatusInfo {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  environment: string;
  version: string;
  database: SystemComponentStatusItem;
  omniroute: SystemComponentStatusItem;
  gmail: SystemComponentStatusItem;
  outlook: SystemComponentStatusItem;
  job_connectors: SystemComponentStatusItem;
  application_queue: SystemComponentStatusItem;
  workers: SystemComponentStatusItem;
  ai_service: SystemComponentStatusItem;
}

export interface ConnectorTestResult {
  slug: string;
  name: string;
  status: 'PASS' | 'AUTH_REQUIRED' | 'UNSUPPORTED' | 'RATE_LIMITED' | 'ERROR';
  capability: string;
  discovery_tested: boolean;
  submission_tested: boolean;
  message: string;
}



