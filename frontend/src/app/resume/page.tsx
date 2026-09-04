'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  FileText,
  Upload,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Briefcase,
  GraduationCap,
  FolderGit2,
  Award,
  Plus,
  Trash2,
  RefreshCw,
  Save,
  Layers,
  FileCode,
  ExternalLink,
  Code2,
  Database,
  Cloud,
  Wrench,
  Users,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  StructuredResumeData,
  PersonalDetails,
  CategorizedSkills,
  EducationItem,
  ExperienceItem,
  ProjectItem,
  CertificationItem,
  ResumeVersionResponse,
} from '@/types';

export default function ResumeIntelligencePage() {
  const [activeResumeId, setActiveResumeId] = useState<string | null>(null);
  const [resumes, setResumes] = useState<any[]>([]);
  const [versions, setVersions] = useState<ResumeVersionResponse[]>([]);
  const [rawText, setRawText] = useState<string>('');
  const [showRawText, setShowRawText] = useState(false);

  // Structured Editable State
  const [personal, setPersonal] = useState<PersonalDetails>({
    name: 'Alex Mercer',
    email: 'alex.mercer@example.com',
    phone: '(415) 555-0199',
    location: 'San Francisco, CA (Remote)',
    linkedin_url: 'https://linkedin.com/in/alexmercer-dev',
    github_url: 'https://github.com/alexmercer-dev',
    portfolio_url: 'https://alexmercer.dev',
    headline: 'Senior Full Stack & AI Systems Engineer',
    summary:
      'Senior Engineer with 5+ years of experience designing high-throughput distributed backends, REST/GraphQL APIs, and modern React/Next.js interfaces.',
    is_uncertain: false,
    uncertain_fields: [],
  });

  const [skills, setSkills] = useState<CategorizedSkills>({
    programming_languages: ['Python', 'TypeScript', 'JavaScript', 'Go', 'SQL'],
    frameworks: ['FastAPI', 'React', 'Next.js', 'TailwindCSS', 'Node.js'],
    databases: ['PostgreSQL', 'Redis', 'pgvector', 'MongoDB'],
    cloud: ['AWS', 'Docker', 'GCP', 'Cloudflare'],
    tools: ['Git', 'GitHub Actions', 'Postman', 'Linux'],
    soft_skills: ['System Design', 'Cross-Functional Leadership', 'Mentorship'],
  });

  const [education, setEducation] = useState<EducationItem[]>([
    {
      id: 'edu-1',
      degree: 'Bachelor of Science',
      institution: 'University of California, Berkeley',
      field_of_study: 'Computer Science',
      start_date: '2017',
      end_date: '2021',
      graduation_year: '2021',
      cgpa: '3.85',
      description: "Dean's Honor List, coursework in Distributed Systems, Algorithms, and Database Management.",
      is_uncertain: false,
    },
  ]);

  const [experience, setExperience] = useState<ExperienceItem[]>([
    {
      id: 'exp-1',
      company: 'Apex Cloud Systems',
      role: 'Senior Backend Engineer',
      start_date: '2023-01',
      end_date: 'Present',
      is_current: true,
      responsibilities: [
        'Architected asynchronous microservices with FastAPI and PostgreSQL pgvector, cutting p99 latency by 42%.',
        'Engineered vector retrieval pipelines for search across 10M+ documents with sub-50ms latency.',
        'Mentored 6 junior engineers and established automated CI/CD workflows.',
      ],
      technologies: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis'],
      is_uncertain: false,
    },
    {
      id: 'exp-2',
      company: 'Nexus Tech Labs',
      role: 'Full Stack Software Engineer',
      start_date: '2021-03',
      end_date: '2022-12',
      is_current: false,
      responsibilities: [
        'Developed high-performance Next.js web application used by 120k monthly active users.',
        'Optimized relational database queries reducing database CPU load by 35%.',
      ],
      technologies: ['React', 'TypeScript', 'Node.js', 'PostgreSQL', 'TailwindCSS'],
      is_uncertain: false,
    },
  ]);

  const [projects, setProjects] = useState<ProjectItem[]>([
    {
      id: 'proj-1',
      name: 'AI Vector Search & Ranking Engine',
      description:
        'Open-source hybrid keyword + semantic similarity search engine built with FastAPI and PostgreSQL pgvector.',
      technologies: ['Python', 'FastAPI', 'PostgreSQL', 'pgvector', 'Docker'],
      links: ['https://github.com/alexmercer-dev/ai-search-engine'],
      is_uncertain: false,
    },
  ]);

  const [certifications, setCertifications] = useState<CertificationItem[]>([
    {
      id: 'cert-1',
      name: 'AWS Certified Solutions Architect',
      issuer: 'Amazon Web Services',
      date: '2023',
      is_uncertain: false,
    },
  ]);

  // Skill input helper states
  const [newSkillText, setNewSkillText] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState<keyof CategorizedSkills>('programming_languages');

  // UI state
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [versioning, setVersioning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadInitialData() {
    try {
      setLoading(true);
      const resumeList = await api.getResumes();
      setResumes(resumeList);
      if (resumeList && resumeList.length > 0) {
        const primary = resumeList[0];
        setActiveResumeId(primary.id);
        setRawText(primary.raw_text || '');
        if (primary.parsed_data && primary.parsed_data.personal) {
          applyStructuredData(primary.parsed_data);
        }
        // Load versions
        loadVersions(primary.id);
      }
    } catch (err) {
      console.error('Failed to load initial resume data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(resumeId: string) {
    try {
      const vList = await api.getResumeVersions(resumeId);
      setVersions(vList);
    } catch (err) {
      console.error('Failed to load versions:', err);
    }
  }

  function applyStructuredData(data: StructuredResumeData) {
    if (data.personal) setPersonal(data.personal);
    if (data.skills) setSkills(data.skills);
    if (data.education) setEducation(data.education);
    if (data.experience) setExperience(data.experience);
    if (data.projects) setProjects(data.projects);
    if (data.certifications) setCertifications(data.certifications);
    if (data.raw_text) setRawText(data.raw_text);
  }

  function notify(text: string, type: 'success' | 'error' = 'success') {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage(null), 4000);
  }

  // 1. File Upload & Extraction
  async function handleFileUpload(fileToUpload: File) {
    if (!fileToUpload) return;
    if (fileToUpload.size > 10 * 1024 * 1024) {
      notify('File size exceeds 10MB limit.', 'error');
      return;
    }
    const ext = fileToUpload.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'doc', 'txt'].includes(ext || '')) {
      notify('Only PDF, DOCX, and TXT files are supported.', 'error');
      return;
    }

    try {
      setAnalyzing(true);
      notify('Parsing document and extracting structured candidate intelligence...');
      const res = await api.uploadResumeFile(fileToUpload, undefined, fileToUpload.name);
      if (res.structured_data) {
        applyStructuredData(res.structured_data);
      }
      setActiveResumeId(res.resume_id);
      setRawText(res.raw_text || '');
      await loadVersions(res.resume_id);
      notify('Resume extracted and candidate profile updated successfully!');
    } catch (err: any) {
      notify(`Extraction failed: ${err.message}`, 'error');
    } finally {
      setAnalyzing(false);
      setSelectedFile(null);
    }
  }

  // 2. Re-analyze Resume
  async function handleReanalyze() {
    if (!activeResumeId) return;
    try {
      setAnalyzing(true);
      notify('Re-analyzing resume with AI extraction engine...');
      const res = await api.reanalyzeResume(activeResumeId);
      if (res.structured_data) {
        applyStructuredData(res.structured_data);
      }
      notify('Resume successfully re-analyzed.');
    } catch (err: any) {
      notify(`Re-analysis failed: ${err.message}`, 'error');
    } finally {
      setAnalyzing(false);
    }
  }

  // 3. Save Approved Profile
  async function handleSaveProfile() {
    try {
      setSaving(true);
      const payload = {
        resume_id: activeResumeId,
        personal,
        skills,
        education,
        experience,
        projects,
        certifications,
      };
      await api.saveApprovedProfile(payload);
      notify('Candidate profile approved and saved to database!');
    } catch (err: any) {
      notify(`Save error: ${err.message}`, 'error');
    } finally {
      setSaving(false);
    }
  }

  // 4. Create New Resume Version
  async function handleCreateVersion() {
    if (!activeResumeId) return;
    const versionTitle = prompt('Enter a label for this version (e.g. "Tailored for AI Systems" or "v2"):');
    if (!versionTitle) return;

    try {
      setVersioning(true);
      const structured: StructuredResumeData = {
        personal,
        education,
        skills,
        experience,
        projects,
        certifications,
        raw_text: rawText,
      };
      const res = await api.createResumeVersion({
        resume_id: activeResumeId,
        version_title: versionTitle,
        structured_data: structured,
      });
      await loadVersions(activeResumeId);
      notify(`New version v${res.version_number} snapshot created!`);
    } catch (err: any) {
      notify(`Version creation failed: ${err.message}`, 'error');
    } finally {
      setVersioning(false);
    }
  }

  // Skill Chip Management
  function handleAddSkill() {
    if (!newSkillText.trim()) return;
    const clean = newSkillText.trim();
    const currentList = skills[newSkillCategory] || [];
    if (!currentList.some((s) => s.toLowerCase() === clean.toLowerCase())) {
      setSkills((prev) => ({
        ...prev,
        [newSkillCategory]: [...currentList, clean],
      }));
    }
    setNewSkillText('');
  }

  function handleRemoveSkill(category: keyof CategorizedSkills, skillToRemove: string) {
    setSkills((prev) => ({
      ...prev,
      [category]: (prev[category] || []).filter((s) => s !== skillToRemove),
    }));
  }

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Resume Intelligence Studio"
        subtitle="Binary document parsing, zero-hallucination structured extraction, and profile versioning"
        actionButton={
          <div className="flex items-center gap-2">
            <button
              onClick={handleReanalyze}
              disabled={analyzing || !activeResumeId}
              className="flex items-center gap-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-2 rounded-lg shadow-2xs transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin text-sky-600' : 'text-slate-500'}`} />
              <span>{analyzing ? 'Analyzing...' : 'Re-analyze Resume'}</span>
            </button>

            <button
              onClick={handleCreateVersion}
              disabled={versioning || !activeResumeId}
              className="flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 text-xs font-semibold px-3 py-2 rounded-lg transition-colors"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Create Version</span>
            </button>

            <button
              onClick={handleSaveProfile}
              disabled={saving}
              className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saving ? 'Saving...' : 'Save Profile'}</span>
            </button>
          </div>
        }
      />

      <div className="p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* Status Notification */}
        {statusMessage && (
          <div
            className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2.5 border animate-in fade-in duration-200 ${
              statusMessage.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Upload Zone & Version Bar Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Document Upload Zone (2 cols) */}
          <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-sky-500" /> Upload PDF / DOCX Resume
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Direct text stream extraction with MIME validation (Max 10MB)
                </p>
              </div>
              <button
                onClick={() => setShowRawText(!showRawText)}
                className="text-xs font-semibold text-slate-600 hover:text-sky-600 flex items-center gap-1"
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>{showRawText ? 'Hide Raw Text' : 'View Raw Extracted Text'}</span>
              </button>
            </div>

            {/* Drag & Drop Box */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all ${
                dragActive
                  ? 'border-sky-500 bg-sky-50/50'
                  : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
              }`}
            >
              <div className="w-10 h-10 rounded-full bg-sky-100 text-sky-600 flex items-center justify-center mx-auto mb-2">
                <FileText className="w-5 h-5" />
              </div>
              <div className="text-xs font-bold text-slate-800">
                Drag & drop your resume file, or{' '}
                <label className="text-sky-600 hover:underline cursor-pointer">
                  browse
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileUpload(e.target.files[0]);
                      }
                    }}
                  />
                </label>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">Supports PDF (.pdf), Microsoft Word (.docx), and Plain Text</p>
            </div>

            {/* Collapsible Raw Text View */}
            {showRawText && (
              <div className="bg-slate-900 text-slate-200 rounded-xl p-4 text-xs font-mono max-h-48 overflow-y-auto whitespace-pre-line leading-relaxed border border-slate-800">
                {rawText || 'No raw text available.'}
              </div>
            )}
          </div>

          {/* Resume Version Snapshots (1 col) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-500" /> Resume Versions
              </h3>
              <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                {versions.length} Snapshots
              </span>
            </div>

            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {versions && versions.length > 0 ? (
                versions.map((v) => (
                  <div
                    key={v.id}
                    onClick={() => {
                      if (v.tailored_content) {
                        applyStructuredData(v.tailored_content);
                        notify(`Loaded version v${v.version_number}`);
                      }
                    }}
                    className="p-3 rounded-xl border border-slate-200/80 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all cursor-pointer flex items-center justify-between"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800">Version {v.version_number}</div>
                      <div className="text-[10px] text-slate-400">
                        {new Date(v.created_at).toLocaleDateString()} at {new Date(v.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                    <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded">
                      Load Snapshot
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-xs text-slate-400">No previous versions.</div>
              )}
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* INTERACTIVE EXTRACTED CANDIDATE PROFILE EDITOR */}
        {/* ========================================================= */}
        <div className="space-y-8">
          {/* 1. Personal Details Section */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                1. Personal Information & Social Links
              </h3>
              {personal.is_uncertain && (
                <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  Review Suggested (Uncertain fields: {personal.uncertain_fields?.join(', ') || 'dates'})
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Full Name</label>
                <input
                  type="text"
                  value={personal.name || ''}
                  onChange={(e) => setPersonal({ ...personal, name: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Email Address</label>
                <input
                  type="email"
                  value={personal.email || ''}
                  onChange={(e) => setPersonal({ ...personal, email: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Phone Number</label>
                <input
                  type="text"
                  value={personal.phone || ''}
                  onChange={(e) => setPersonal({ ...personal, phone: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Location / Preference</label>
                <input
                  type="text"
                  value={personal.location || ''}
                  onChange={(e) => setPersonal({ ...personal, location: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">LinkedIn Profile</label>
                <input
                  type="text"
                  value={personal.linkedin_url || ''}
                  onChange={(e) => setPersonal({ ...personal, linkedin_url: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">GitHub / Portfolio URL</label>
                <input
                  type="text"
                  value={personal.github_url || ''}
                  onChange={(e) => setPersonal({ ...personal, github_url: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div className="sm:col-span-2 md:col-span-3">
                <label className="font-bold text-slate-700 block mb-1">Professional Headline</label>
                <input
                  type="text"
                  value={personal.headline || ''}
                  onChange={(e) => setPersonal({ ...personal, headline: e.target.value })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div className="sm:col-span-2 md:col-span-3">
                <label className="font-bold text-slate-700 block mb-1">Executive Summary</label>
                <textarea
                  value={personal.summary || ''}
                  onChange={(e) => setPersonal({ ...personal, summary: e.target.value })}
                  rows={2}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 leading-relaxed focus:outline-none focus:ring-2 focus:ring-sky-500"
                ></textarea>
              </div>
            </div>
          </div>

          {/* 2. Categorized Skills Manager (6 Categories) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-sky-500" /> 2. Categorized Skills Matrix
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Deduplicated across 6 skill dimensions</p>
              </div>

              {/* Add Skill Bar */}
              <div className="flex items-center gap-2">
                <select
                  value={newSkillCategory}
                  onChange={(e) => setNewSkillCategory(e.target.value as any)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700"
                >
                  <option value="programming_languages">Programming Languages</option>
                  <option value="frameworks">Frameworks</option>
                  <option value="databases">Databases</option>
                  <option value="cloud">Cloud</option>
                  <option value="tools">Tools</option>
                  <option value="soft_skills">Soft Skills</option>
                </select>

                <input
                  type="text"
                  value={newSkillText}
                  onChange={(e) => setNewSkillText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSkill();
                    }
                  }}
                  placeholder="Add skill..."
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 w-36"
                />

                <button
                  onClick={handleAddSkill}
                  className="bg-sky-600 hover:bg-sky-700 text-white p-1.5 rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* 6 Category Grids */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[
                { key: 'programming_languages', label: 'Programming Languages', icon: Code2, color: 'sky' },
                { key: 'frameworks', label: 'Frameworks & Libraries', icon: Layers, color: 'indigo' },
                { key: 'databases', label: 'Databases & Vector Storage', icon: Database, color: 'emerald' },
                { key: 'cloud', label: 'Cloud & Infrastructure', icon: Cloud, color: 'amber' },
                { key: 'tools', label: 'Developer Tools & CI/CD', icon: Wrench, color: 'purple' },
                { key: 'soft_skills', label: 'Soft Skills & Leadership', icon: Users, color: 'slate' },
              ].map((cat) => {
                const Icon = cat.icon;
                const skillList = skills[cat.key as keyof CategorizedSkills] || [];

                return (
                  <div key={cat.key} className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 space-y-2.5">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                      <span className="flex items-center gap-1.5">
                        <Icon className="w-3.5 h-3.5 text-slate-500" />
                        {cat.label}
                      </span>
                      <span className="text-[10px] font-bold text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded">
                        {skillList.length}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5 min-h-[42px]">
                      {skillList.map((sk, idx) => (
                        <span
                          key={idx}
                          className="bg-white border border-slate-200 text-slate-800 text-[11px] font-medium px-2 py-0.5 rounded-lg flex items-center gap-1 shadow-2xs group"
                        >
                          {sk}
                          <button
                            onClick={() => handleRemoveSkill(cat.key as keyof CategorizedSkills, sk)}
                            className="text-slate-400 hover:text-rose-600 transition-colors"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                      {skillList.length === 0 && (
                        <span className="text-[11px] text-slate-400 italic">No skills added.</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 3. Work Experience Editor */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-indigo-500" /> 3. Work Experience
              </h3>
              <button
                onClick={() =>
                  setExperience([
                    ...experience,
                    {
                      id: `exp-${Date.now()}`,
                      company: 'New Company',
                      role: 'Software Engineer',
                      start_date: '2023-01',
                      end_date: 'Present',
                      is_current: true,
                      responsibilities: ['Engineered scalable web systems.'],
                      technologies: ['Python', 'FastAPI'],
                      is_uncertain: false,
                    },
                  ])
                }
                className="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Add Experience
              </button>
            </div>

            <div className="space-y-4">
              {experience.map((exp, idx) => (
                <div key={exp.id || idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1">
                      <input
                        type="text"
                        value={exp.role}
                        onChange={(e) => {
                          const updated = [...experience];
                          updated[idx].role = e.target.value;
                          setExperience(updated);
                        }}
                        placeholder="Role Title"
                        className="bg-white border border-slate-200 rounded-lg p-2 text-xs font-bold text-slate-900"
                      />
                      <input
                        type="text"
                        value={exp.company}
                        onChange={(e) => {
                          const updated = [...experience];
                          updated[idx].company = e.target.value;
                          setExperience(updated);
                        }}
                        placeholder="Company Name"
                        className="bg-white border border-slate-200 rounded-lg p-2 text-xs font-semibold text-slate-800"
                      />
                    </div>
                    <button
                      onClick={() => setExperience(experience.filter((_, i) => i !== idx))}
                      className="ml-3 p-2 text-slate-400 hover:text-rose-600 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      value={exp.start_date || ''}
                      onChange={(e) => {
                        const updated = [...experience];
                        updated[idx].start_date = e.target.value;
                        setExperience(updated);
                      }}
                      placeholder="Start Date (YYYY-MM)"
                      className="bg-white border border-slate-200 rounded-lg p-2 text-xs text-slate-700"
                    />
                    <input
                      type="text"
                      value={exp.end_date || ''}
                      onChange={(e) => {
                        const updated = [...experience];
                        updated[idx].end_date = e.target.value;
                        setExperience(updated);
                      }}
                      placeholder="End Date (or Present)"
                      className="bg-white border border-slate-200 rounded-lg p-2 text-xs text-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-500 block mb-1">
                      Key Responsibilities & Impact (One bullet per line)
                    </label>
                    <textarea
                      value={(exp.responsibilities || []).join('\n')}
                      onChange={(e) => {
                        const updated = [...experience];
                        updated[idx].responsibilities = e.target.value.split('\n').filter((l) => l.trim().length > 0);
                        setExperience(updated);
                      }}
                      rows={3}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2.5 text-xs text-slate-700 leading-relaxed"
                    ></textarea>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Education & Projects Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Education Editor */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-emerald-500" /> 4. Education
                </h3>
                <button
                  onClick={() =>
                    setEducation([
                      ...education,
                      {
                        id: `edu-${Date.now()}`,
                        degree: 'Bachelor of Science',
                        institution: 'University',
                        field_of_study: 'Computer Science',
                        graduation_year: '2022',
                      },
                    ])
                  }
                  className="text-xs font-bold text-emerald-600 hover:text-emerald-700"
                >
                  + Add
                </button>
              </div>

              <div className="space-y-3">
                {education.map((edu, idx) => (
                  <div key={edu.id || idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <input
                        type="text"
                        value={edu.institution}
                        onChange={(e) => {
                          const updated = [...education];
                          updated[idx].institution = e.target.value;
                          setEducation(updated);
                        }}
                        placeholder="Institution Name"
                        className="bg-white border border-slate-200 rounded-lg p-1.5 font-bold text-slate-900 flex-1 mr-2"
                      />
                      <button
                        onClick={() => setEducation(education.filter((_, i) => i !== idx))}
                        className="text-slate-400 hover:text-rose-600"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={edu.degree}
                        onChange={(e) => {
                          const updated = [...education];
                          updated[idx].degree = e.target.value;
                          setEducation(updated);
                        }}
                        placeholder="Degree"
                        className="bg-white border border-slate-200 rounded-lg p-1.5 text-slate-700"
                      />
                      <input
                        type="text"
                        value={edu.graduation_year || edu.end_date || ''}
                        onChange={(e) => {
                          const updated = [...education];
                          updated[idx].graduation_year = e.target.value;
                          setEducation(updated);
                        }}
                        placeholder="Graduation Year"
                        className="bg-white border border-slate-200 rounded-lg p-1.5 text-slate-700"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Projects & Certifications */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <FolderGit2 className="w-4 h-4 text-purple-500" /> 5. Projects & Certifications
                </h3>
                <button
                  onClick={() =>
                    setProjects([
                      ...projects,
                      {
                        id: `proj-${Date.now()}`,
                        name: 'New Project',
                        description: 'Project description.',
                        technologies: ['Python'],
                        links: [],
                      },
                    ])
                  }
                  className="text-xs font-bold text-purple-600 hover:text-purple-700"
                >
                  + Add Project
                </button>
              </div>

              <div className="space-y-3">
                {projects.map((proj, idx) => (
                  <div key={proj.id || idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <input
                        type="text"
                        value={proj.name}
                        onChange={(e) => {
                          const updated = [...projects];
                          updated[idx].name = e.target.value;
                          setProjects(updated);
                        }}
                        placeholder="Project Name"
                        className="bg-white border border-slate-200 rounded-lg p-1.5 font-bold text-slate-900 flex-1 mr-2"
                      />
                      <button
                        onClick={() => setProjects(projects.filter((_, i) => i !== idx))}
                        className="text-slate-400 hover:text-rose-600"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <textarea
                      value={proj.description || ''}
                      onChange={(e) => {
                        const updated = [...projects];
                        updated[idx].description = e.target.value;
                        setProjects(updated);
                      }}
                      placeholder="Project description and impact..."
                      rows={2}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-700"
                    ></textarea>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
