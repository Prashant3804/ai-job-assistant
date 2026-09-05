'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import {
  Mail,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Award,
  Calendar,
  XCircle,
  Inbox,
  User,
  Send,
} from 'lucide-react';
import { api } from '@/lib/api';
import { EmailMessage } from '@/types';

export default function EmailsPage() {
  const [emails, setEmails] = useState<EmailMessage[]>([]);
  const [loading, setLoading] = useState(true);

  // Playground state
  const [senderName, setSenderName] = useState('');
  const [senderEmail, setSenderEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [bodyText, setBodyText] = useState('');
  const [classifying, setClassifying] = useState(false);
  const [classifyResult, setClassifyResult] = useState<any>(null);

  useEffect(() => {
    loadEmails();
  }, []);

  async function loadEmails() {
    try {
      setLoading(true);
      const res = await api.getEmails();
      setEmails(res);
    } catch (err) {
      console.error('Failed to load emails:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleClassify() {
    if (!bodyText.trim()) return;
    try {
      setClassifying(true);
      const res = await api.classifyEmail({
        sender_name: senderName,
        sender_email: senderEmail,
        subject,
        body_text: bodyText,
      });
      setClassifyResult(res);
    } catch (err: any) {
      alert(`Classification error: ${err.message}`);
    } finally {
      setClassifying(false);
    }
  }

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'INTERVIEW_INVITATION':
        return (
          <span className="bg-amber-50 text-amber-700 border border-amber-200 text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-amber-600" /> Interview Invitation
          </span>
        );
      case 'OFFER':
        return (
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-1">
            <Award className="w-3.5 h-3.5 text-emerald-600" /> Job Offer
          </span>
        );
      case 'REJECTION':
        return (
          <span className="bg-rose-50 text-rose-700 border border-rose-200 text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5 text-rose-600" /> Rejection
          </span>
        );
      case 'OA_REQUEST':
        return (
          <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" /> Assessment / OA
          </span>
        );
      default:
        return (
          <span className="bg-slate-100 text-slate-700 text-xs font-bold px-2.5 py-1 rounded-lg">
            {classification}
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Recruiter Emails & AI Classifier"
        subtitle="Automatic intent detection, interview detection, and application status synchronization"
      />

      <div className="p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* Real-time Classifier Playground */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-sky-500" />
                AI Email Recruiter Classifier Playground
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Test AI classification on any recruiter email or custom message in real time.
              </p>
            </div>
            <button
              onClick={handleClassify}
              disabled={classifying || !bodyText.trim()}
              className="flex items-center gap-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:opacity-95 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-sm transition-opacity"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{classifying ? 'Classifying...' : 'Run AI Classifier'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="Sender Name"
                  className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900"
                />
                <input
                  type="email"
                  value={senderEmail}
                  onChange={(e) => setSenderEmail(e.target.value)}
                  placeholder="Sender Email"
                  className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900"
                />
              </div>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Email Subject"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 font-semibold"
              />
              <textarea
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                placeholder="Email message body..."
                rows={4}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
              ></textarea>
            </div>

            {/* Classification Output Box */}
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 flex flex-col justify-center">
              {classifyResult ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-bold text-slate-500">AI Classification</span>
                    {getClassificationBadge(classifyResult.classification)}
                  </div>

                  <div className="text-xs space-y-1">
                    <div className="font-bold text-slate-800">
                      Detected Company:{' '}
                      <span className="text-sky-600">{classifyResult.detected_company || 'Identified'}</span>
                    </div>
                    <div className="font-bold text-slate-800">
                      Confidence Score:{' '}
                      <span className="text-emerald-600">{(classifyResult.confidence_score * 100).toFixed(1)}%</span>
                    </div>
                    {classifyResult.suggested_status_update && (
                      <div className="text-amber-700 font-medium">
                        Suggested Status: <strong>{classifyResult.suggested_status_update}</strong>
                      </div>
                    )}
                  </div>

                  <p className="text-xs text-slate-600 bg-white p-3 rounded-lg border border-slate-200">
                    {classifyResult.summary}
                  </p>
                </div>
              ) : (
                <div className="text-center text-xs text-slate-400 py-6">
                  Click &ldquo;Run AI Classifier&rdquo; to analyze the email intent and detect status updates.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Ingested Emails Feed */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Inbox className="w-4 h-4 text-indigo-500" />
            Ingested Recruiter Messages
          </h3>

          <div className="space-y-4">
            {loading ? (
              <div className="text-center py-8 text-xs text-slate-400">Loading emails...</div>
            ) : emails.length > 0 ? (
              emails.map((msg) => (
                <div
                  key={msg.id}
                  className="p-5 rounded-xl border border-slate-200 bg-white hover:border-sky-300 hover:shadow-xs transition-all space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-slate-900">{msg.sender_name || msg.sender_email}</span>
                      <span className="text-xs text-slate-400">({msg.sender_email})</span>
                    </div>
                    {getClassificationBadge(msg.classification)}
                  </div>

                  <div className="font-semibold text-xs text-slate-800">{msg.subject}</div>

                  <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 p-3 rounded-xl border border-slate-100">
                    {msg.body_text}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                    <span>Received: {new Date(msg.received_at).toLocaleString()}</span>
                    <span>Confidence: {(msg.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-400">No emails ingested yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
