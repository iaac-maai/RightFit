// Small ways of writing things on the page
import { ROLE_LABEL, type Role } from "../worker/roles";

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]!.toUpperCase()).join("") || "?";

export const day = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export const daysLeft = (iso: string) => Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000));

export const country = (code: string) => (code === "ES" ? "Spain" : "Romania");

// "a contractor", "an engineer"
export const aRole = (role: Role) => {
  const word = ROLE_LABEL[role].toLowerCase();
  return `${/^[aeiou]/.test(word) ? "an" : "a"} ${word}`;
};

export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function greeting(name: string) {
  const hour = new Date().getHours();
  const part = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const first = name.trim().split(/\s+/)[0];
  return first ? `${part}, ${first}` : part;
}
