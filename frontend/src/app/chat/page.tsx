'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Header } from '@/components/Header';
import {
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  Briefcase,
  Plus,
  Trash2,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  X,
  Building,
  MapPin,
  DollarSign,
  Wrench,
  BarChart3,
  Flame,
  MessageSquare
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  ChatMessage,
  ChatConversation,
  ChatJobCard,
  ChatMatchScorecard,
  ChatMissingSkillsData,
} from '@/types';

const defaultStarterPrompts = [
  { text: 'Find remote Python & FastAPI developer jobs', icon: Sparkles },
  { text: 'Show my best matching jobs based on my resume', icon: Flame },
  { text: 'What skills am I missing for senior software roles?', icon: AlertTriangle },
  { text: 'How many applications have I submitted so far?', icon: BarChart3 },
];

export default function ChatPage() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [selectedJob, setSelectedJob] = useState<ChatJobCard | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load user conversations on initial mount
  useEffect(() => {
    async function loadConversations() {
      try {
        setLoadingConversations(true);
        const convs = await api.getConversations();
        if (convs && convs.length > 0) {
          setConversations(convs);
          setActiveConversationId(convs[0].id);
        } else {
          // Create initial default conversation
          const newConv = await api.createConversation({ title: 'New Job Search Chat' });
          setConversations([newConv]);
          setActiveConversationId(newConv.id);
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      } finally {
        setLoadingConversations(false);
      }
    }
    loadConversations();
  }, []);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId) return;

    async function loadConversationMessages() {
      try {
        setLoading(true);
        const convDetail = await api.getConversation(activeConversationId!);
        if (convDetail && convDetail.messages) {
          if (convDetail.messages.length === 0) {
            // Add greeting for empty conversation
            setMessages([
              {
                id: 'welcome-1',
                conversation_id: activeConversationId!,
                role: 'assistant',
                sender_type: 'ASSISTANT',
                content:
                  '👋 Hello! I am your AI Job Search & Matching Copilot.\n\nI can help you:\n• Discover high-fit jobs across 10+ integrated platforms\n• Calculate explainable match scores tailored to your resume\n• Analyze missing required & preferred skills\n• Track application statuses and history\n\nWhat would you like to explore today?',
                structured_payload: {
                  suggestions: [
                    'Find remote Python developer jobs',
                    'Show my best matching jobs',
                    'What skills am I missing?',
                    'How many applications have I submitted?',
                  ],
                },
                created_at: new Date().toISOString(),
              },
            ]);
          } else {
            setMessages(convDetail.messages);
          }
        }
      } catch (err) {
        console.error('Failed to load conversation details:', err);
      } finally {
        setLoading(false);
      }
    }

    loadConversationMessages();
  }, [activeConversationId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleCreateNewConversation() {
    try {
      const newConv = await api.createConversation({
        title: `Chat ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
      });
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
      setMessages([
        {
          id: 'welcome-new',
          conversation_id: newConv.id,
          role: 'assistant',
          sender_type: 'ASSISTANT',
          content: 'Started a fresh session! What job or matching criteria should we explore?',
          structured_payload: {
            suggestions: [
              'Find remote Python developer jobs',
              'Show my best matching jobs',
              'What skills am I missing?',
            ],
          },
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      alert(`Could not create conversation: ${err.message || 'Unknown error'}`);
    }
  }

  async function handleDeleteConversation(convId: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation session?')) return;

    try {
      await api.deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (activeConversationId === convId) {
        if (remaining.length > 0) {
          setActiveConversationId(remaining[0].id);
        } else {
          handleCreateNewConversation();
        }
      }
    } catch (err: any) {
      alert(`Failed to delete conversation: ${err.message}`);
    }
  }

  async function handleSend(textToSend?: string) {
    const text = textToSend || input;
    if (!text.trim() || loading || !activeConversationId) return;

    const userMsg: ChatMessage = {
      id: `local-user-${Date.now()}`,
      conversation_id: activeConversationId,
      role: 'user',
      sender_type: 'USER',
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const assistantReply: ChatMessage = await api.sendMessageToConversation(
        activeConversationId,
        text
      );
      setMessages((prev) => [...prev, assistantReply]);

      // Update conversation title if first user message
      if (messages.length <= 1) {
        const shortTitle = text.length > 28 ? `${text.slice(0, 28)}...` : text;
        setConversations((prev) =>
          prev.map((c) => (c.id === activeConversationId ? { ...c, title: shortTitle } : c))
        );
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        conversation_id: activeConversationId,
        role: 'assistant',
        sender_type: 'ASSISTANT',
        content: `⚠️ Encountered an issue querying assistant: ${err.message || 'Please check backend services.'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-slate-50">
      <Header
        title="AI Chatbot & Conversational Assistant"
        subtitle="Conversational job discovery, explainable match evaluations, and skills gap analysis"
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sessions Sidebar */}
        <div
          className={`${
            sidebarOpen ? 'w-72' : 'w-0'
          } transition-all duration-200 border-r border-slate-200 bg-white flex flex-col overflow-hidden shrink-0`}
        >
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-sky-600" />
              Chat Sessions
            </h2>
            <button
              onClick={handleCreateNewConversation}
              className="flex items-center gap-1 bg-sky-50 hover:bg-sky-100 text-sky-700 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors border border-sky-200/60 cursor-pointer"
              title="Start New Chat"
            >
              <Plus className="w-3.5 h-3.5" />
              New
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loadingConversations ? (
              <div className="p-4 text-center text-xs text-slate-400">Loading sessions...</div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400">No active conversations.</div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConversationId;
                return (
                  <div
                    key={conv.id}
                    onClick={() => setActiveConversationId(conv.id)}
                    className={`group flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                      isActive
                        ? 'bg-sky-500/10 text-sky-900 font-semibold border border-sky-200 shadow-2xs'
                        : 'text-slate-600 hover:bg-slate-100/80 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <div
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          isActive ? 'bg-sky-500' : 'bg-slate-300'
                        }`}
                      />
                      <span className="truncate">{conv.title || 'Untitled Session'}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 rounded-md transition-opacity cursor-pointer"
                      title="Delete Session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <div className="p-3 border-t border-slate-100 bg-slate-50/50 text-[11px] text-slate-400 flex items-center justify-between">
            <span>OmniRoute AI Gateway</span>
            <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Active
            </span>
          </div>
        </div>

        {/* Main Chat Thread */}
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50 relative">
          {/* Top Session Sub-Header */}
          <div className="bg-white/80 backdrop-blur-xs border-b border-slate-200 px-6 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-slate-500 hover:text-slate-800 p-1.5 rounded-lg hover:bg-slate-100 text-xs font-medium border border-slate-200 cursor-pointer"
              >
                {sidebarOpen ? 'Hide Sessions' : 'Show Sessions'}
              </button>
              <div className="h-4 w-[1px] bg-slate-200" />
              <span className="text-xs font-semibold text-slate-700">
                {conversations.find((c) => c.id === activeConversationId)?.title || 'Current Session'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium border border-slate-200">
                Controlled Tools: 17
              </span>
            </div>
          </div>

          {/* Messages List */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl w-full mx-auto">
            {messages.map((m) => {
              const isUser = m.role === 'user' || m.sender_type === 'USER';
              const payload = m.structured_payload;
              const jobCards: ChatJobCard[] = payload?.job_cards || [];
              const scorecard: ChatMatchScorecard | undefined = payload?.match_scorecard;
              const missingSkills: ChatMissingSkillsData | undefined = payload?.missing_skills_analysis;
              const executedTools: string[] = payload?.executed_tools || [];
              const suggestions: string[] = payload?.suggestions || [];

              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-2`}
                >
                  <div
                    className={`flex items-start gap-3.5 max-w-[90%] md:max-w-[85%] ${
                      isUser ? 'flex-row-reverse' : 'flex-row'
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-white font-bold text-xs shadow-xs ${
                        isUser
                          ? 'bg-slate-800 border border-slate-700'
                          : 'bg-gradient-to-tr from-sky-600 to-indigo-600'
                      }`}
                    >
                      {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    {/* Content Box */}
                    <div className="flex flex-col space-y-2 w-full">
                      <div
                        className={`rounded-2xl p-4.5 text-sm leading-relaxed whitespace-pre-line shadow-xs ${
                          isUser
                            ? 'bg-slate-900 text-white rounded-tr-none'
                            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                        }`}
                      >
                        {m.content}
                      </div>

                      {/* Tool Execution Badges */}
                      {!isUser && executedTools.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                          <span className="text-[11px] text-slate-400 flex items-center gap-1">
                            <Wrench className="w-3 h-3 text-slate-400" />
                            Executed:
                          </span>
                          {executedTools.map((t, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Render Job Cards Carousel/Grid */}
                      {!isUser && jobCards.length > 0 && (
                        <div className="pt-2 space-y-2.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                              <Briefcase className="w-3.5 h-3.5 text-sky-600" />
                              Discovered Jobs ({jobCards.length})
                            </span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {jobCards.map((job, idx) => {
                              const score = job.overall_score;
                              return (
                                <div
                                  key={job.job_id || idx}
                                  className="bg-white border border-slate-200 hover:border-sky-300 rounded-xl p-3.5 shadow-2xs hover:shadow-sm transition-all flex flex-col justify-between space-y-2.5"
                                >
                                  <div>
                                    <div className="flex items-start justify-between gap-2">
                                      <h4 className="text-xs font-bold text-slate-900 line-clamp-1">
                                        {job.title}
                                      </h4>
                                      {score !== undefined && (
                                        <span
                                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                            score >= 80
                                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                              : score >= 60
                                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                                          }`}
                                        >
                                          {Math.round(score)}% Match
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-xs text-slate-500 font-medium flex items-center gap-1 mt-0.5">
                                      <Building className="w-3 h-3 text-slate-400" />
                                      <span>{job.company}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-1.5 flex-wrap">
                                      <span className="inline-flex items-center gap-0.5">
                                        <MapPin className="w-3 h-3 text-slate-400" />
                                        {job.location}
                                      </span>
                                      <span className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-medium text-slate-600">
                                        {job.remote_type}
                                      </span>
                                      {job.salary_range && job.salary_range !== 'Not specified' && (
                                        <span className="inline-flex items-center gap-0.5 text-emerald-700 font-medium">
                                          <DollarSign className="w-3 h-3" />
                                          {job.salary_range}
                                        </span>
                                      )}
                                    </div>

                                    {/* Matched skills pill preview */}
                                    {job.matched_skills && job.matched_skills.length > 0 && (
                                      <div className="flex items-center gap-1 flex-wrap mt-2">
                                        {job.matched_skills.slice(0, 3).map((sk, sIdx) => (
                                          <span
                                            key={sIdx}
                                            className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200/60 px-1.5 py-0.5 rounded font-medium"
                                          >
                                            ✓ {sk}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                                    <button
                                      onClick={() => setSelectedJob(job)}
                                      className="text-sky-600 hover:text-sky-800 font-semibold inline-flex items-center gap-0.5 text-[11px] cursor-pointer"
                                    >
                                      View Details <ChevronRight className="w-3 h-3" />
                                    </button>
                                    {job.apply_url && (
                                      <a
                                        href={job.apply_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-900"
                                      >
                                        Apply Source <ExternalLink className="w-3 h-3 text-slate-400" />
                                      </a>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Render Match Scorecard Widget */}
                      {!isUser && scorecard && (
                        <div className="pt-2">
                          <div className="bg-white border border-sky-200 rounded-xl p-4 shadow-sm space-y-3">
                            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                              <div>
                                <h4 className="text-xs font-bold text-slate-900">
                                  Explainable Match Scorecard
                                </h4>
                                <p className="text-[11px] text-slate-500">
                                  {scorecard.job_title} at {scorecard.company}
                                </p>
                              </div>
                              <div className="text-right">
                                <span className="text-lg font-black text-sky-700">
                                  {Math.round(scorecard.overall_score)}%
                                </span>
                                <span className="block text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                                  {scorecard.recommendation.replace('_', ' ')}
                                </span>
                              </div>
                            </div>

                            {/* Dimension Progress Bars */}
                            {scorecard.dimension_scores && (
                              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                                <div>
                                  <div className="flex justify-between text-[11px] text-slate-600 mb-0.5">
                                    <span>Skills (35%)</span>
                                    <span className="font-semibold">
                                      {Math.round(scorecard.dimension_scores.skills_score)}%
                                    </span>
                                  </div>
                                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-sky-500 rounded-full"
                                      style={{ width: `${scorecard.dimension_scores.skills_score}%` }}
                                    />
                                  </div>
                                </div>

                                <div>
                                  <div className="flex justify-between text-[11px] text-slate-600 mb-0.5">
                                    <span>Experience (20%)</span>
                                    <span className="font-semibold">
                                      {Math.round(scorecard.dimension_scores.experience_score)}%
                                    </span>
                                  </div>
                                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-indigo-500 rounded-full"
                                      style={{ width: `${scorecard.dimension_scores.experience_score}%` }}
                                    />
                                  </div>
                                </div>

                                <div>
                                  <div className="flex justify-between text-[11px] text-slate-600 mb-0.5">
                                    <span>Role Fit (15%)</span>
                                    <span className="font-semibold">
                                      {Math.round(scorecard.dimension_scores.role_relevance_score)}%
                                    </span>
                                  </div>
                                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-emerald-500 rounded-full"
                                      style={{ width: `${scorecard.dimension_scores.role_relevance_score}%` }}
                                    />
                                  </div>
                                </div>

                                <div>
                                  <div className="flex justify-between text-[11px] text-slate-600 mb-0.5">
                                    <span>Location/Remote (15%)</span>
                                    <span className="font-semibold">
                                      {Math.round(scorecard.dimension_scores.location_remote_score)}%
                                    </span>
                                  </div>
                                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-violet-500 rounded-full"
                                      style={{ width: `${scorecard.dimension_scores.location_remote_score}%` }}
                                    />
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Key Strengths & Gaps */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-[11px]">
                              {scorecard.key_strengths && scorecard.key_strengths.length > 0 && (
                                <div className="bg-emerald-50/70 border border-emerald-100 p-2.5 rounded-lg space-y-1">
                                  <span className="font-bold text-emerald-800 flex items-center gap-1">
                                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                    Strengths
                                  </span>
                                  <ul className="list-disc list-inside text-emerald-900 space-y-0.5">
                                    {scorecard.key_strengths.slice(0, 3).map((st, sIdx) => (
                                      <li key={sIdx}>{st}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {scorecard.risks_or_gaps && scorecard.risks_or_gaps.length > 0 && (
                                <div className="bg-amber-50/70 border border-amber-100 p-2.5 rounded-lg space-y-1">
                                  <span className="font-bold text-amber-800 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3 text-amber-600" />
                                    Gaps / Risks
                                  </span>
                                  <ul className="list-disc list-inside text-amber-900 space-y-0.5">
                                    {scorecard.risks_or_gaps.slice(0, 3).map((rg, rIdx) => (
                                      <li key={rIdx}>{rg}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Render Missing Skills Analysis */}
                      {!isUser && missingSkills && (
                        <div className="pt-2">
                          <div className="bg-white border border-rose-200 rounded-xl p-4 shadow-sm space-y-2.5">
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                                Missing Skills Analysis
                              </h4>
                              <span className="text-[11px] font-semibold text-rose-600">
                                Gap: {Math.round(missingSkills.skills_gap_percentage || 0)}%
                              </span>
                            </div>

                            {missingSkills.missing_required_skills &&
                              missingSkills.missing_required_skills.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block mb-1">
                                    Required Skills to Acquire:
                                  </span>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    {missingSkills.missing_required_skills.map((sk, idx) => (
                                      <span
                                        key={idx}
                                        className="text-[11px] bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-md font-medium"
                                      >
                                        ✗ {sk}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                            {missingSkills.missing_preferred_skills &&
                              missingSkills.missing_preferred_skills.length > 0 && (
                                <div className="pt-1">
                                  <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block mb-1">
                                    Preferred Nice-to-Have Skills:
                                  </span>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    {missingSkills.missing_preferred_skills.map((sk, idx) => (
                                      <span
                                        key={idx}
                                        className="text-[11px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-md font-medium"
                                      >
                                        + {sk}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                            {missingSkills.upskilling_recommendation && (
                              <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100">
                                💡 <strong>Recommendation:</strong> {missingSkills.upskilling_recommendation}
                              </p>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Clickable Suggestions */}
                      {!isUser && suggestions.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap pt-1.5">
                          {suggestions.map((sug, sIdx) => (
                            <button
                              key={sIdx}
                              onClick={() => handleSend(sug)}
                              className="text-[11px] font-medium bg-white hover:bg-sky-50 text-slate-700 hover:text-sky-700 border border-slate-200 hover:border-sky-300 px-2.5 py-1 rounded-full transition-all shadow-2xs cursor-pointer"
                            >
                              💬 {sug}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Loading / Typing Indicator */}
            {loading && (
              <div className="flex items-start gap-3.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-xs">
                  <Bot className="w-4 h-4 animate-spin" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none p-4 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
                  <span className="w-2 h-2 rounded-full bg-sky-500 animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]" />
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]" />
                  <span className="font-medium">
                    AI Assistant is executing tools and synthesizing insights...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Starter Prompts */}
          {messages.length <= 2 && (
            <div className="max-w-4xl w-full mx-auto px-6 pb-2">
              <div className="flex items-center gap-2 overflow-x-auto py-1 no-scrollbar">
                {defaultStarterPrompts.map((qp, i) => {
                  const Icon = qp.icon;
                  return (
                    <button
                      key={i}
                      onClick={() => handleSend(qp.text)}
                      className="flex items-center gap-1.5 shrink-0 bg-white hover:bg-sky-50 text-slate-700 hover:text-sky-700 border border-slate-200 hover:border-sky-300 text-xs px-3 py-1.5 rounded-full transition-colors shadow-2xs font-medium cursor-pointer"
                    >
                      <Icon className="w-3.5 h-3.5 text-sky-500" />
                      <span>{qp.text}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Message Input Form */}
          <div className="border-t border-slate-200 bg-white p-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="max-w-4xl mx-auto flex items-center gap-3"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about matching jobs, skills gap, salary ranges, or application status..."
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition-all text-slate-900 placeholder:text-slate-400"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-semibold p-3 rounded-xl shadow-sm transition-colors shrink-0 cursor-pointer"
                title="Send Message"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Modal: Job Details Preview */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[85vh] overflow-y-auto space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">{selectedJob.title}</h3>
                <p className="text-xs text-slate-600 font-medium">{selectedJob.company}</p>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-600 flex-wrap">
              <span className="inline-flex items-center gap-1 font-medium">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {selectedJob.location} ({selectedJob.remote_type})
              </span>
              <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
                <DollarSign className="w-3.5 h-3.5" />
                {selectedJob.salary_range || 'Salary not disclosed'}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-700">
                Source: {selectedJob.source}
              </span>
            </div>

            {selectedJob.required_skills && selectedJob.required_skills.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-800 mb-1.5">Required Skills</h4>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {selectedJob.required_skills.map((sk, idx) => (
                    <span
                      key={idx}
                      className="text-xs bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded-md"
                    >
                      {sk}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedJob.description_snippet && (
              <div>
                <h4 className="text-xs font-bold text-slate-800 mb-1.5">Description</h4>
                <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 p-3 rounded-xl border border-slate-100">
                  {selectedJob.description_snippet}
                </p>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                Close
              </button>
              {selectedJob.apply_url && (
                <a
                  href={selectedJob.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white inline-flex items-center gap-1.5 shadow-sm"
                >
                  Apply on Source Platform <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

