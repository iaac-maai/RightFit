// Who may invite whom, and who sees whom, in one project (spec/features/rightfit_online.md, sections 4 and 5).
// Plain functions with no Cloudflare in them: the Worker and the page both use them, and roles.test.ts checks them.

// Suppliers are left out for now: letting the makers' resellers into a project could bring conflicts of interest
// (Luca, 20 Nov 2026). The idea is kept in spec/features/rightfit_online.md, section 11.
export const ROLES = ["consultant", "designer", "site_supervisor", "client", "contractor", "subcontractor"] as const;
export type Role = (typeof ROLES)[number];

// The people who answer the forms
export const REVIEWERS: readonly Role[] = ["consultant", "designer", "site_supervisor", "client"];

export const ROLE_LABEL: Record<Role, string> = {
  consultant: "Consultant",
  designer: "Designer",
  site_supervisor: "Site supervisor",
  client: "Client",
  contractor: "Contractor",
  subcontractor: "Subcontractor",
};

// One line on each role, shown where a person picks whom to invite
export const ROLE_NOTE: Record<Role, string> = {
  consultant: "Reviews and answers the forms, and runs the project space.",
  designer: "Wrote the design, and checks each form against it.",
  site_supervisor: "Represents the client on site, and signs the forms.",
  client: "Owns the project, and signs the forms.",
  contractor: "Sends the forms to the reviewers and brings in the subcontractors.",
  subcontractor: "Prepares the forms for its part of the work.",
};

const INVITES: Record<Role, readonly Role[]> = {
  consultant: ["consultant", "designer", "site_supervisor", "client", "contractor"],
  designer: ["designer"],
  site_supervisor: ["site_supervisor"],
  client: ["client"],
  contractor: ["contractor", "subcontractor"],
  subcontractor: ["subcontractor"],
};

export const isRole = (value: unknown): value is Role => typeof value === "string" && (ROLES as readonly string[]).includes(value);
export const rolesInvitableBy = (role: Role): readonly Role[] => INVITES[role];
export const mayInvite = (inviter: Role, invitee: Role) => INVITES[inviter].includes(invitee);
const seesEveryone = (role: Role) => REVIEWERS.includes(role) || role === "contractor";

// A member of a project, as far as these rules need: invitedBy is the id of the member who invited them
export interface Person {
  id: string;
  role: Role;
  invitedBy: string | null;
}

// The first person of this person's firm in the chain: walk up while the inviter has the same role
function firmRoot(byId: Map<string, Person>, person: Person): Person {
  let current = person;
  const seen = new Set<string>();
  while (current.invitedBy && !seen.has(current.id)) {
    seen.add(current.id);
    const parent = byId.get(current.invitedBy);
    if (!parent || parent.role !== current.role) break;
    current = parent;
  }
  return current;
}

// The branch of a firm: its first person and everyone invited from there, down the chain
function branchOf(people: Person[], rootId: string): Set<string> {
  const branch = new Set([rootId]);
  for (let grew = true; grew; ) {
    grew = false;
    for (const p of people) {
      if (p.invitedBy && branch.has(p.invitedBy) && !branch.has(p.id)) {
        branch.add(p.id);
        grew = true;
      }
    }
  }
  return branch;
}

// Everyone above a person, up to the top of the chain
function chainAbove(byId: Map<string, Person>, person: Person): Set<string> {
  const above = new Set<string>();
  for (let next = person.invitedBy; next && !above.has(next); next = byId.get(next)?.invitedBy ?? null) above.add(next);
  return above;
}

// The people a member may see: reviewers and the contractor see the whole team; a subcontractor sees the reviewers,
// the contractor, the chain above its firm and its own branch, never another firm's branch
export function visiblePeople<T extends Person>(people: T[], viewer: Person): T[] {
  if (seesEveryone(viewer.role)) return people;
  const byId = new Map<string, Person>(people.map((p) => [p.id, p]));
  const root = firmRoot(byId, byId.get(viewer.id) ?? viewer);
  const branch = branchOf(people, root.id);
  const above = chainAbove(byId, root);
  return people.filter((p) => seesEveryone(p.role) || branch.has(p.id) || above.has(p.id));
}

// The pending invitations a member may see: all of them for reviewers and the contractor, otherwise only those
// sent from the member's own branch
export function visibleInvitations<T extends { invitedBy: string }>(invitations: T[], people: Person[], viewer: Person): T[] {
  if (seesEveryone(viewer.role)) return invitations;
  const byId = new Map<string, Person>(people.map((p) => [p.id, p]));
  const branch = branchOf(people, firmRoot(byId, byId.get(viewer.id) ?? viewer).id);
  return invitations.filter((i) => branch.has(i.invitedBy));
}

// Withdraw a pending invitation: whoever sent it, or any consultant
export const mayWithdraw = (viewer: Person, invitedBy: string) => viewer.id === invitedBy || viewer.role === "consultant";

// Management: the accounts named in the ADMIN_EMAILS secret, and only with an address Google has verified (worker/admin.ts)
export function adminList(value: string | undefined) {
  return new Set((value ?? "").split(",").map((e) => e.trim().toLowerCase()).filter(Boolean));
}

export function isAdmin(user: { email: string; emailVerified: boolean }, list: string | undefined) {
  return user.emailVerified && adminList(list).has(user.email.trim().toLowerCase());
}
