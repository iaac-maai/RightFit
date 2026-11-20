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

export interface ProjectCard { id: string; name: string; country: Country; role: Role; company: string; people: number }

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
  project: { id: string; name: string; country: Country; createdAt: string };
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
