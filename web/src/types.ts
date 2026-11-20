// What the Worker answers (worker/index.ts), as the page reads it
import type { Role } from "../worker/roles";

export type { Role };
export type Country = "RO" | "ES";

export interface Session {
  user: { name: string; email: string; image: string | null; emailVerified: boolean };
  termsAccepted: boolean;
  termsVersion: string;
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
