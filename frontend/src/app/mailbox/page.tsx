'use client';

import React, { useState, useEffect } from 'react';
import {
  Mail,
  RefreshCw,
  Plus,
  ShieldCheck,
  CheckCircle,
  AlertCircle,
  Clock,
  Sparkles,
  Inbox,
  UserCheck,
  Calendar,
  Award,
  XCircle,
  Search,
  ExternalLink,
  ChevronRight,
  Filter,
  Tag,
  Paperclip,
  Trash2,
  Lock,
  Copy,
  Check,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  MailboxConnection,
  MailboxMessage,
  MailboxStats,
  RecruiterContact,
  CommunicationDraft,
  DraftIntent,
  DraftTone,
} from '@/types';

export default function MailboxPage() {
  const [connections, setConnections] = useState<MailboxConnection[]>([]);
  const [messages, setMessages] = useState<MailboxMessage[]>([]);
  const [stats, setStats] = useState<MailboxStats | null>(null);
  const [recruiters, setRecruiters] = useState<RecruiterContact[]>([]);
  const [selectedMessage, setSelectedMessage] = useState<MailboxMessage | null>(null);
  
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [recruiterOnly, setRecruiterOnly] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'html' | 'text'>('html');

  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showAccountsModal, setShowAccountsModal] = useState<boolean>(false);
  const [showReclassifyModal, setShowReclassifyModal] = useState<boolean>(false);
  const [reclassifyCategory, setReclassifyCategory] = useState<string>('INTERVIEW_INVITATION');

  // AI Response Drafter State (Phase 8)
  const [showDrafterModal, setShowDrafterModal] = useState<boolean>(false);
  const [drafterIntent, setDrafterIntent] = useState<DraftIntent>('SCHEDULE_INTERVIEW');
  const [drafterTone, setDrafterTone] = useState<DraftTone>('PROFESSIONAL');
  const [candidateAvailability, setCandidateAvailability] = useState<string>(
    'Tuesday 2:00 PM - 5:00 PM EST\nThursday 10:00 AM - 1:00 PM EST'
  );
  const [customInstructions, setCustomInstructions] = useState<string>('');
  const [generatedDraft, setGeneratedDraft] = useState<CommunicationDraft | null>(null);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState<boolean>(false);
  const [copiedDraft, setCopiedDraft] = useState<boolean>(false);

  const loadMailboxData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [connsRes, msgsRes, statsRes, recsRes] = await Promise.all([
        api.getMailboxConnections().catch(() => []),
        api.getMailboxMessages().catch(() => []),
        api.getMailboxStats().catch(() => null),
        api.getMailboxRecruiters().catch(() => []),
      ]);

      setConnections(connsRes);
      setMessages(msgsRes);
      setStats(statsRes);
      setRecruiters(recsRes);

      if (msgsRes.length > 0) {
        setSelectedMessage((prev) => prev || msgsRes[0]);
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to load mailbox data' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMailboxData();
  }, [loadMailboxData]);

  const handleSync = async (connectionId?: string) => {
    setSyncing(true);
    setStatusMsg(null);
    try {
      const res = await api.triggerMailboxSync({ connection_id: connectionId, full_sync: false });
      const totalNew = res.reduce((acc: number, item: any) => acc + (item.synced_count || 0), 0);
      setStatusMsg({ type: 'success', text: `Sync complete: ${totalNew} new messages updated.` });
      await loadMailboxData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Synchronization failed' });
    } finally {
      setSyncing(false);
    }
  };

  const handleConnect = async (provider: 'gmail' | 'outlook') => {
    try {
      const authData = provider === 'gmail' ? await api.getGmailConnectUrl() : await api.getOutlookConnectUrl();
      
      // If mock/testing environment code:
      const simulatedCode = `mock_code_${provider}_${Date.now()}`;
      await api.handleOAuthCallback({
        code: simulatedCode,
        state: authData.state,
        provider: provider,
      });

      setStatusMsg({ type: 'success', text: `Successfully connected ${provider.toUpperCase()} mailbox!` });
      setShowAccountsModal(false);
      await loadMailboxData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || `Failed to initiate ${provider} connection` });
    }
  };

  const handleDisconnect = async (connectionId: string) => {
    try {
      await api.disconnectMailbox(connectionId);
      setStatusMsg({ type: 'success', text: 'Mailbox disconnected.' });
      await loadMailboxData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to disconnect account' });
    }
  };

  const handleManualReclassify = async () => {
    if (!selectedMessage) return;
    try {
      const updated = await api.reclassifyMailboxMessage(selectedMessage.id, {
        classification: reclassifyCategory,
        recruiter_status: 'RECRUITER_CONFIRMED',
      });
      setSelectedMessage(updated);
      setShowReclassifyModal(false);
      setStatusMsg({ type: 'success', text: `Message reclassified as ${reclassifyCategory.replace('_', ' ')}` });
      await loadMailboxData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Reclassification failed' });
    }
  };

  const filteredMessages = messages.filter((msg) => {
    if (categoryFilter !== 'ALL' && msg.classification !== categoryFilter) {
      return false;
    }
    if (recruiterOnly && !msg.is_recruiter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchSubject = msg.subject.toLowerCase().includes(q);
      const matchSender = (msg.sender_name || msg.sender_email).toLowerCase().includes(q);
      const matchCompany = (msg.detected_company || '').toLowerCase().includes(q);
      if (!matchSubject && !matchSender && !matchCompany) {
        return false;
      }
    }
    return true;
  });

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'OFFER':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'INTERVIEW_INVITATION':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'ASSESSMENT_REQUEST':
      case 'ASSESSMENT':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/30';
      case 'REJECTION':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'APPLICATION_CONFIRMATION':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'RECRUITER_OUTREACH':
      case 'RECRUITER_MESSAGE':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-700/50 text-slate-400 border-slate-600/30';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Mailbox Intelligence & Recruiter Hub</h1>
            <span className="bg-sky-500/20 text-sky-400 border border-sky-500/30 text-xs font-semibold px-2 py-0.5 rounded-full">
              Phase 7 OAuth
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Connect Gmail and Outlook securely with read-only scopes. AI automatically extracts interview invites, offers, assessments, and keeps application records in sync.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleSync()}
            disabled={syncing || connections.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-medium border border-slate-700 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin text-sky-400' : ''}`} />
            <span>{syncing ? 'Syncing...' : 'Sync Mailbox'}</span>
          </button>

          <button
            onClick={() => setShowAccountsModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-sky-600/20"
          >
            <Plus className="w-4 h-4" />
            <span>Connect Accounts ({connections.length})</span>
          </button>
        </div>
      </div>

      {/* Notification / Status Message */}
      {statusMsg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between text-sm ${
            statusMsg.type === 'success'
              ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
              : 'bg-rose-950/60 border border-rose-800 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMsg.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{statusMsg.text}</span>
          </div>
          <button onClick={() => setStatusMsg(null)} className="text-slate-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Accounts</span>
            <Mail className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-white mt-1">{stats?.total_connections || connections.length}</div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Active
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Job Emails</span>
            <Sparkles className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-white mt-1">{stats?.job_related_messages || 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Classified</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Interviews</span>
            <Calendar className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-400 mt-1">{stats?.interview_invitations || 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Invited</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Offers</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400 mt-1">{stats?.offers || 0}</div>
          <div className="text-[11px] text-emerald-400 mt-1">Received</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Recruiters</span>
            <UserCheck className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-purple-400 mt-1">{stats?.recruiter_messages || recruiters.length}</div>
          <div className="text-[11px] text-slate-500 mt-1">Contacts</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
            <span>Rejections</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-400 mt-1">{stats?.rejections || 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Processed</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          {[
            { key: 'ALL', label: 'All Emails' },
            { key: 'INTERVIEW_INVITATION', label: 'Interviews' },
            { key: 'OFFER', label: 'Offers' },
            { key: 'ASSESSMENT_REQUEST', label: 'Assessments' },
            { key: 'REJECTION', label: 'Rejections' },
            { key: 'RECRUITER_OUTREACH', label: 'Recruiters' },
            { key: 'APPLICATION_CONFIRMATION', label: 'Confirmations' },
          ].map((cat) => (
            <button
              key={cat.key}
              onClick={() => setCategoryFilter(cat.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0 ${
                categoryFilter === cat.key
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search sender, company, subject..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white pl-9 pr-3 py-1.5 rounded-xl text-xs focus:outline-none focus:border-sky-500"
            />
          </div>

          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none shrink-0 bg-slate-800 px-3 py-1.5 rounded-xl border border-slate-700">
            <input
              type="checkbox"
              checked={recruiterOnly}
              onChange={(e) => setRecruiterOnly(e.target.checked)}
              className="rounded bg-slate-700 border-slate-600 text-sky-500 focus:ring-0"
            />
            <span>Recruiters Only</span>
          </label>
        </div>
      </div>

      {/* Split Screen Master-Detail Mailbox Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Side: Message List (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col">
          <div className="p-3 border-b border-slate-800 bg-slate-800/40 flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Inbox Messages ({filteredMessages.length})</span>
            <span className="text-[11px] text-slate-500">Encrypted at rest</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 max-h-[650px]">
            {loading ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-sky-400" />
                Loading mailbox messages...
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                <Inbox className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                No messages found matching criteria.
              </div>
            ) : (
              filteredMessages.map((msg) => {
                const isSelected = selectedMessage?.id === msg.id;
                return (
                  <div
                    key={msg.id}
                    onClick={() => setSelectedMessage(msg)}
                    className={`p-4 cursor-pointer transition flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-sky-950/40 border-l-4 border-sky-500'
                        : 'hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-xs text-white truncate max-w-[180px]">
                          {msg.sender_name || msg.sender_email}
                        </span>
                        {msg.is_recruiter && (
                          <span className="bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] px-1 py-0.2 rounded font-medium">
                            Recruiter
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500">
                        {new Date(msg.received_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>

                    <div className="text-xs font-medium text-slate-200 truncate">{msg.subject}</div>

                    <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {msg.snippet || msg.body_text || 'No preview available'}
                    </p>

                    <div className="flex items-center justify-between mt-1">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getCategoryBadgeClass(
                          msg.classification
                        )}`}
                      >
                        {msg.classification.replace(/_/g, ' ')}
                      </span>

                      {msg.detected_company && (
                        <span className="text-[11px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                          {msg.detected_company}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Message Detail Viewer (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col">
          {selectedMessage ? (
            <div className="flex-1 flex flex-col">
              {/* Header */}
              <div className="p-5 border-b border-slate-800 space-y-3 bg-slate-800/20">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-white tracking-tight leading-snug">
                      {selectedMessage.subject}
                    </h2>
                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                      <span>From: <strong className="text-slate-200">{selectedMessage.sender_name || selectedMessage.sender_email}</strong> &lt;{selectedMessage.sender_email}&gt;</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => {
                        setDrafterIntent(
                          selectedMessage.classification === 'INTERVIEW_INVITATION'
                            ? 'SCHEDULE_INTERVIEW'
                            : selectedMessage.classification === 'OFFER'
                            ? 'NEGOTIATE_OFFER'
                            : selectedMessage.classification === 'RECRUITER_OUTREACH'
                            ? 'COLD_REPLY'
                            : 'GENERAL'
                        );
                        setGeneratedDraft(null);
                        setShowDrafterModal(true);
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-bold rounded-lg shadow-sm transition"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>AI Reply Drafter</span>
                    </button>
                    <button
                      onClick={() => {
                        setReclassifyCategory(selectedMessage.classification);
                        setShowReclassifyModal(true);
                      }}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition"
                    >
                      Reclassify
                    </button>
                  </div>
                </div>

                {/* Metadata & Classification pill */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                  <span
                    className={`font-semibold px-2.5 py-0.5 rounded-full border ${getCategoryBadgeClass(
                      selectedMessage.classification
                    )}`}
                  >
                    {selectedMessage.classification.replace(/_/g, ' ')}
                  </span>

                  {selectedMessage.detected_company && (
                    <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                      Company: {selectedMessage.detected_company}
                    </span>
                  )}

                  {selectedMessage.detected_job_title && (
                    <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                      Role: {selectedMessage.detected_job_title}
                    </span>
                  )}

                  {selectedMessage.has_attachments && (
                    <span className="flex items-center gap-1 bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">
                      <Paperclip className="w-3 h-3" />
                      Attachments
                    </span>
                  )}

                  <span className="text-slate-500 ml-auto text-[11px]">
                    {new Date(selectedMessage.received_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Safe Security Notice */}
              <div className="px-5 py-2 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>XSS-Sanitized Safe Content • Read-Only Scope</span>
                </div>

                <div className="flex items-center gap-1 bg-slate-800 p-0.5 rounded-lg">
                  <button
                    onClick={() => setViewMode('html')}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
                      viewMode === 'html' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Rich View
                  </button>
                  <button
                    onClick={() => setViewMode('text')}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
                      viewMode === 'text' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Plain Text
                  </button>
                </div>
              </div>

              {/* Body Content */}
              <div className="flex-1 p-6 overflow-y-auto max-h-[500px]">
                {viewMode === 'html' && selectedMessage.body_html ? (
                  <div
                    className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: selectedMessage.body_html }}
                  />
                ) : (
                  <pre className="whitespace-pre-wrap font-sans text-slate-300 text-sm leading-relaxed">
                    {selectedMessage.body_text || selectedMessage.snippet || 'No email content available'}
                  </pre>
                )}

                {/* Attachments Section if present */}
                {selectedMessage.attachments_metadata && selectedMessage.attachments_metadata.length > 0 && (
                  <div className="mt-8 pt-4 border-t border-slate-800">
                    <h4 className="text-xs font-semibold text-slate-400 mb-2 flex items-center gap-1.5">
                      <Paperclip className="w-3.5 h-3.5" /> Attachments ({selectedMessage.attachments_metadata.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedMessage.attachments_metadata.map((att: any, idx: number) => (
                        <div
                          key={idx}
                          className="bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-xs text-slate-300 flex items-center gap-2"
                        >
                          <Paperclip className="w-3.5 h-3.5 text-slate-500" />
                          <span>{att.filename || 'Attachment'}</span>
                          <span className="text-[10px] text-slate-500">({Math.round((att.size || 0) / 1024)} KB)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <Mail className="w-12 h-12 mb-3 text-slate-700" />
              <h3 className="text-base font-semibold text-slate-300">Select an email to view details</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Choose any recruiter message, interview invitation, or application update from the left inbox list.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Connected Accounts Modal */}
      {showAccountsModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white">Manage Mailbox Accounts</h3>
                <p className="text-xs text-slate-400 mt-0.5">OAuth 2.0 Read-Only Mailbox Connections</p>
              </div>
              <button
                onClick={() => setShowAccountsModal(false)}
                className="text-slate-400 hover:text-white text-xl font-bold"
              >
                &times;
              </button>
            </div>

            {/* Active Connections List */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Connections</h4>
              {connections.length === 0 ? (
                <div className="p-4 bg-slate-800/40 rounded-xl text-center text-xs text-slate-400">
                  No active mailboxes connected yet.
                </div>
              ) : (
                connections.map((conn) => (
                  <div
                    key={conn.id}
                    className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-xl flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold text-white flex items-center gap-1.5">
                        <span>{conn.provider}</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      </div>
                      <div className="text-slate-400">{conn.email_address}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        Last sync: {conn.last_sync_at ? new Date(conn.last_sync_at).toLocaleString() : 'Never'}
                      </div>
                    </div>

                    <button
                      onClick={() => handleDisconnect(conn.id)}
                      className="p-2 text-rose-400 hover:bg-rose-950/40 rounded-lg transition"
                      title="Disconnect Account"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Connect Providers */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Connect New Account</h4>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleConnect('gmail')}
                  className="p-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-white transition"
                >
                  <Mail className="w-4 h-4 text-rose-400" />
                  <span>Connect Gmail</span>
                </button>

                <button
                  onClick={() => handleConnect('outlook')}
                  className="p-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-white transition"
                >
                  <Mail className="w-4 h-4 text-sky-400" />
                  <span>Connect Outlook</span>
                </button>
              </div>
            </div>

            <div className="p-3 bg-slate-800/40 rounded-xl border border-slate-700/40 text-[11px] text-slate-400 leading-relaxed">
              <Lock className="w-3.5 h-3.5 inline mr-1 text-emerald-400" />
              <strong>Privacy Guarantee:</strong> Only read-only scopes (<code>gmail.readonly</code> & <code>Mail.Read</code>) are requested. Tokens are symmetrically encrypted using Fernet at rest and never shared with LLMs.
            </div>
          </div>
        </div>
      )}

      {/* Manual Reclassification Modal */}
      {showReclassifyModal && selectedMessage && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Reclassify Email Message</h3>
            <p className="text-xs text-slate-400">
              Override the classification category for: <strong className="text-slate-200">{selectedMessage.subject}</strong>
            </p>

            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-300">Select Category</label>
              <select
                value={reclassifyCategory}
                onChange={(e) => setReclassifyCategory(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-sky-500"
              >
                <option value="INTERVIEW_INVITATION">Interview Invitation</option>
                <option value="OFFER">Job Offer</option>
                <option value="ASSESSMENT_REQUEST">Online Assessment Request</option>
                <option value="REJECTION">Application Rejection</option>
                <option value="RECRUITER_OUTREACH">Recruiter Direct Outreach</option>
                <option value="APPLICATION_CONFIRMATION">Application Confirmation</option>
                <option value="NOT_JOB_RELATED">Not Job Related</option>
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3">
              <button
                onClick={() => setShowReclassifyModal(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleManualReclassify}
                className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-medium"
              >
                Save Classification
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Response Drafter Modal (Phase 8) */}
      {showDrafterModal && selectedMessage && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="bg-sky-500/20 text-sky-400 border border-sky-500/30 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                  Strict Human-in-the-Loop AI
                </span>
                <h3 className="text-lg font-bold text-white mt-1.5 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-sky-400" />
                  Contextual AI Response Drafter
                </h3>
              </div>
              <button
                onClick={() => setShowDrafterModal(false)}
                className="text-slate-400 hover:text-white text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800"
              >
                Close
              </button>
            </div>

            {/* Recipient context */}
            <div className="p-3.5 bg-slate-800/40 rounded-xl border border-slate-700/50 text-xs text-slate-300 space-y-1">
              <div><strong>To:</strong> {selectedMessage.sender_name || selectedMessage.sender_email} &lt;{selectedMessage.sender_email}&gt;</div>
              <div><strong>Regarding:</strong> {selectedMessage.subject}</div>
            </div>

            {/* Intent & Tone selector */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Communication Intent</label>
                <select
                  value={drafterIntent}
                  onChange={(e) => setDrafterIntent(e.target.value as any)}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-sky-500"
                >
                  <option value="SCHEDULE_INTERVIEW">Schedule Interview (Provide Slots)</option>
                  <option value="THANK_YOU">Post-Interview Thank You</option>
                  <option value="NEGOTIATE_OFFER">Negotiate Job Offer</option>
                  <option value="FOLLOW_UP">Follow Up on Application</option>
                  <option value="ACCEPT_OFFER">Accept Job Offer</option>
                  <option value="DECLINE_OFFER">Decline Job Offer</option>
                  <option value="COLD_REPLY">Reply to Recruiter Outreach</option>
                  <option value="GENERAL">General Professional Reply</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Desired Tone</label>
                <select
                  value={drafterTone}
                  onChange={(e) => setDrafterTone(e.target.value as any)}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-sky-500"
                >
                  <option value="PROFESSIONAL">Professional (Polished Standard)</option>
                  <option value="CONFIDENT">Confident (Assertive Track Record)</option>
                  <option value="ENTHUSIASTIC">Enthusiastic (High Energy / Passion)</option>
                  <option value="ASSERTIVE">Assertive (Direct / Negotiation)</option>
                  <option value="CONCISE">Concise (Brief / Executive)</option>
                </select>
              </div>
            </div>

            {drafterIntent === 'SCHEDULE_INTERVIEW' && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Your Availability Slots (One per line)</label>
                <textarea
                  rows={2}
                  value={candidateAvailability}
                  onChange={(e) => setCandidateAvailability(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-3 py-2 rounded-xl text-xs font-mono focus:outline-none focus:border-sky-500"
                  placeholder="e.g. Tuesday 2:00 PM - 5:00 PM EST"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Special Instructions or Salary Targets (Optional)</label>
              <input
                type="text"
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                placeholder="e.g. Mention 10 years distributed systems experience or target $170k base"
                className="w-full bg-slate-800 border border-slate-700 text-white px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={async () => {
                  setIsGeneratingDraft(true);
                  try {
                    const slots = candidateAvailability.split('\n').map((s) => s.trim()).filter(Boolean);
                    const draft = await api.generateResponseDraft({
                      recruiter_name: selectedMessage.sender_name || undefined,
                      recruiter_email: selectedMessage.sender_email,
                      company_name: selectedMessage.detected_company || undefined,
                      job_title: selectedMessage.detected_job_title || undefined,
                      application_id: selectedMessage.application_id || undefined,
                      message_id: selectedMessage.id,
                      intent: drafterIntent,
                      tone: drafterTone,
                      candidate_availability: slots,
                      custom_instructions: customInstructions || undefined,
                      incoming_email_snippet: selectedMessage.snippet || selectedMessage.body_text?.substring(0, 300),
                    });
                    setGeneratedDraft(draft);
                  } catch (err: any) {
                    alert(`Failed to generate draft: ${err.message || err}`);
                  } finally {
                    setIsGeneratingDraft(false);
                  }
                }}
                disabled={isGeneratingDraft}
                className="bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>{isGeneratingDraft ? 'Generating Draft...' : 'Generate AI Reply Draft'}</span>
              </button>
            </div>

            {/* Generated Draft Output Area */}
            {generatedDraft && (
              <div className="p-4 bg-slate-800/80 rounded-2xl border border-sky-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400">Generated Subject Line</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(`${generatedDraft.subject}\n\n${generatedDraft.body_text}`);
                        setCopiedDraft(true);
                        setTimeout(() => setCopiedDraft(false), 2000);
                      }}
                      className="inline-flex items-center gap-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold px-3 py-1 rounded-lg transition"
                    >
                      {copiedDraft ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedDraft ? 'Copied Full Draft' : 'Copy All'}</span>
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          const approved = await api.approveDraft(generatedDraft.id);
                          setGeneratedDraft(approved);
                          alert('Draft approved! Marked ready for sending.');
                        } catch (err: any) {
                          alert(`Approval failed: ${err.message || err}`);
                        }
                      }}
                      className={`inline-flex items-center gap-1 text-xs font-bold px-3 py-1 rounded-lg transition ${
                        generatedDraft.is_approved
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                      }`}
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>{generatedDraft.is_approved ? 'Approved' : 'Approve Draft'}</span>
                    </button>
                  </div>
                </div>

                <input
                  type="text"
                  value={generatedDraft.subject}
                  onChange={(e) => setGeneratedDraft({ ...generatedDraft, subject: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white font-medium"
                />

                <textarea
                  rows={8}
                  value={generatedDraft.body_text}
                  onChange={(e) => setGeneratedDraft({ ...generatedDraft, body_text: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 leading-relaxed font-sans focus:outline-none focus:border-sky-500"
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
