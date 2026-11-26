// What the Worker answers (worker/index.ts), as the page reads it
import type { Role } from "../worker/roles";

export type { Role };
export type Country = "RO" | "ES";

export interface Session {
  user: { name: string; email: string; image: string | null; emailVerified: boolean };
  termsAccepted: boolean;
  termsVersion: string;
  dpaVersion: string;
  admin: boolean;
}

export interface ProjectCard { id: string; name: string; country: Country; locked: boolean; role: Role; company: string; people: number }

export interface WaitingInvitation {
  id: string; role: Role; company: string; createdAt: string; expiresAt: string; project: string;
  invitedBy: string | null; inviterCompany: string | null; inviterRole: Role | null;
}

export interface HomeData { projects: ProjectCard[]; invitations: WaitingInvitation[] }

export interface TeamPerson {
  id: string; role: Role; invitedBy: string | null; name: string; email: string; image: string | null; company: string; joinedAt: string;
}

export interface PendingInvitation {
  id: string; email: string; role: Role; company: string; invitedBy: string; createdAt: string; expiresAt: string;
  expired: boolean; mayWithdraw: boolean;
}

export interface ProjectData {
  project: { id: string; name: string; country: Country; createdAt: string; locked: number; packages: number; boqLines: number };
  me: { id: string; role: Role; company: string };
  people: TeamPerson[];
  invitations: PendingInvitation[];
  mayInvite: Role[];
  mayRemove: boolean;
}

export interface InvitationPreview {
  project: string; role: Role; company: string; email: string; invitedBy: string | null; inviterCompany: string | null;
  inviterRole: Role | null; state: "pending" | "accepted" | "declined" | "withdrawn"; expired: boolean; google: boolean;
}

export interface CreatedInvitation { id: string; link: string; email: string; role: Role; expiresAt: string }

// Management (worker/admin.ts)
export interface AdminEvent {
  id: number; at: string; action: string; detail: Record<string, unknown>; projectId: string | null; project: string | null;
  actor: string | null; actorEmail: string | null;
}
export interface AdminOverview { counts: { people: number; projects: number; pending: number; newPeople: number; google: number }; events: AdminEvent[] }
export interface AdminPerson { id: string; name: string; email: string; verified: boolean; createdAt: string; methods: string[]; projects: number; sessions: number }
export interface AdminProjectRow { id: string; name: string; country: Country; createdAt: string; consultants: string | null; people: number; pending: number }
export interface AdminMember { id: string; role: Role; company: string; invitedBy: string | null; joinedAt: string; userId: string; name: string; email: string; image: string | null }
export interface AdminProjectData {
  project: { id: string; name: string; country: Country; createdAt: string; dpaVersion: string; dpaAcceptedAt: string };
  people: AdminMember[];
  invitations: PendingInvitation[];
  events: AdminEvent[];
}

// The project's own data (worker/project_data.ts)
export interface PackageRow {
  code: string; formNo: string; revision: number; discipline: string; items: string[]; files: number; pages: number | null;
  letter: "A" | "B" | "C" | null; label: string | null; problems: number | null; questions: number | null;
  toConfirm: number | null; readings: number | null; reviewedAt: string | null; uploadedAt?: string | null;
}
export interface PackageFile { name: string; size: number; pages: number | null }
// RightFit's review of one package, as the laptop's review page builds it (app/review_server.py, review())
export type Value = string | number | boolean | null;
export interface Reading {
  key: string; what: string; value: Value; unit: string | null; source: string; page: number | string | null; quote: string | null;
  status: string; checked_by?: string | null; verified_on?: string | null; item: string; product?: string;
  confirmed_in?: string | null; // confirmed first on the same file in another package (MAF-36b)
}
export interface RuleUsed { id: string; status: string; text: string; source: string; url: string }
export interface CheckResult {
  key: string; check: string; check_name: string; title: string; item: string | null; product: string | null; doc: string | null;
  verdict: "flag" | "unclear" | "pass" | "info"; confirmed: boolean; reason: string; sources: string[]; rules: RuleUsed[];
  blocking: boolean; comment: string | null; delta: number | null; dismissed: string | null; evidence: Reading[];
}
export interface Match { item: string | null; product: string; kind: string; page: number | string | null; quote: string | null; status: string }
export interface ReviewDoc {
  no: number; file: string; type: string; listed_as: string | null; covers: string[]; pages: number; status: string; matches: Match[];
  checked_by?: string | null; confirmed_in?: string | null;
}
export interface AiFinding {
  id: string; title: string; finding: string; suggested_comment: string; status: "suggested" | "accepted" | "rejected";
  note: string | null; evidence: { source: string; page: number | string | null; quote: string }[];
}
export interface Decision { decision: "kept" | "dismissed"; reason: string | null; decided_by: string; decided_on: string }
export interface PackageReview {
  review: string; delivery: string; location: Country;
  form: { form_no: string; revision: number };
  status: { letter: "A" | "B" | "C"; label: string; reasons: string[] };
  counts: { problems: number; questions: number; passed: number; would_pass: number; to_confirm: number; readings: number };
  items: { id: string; name: string; model: string; values: Omit<Reading, "item">[] }[];
  documents: ReviewDoc[]; results: CheckResult[]; ai_findings: AiFinding[]; notes: string[];
  answer: { lines: string[]; text: string }; decisions: Record<string, Decision>;
}
// What the laptop read from the PDFs at the import: the comparison with the previous revision, and where each quoted
// line sits on its page (rectangles in percent of the page: left, top, width, height)
export interface Revision { status: "unchanged" | "changed" | "new" | "removed"; file?: string; previous?: string; renamed?: boolean;
  how?: string; similarity?: number; pages?: number; same_pages?: number }
export interface PackageExtra {
  revisions: { previous: string | null; revision?: number; attachments?: Revision[] };
  marks: Record<string, Record<string, Record<string, [number, number, number, number][]>>>;
}
export interface PackageData {
  package: PackageRow; files: PackageFile[]; review: PackageReview | null; mayEdit?: boolean; extra?: PackageExtra | null; mayAdd?: boolean;
  answer?: FormAnswer | null; mayAnswer?: boolean;
}
// The answer the form got, as a reviewer recorded it (MAF-36c), apart from RightFit's draft letter
export interface FormAnswer { answer: "A" | "B" | "C"; answeredAt: string; answeredBy: string | null }

// The rules the checks used for the project's country (worker/project_data.ts, rules)
export interface LawRule {
  rule_id: string; jurisdiction: string; code: string; clause: string; requirement: string; applies_to: string; source_url: string;
  status: string; verified_on: string; valid_from: string; valid_to: string;
}
export interface ChecklistItem { id: string; family: string; item: string; how_to_check: string; if_missing: string; blocking: string }
export interface ConsultantRule {
  rule_id: string; family: string; application: string; kind: string; field: string; operator: string; value: string; unit: string;
  effect: string; text: string; source: string; added_on: string; active: string;
}
export interface ProjectRules {
  location: Country; law: LawRule[]; checklist: ChecklistItem[];
  mine: { rules: ConsultantRule[]; doc_types: Record<string, string>; values: Record<string, string>; kinds?: string[]; families?: string[] };
  mayEdit?: boolean;
}
export interface BoqLine {
  file: string; sheet: string; row: number; nr: string | null; text: string; unit: string | null; qty: string | number | null;
  producer: string | null; standards: string | null;
}
