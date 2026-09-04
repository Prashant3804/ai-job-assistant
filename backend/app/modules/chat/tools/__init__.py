from app.modules.chat.tools.base import BaseTool, ToolResult, ToolRegistry
from app.modules.chat.tools.resume_tools import (
    GetCandidateProfileTool,
    GetResumeVersionsTool,
    GetActiveResumeTool,
    GetCandidateSkillsTool,
    GetCandidateExperienceTool,
    GetCandidateEducationTool,
    GetCandidateProjectsTool,
)
from app.modules.chat.tools.job_tools import (
    SearchJobsTool,
    GetJobDetailsTool,
    GetJobsBySourceTool,
    GetJobsByLocationTool,
    GetJobsByRoleTool,
    GetJobsBySalaryTool,
)
from app.modules.chat.tools.matching_tools import (
    GetJobMatchTool,
    GetRecommendedJobsTool,
    GetMatchHistoryTool,
    GetMissingSkillsTool,
    ExplainJobMatchTool,
)
from app.modules.chat.tools.application_tools import (
    GetApplicationHistoryTool,
    GetApplicationStatusTool,
    GetApplicationStatisticsTool,
    GetAnalyticsOverviewTool,
    GetAutoApplyStatusTool,
    GetAutoApplyPolicyTool,
    GetApplicationDetailsTool,
)
from app.modules.chat.tools.mailbox_tools import (
    GetMailboxConnectionsTool,
    GetRecentJobEmailsTool,
    GetRecruiterMessagesTool,
    GetApplicationEmailsTool,
    GetInterviewEmailsTool,
    GetRejectionEmailsTool,
    GetOfferEmailsTool,
    GetEmailDetailsTool,
    GetEmailThreadTool,
    GetMailboxSyncStatusTool,
)
from app.modules.chat.tools.communication_tools import (
    DraftRecruiterReplyTool,
    GetRecruiterProfileTool,
    ListRecruitersTool,
    GetInterviewPrepBriefTool,
    GenerateInterviewPrepTool,
    ListUpcomingInterviewsTool,
    GetFollowupRecommendationsTool,
    UpdateRecruiterNotesTool,
    GetCommunicationDraftsTool,
    ApproveCommunicationDraftTool,
)

def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    
    # Resume tools
    registry.register(GetCandidateProfileTool())
    registry.register(GetResumeVersionsTool())
    registry.register(GetActiveResumeTool())
    registry.register(GetCandidateSkillsTool())
    registry.register(GetCandidateExperienceTool())
    registry.register(GetCandidateEducationTool())
    registry.register(GetCandidateProjectsTool())

    # Job tools
    registry.register(SearchJobsTool())
    registry.register(GetJobDetailsTool())
    registry.register(GetJobsBySourceTool())
    registry.register(GetJobsByLocationTool())
    registry.register(GetJobsByRoleTool())
    registry.register(GetJobsBySalaryTool())

    # Matching tools
    registry.register(GetJobMatchTool())
    registry.register(GetRecommendedJobsTool())
    registry.register(GetMatchHistoryTool())
    registry.register(GetMissingSkillsTool())
    registry.register(ExplainJobMatchTool())

    # Application & Analytics tools (Read-Only)
    registry.register(GetApplicationHistoryTool())
    registry.register(GetApplicationStatusTool())
    registry.register(GetApplicationStatisticsTool())
    registry.register(GetAnalyticsOverviewTool())
    registry.register(GetAutoApplyStatusTool())
    registry.register(GetAutoApplyPolicyTool())
    registry.register(GetApplicationDetailsTool())

    # Mailbox & Recruiter tools (Read-Only)
    registry.register(GetMailboxConnectionsTool())
    registry.register(GetRecentJobEmailsTool())
    registry.register(GetRecruiterMessagesTool())
    registry.register(GetApplicationEmailsTool())
    registry.register(GetInterviewEmailsTool())
    registry.register(GetRejectionEmailsTool())
    registry.register(GetOfferEmailsTool())
    registry.register(GetEmailDetailsTool())
    registry.register(GetEmailThreadTool())
    registry.register(GetMailboxSyncStatusTool())

    # Phase 8 Communication Intelligence & Recruiter AI Tools
    registry.register(DraftRecruiterReplyTool())
    registry.register(GetRecruiterProfileTool())
    registry.register(ListRecruitersTool())
    registry.register(GetInterviewPrepBriefTool())
    registry.register(GenerateInterviewPrepTool())
    registry.register(ListUpcomingInterviewsTool())
    registry.register(GetFollowupRecommendationsTool())
    registry.register(UpdateRecruiterNotesTool())
    registry.register(GetCommunicationDraftsTool())
    registry.register(ApproveCommunicationDraftTool())

    return registry

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "build_default_tool_registry",
]

