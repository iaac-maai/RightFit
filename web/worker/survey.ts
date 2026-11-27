// The practice survey (spec/features/survey.md): the public page asks for the questions and sends an anonymous answer;
// signed-in people read the results, and the admins the comments and a CSV. The rules are in survey_rules.ts.
import { json, newId, now, readBody, type Env } from "./data";
import { CONSENT, QUESTIONS, SURVEY_VERSION, checkAnswers, live, summarise, toCsv, type Answers } from "./survey_rules";

// Before any session: the questions, and an answer
export async function surveyOpenRoute(request: Request, env: Env, path: string, method: string): Promise<Response | null> {
  if (path === "/api/survey" && method === "GET") return json({ version: SURVEY_VERSION, questions: QUESTIONS, consent: CONSENT });
  // the live numbers at the top of the survey page, for anyone: sums only, never a comment or one person's answers
  if (path === "/api/survey/live" && method === "GET") {
    return json(live(await rows(env)), 200, { "Cache-Control": "no-store" });
  }
  if (path === "/api/survey" && method === "POST") {
    const raw = await request.text();
    if (raw.length > 20_000) return json({ error: "The answer is too long." }, 413);
    let body: Record<string, unknown>;
    try { body = JSON.parse(raw); } catch { return json({ error: "Send JSON." }, 400); }
    const answers = checkAnswers(body);
    if (typeof answers === "string") return json({ error: answers }, 400);
    // the day only, never the time, an address or anything about the browser
    await env.DB.prepare("INSERT INTO survey_response (id, day, version, answers) VALUES (?, ?, ?, ?)")
      .bind(newId(), now().slice(0, 10), SURVEY_VERSION, JSON.stringify(answers)).run();
    return json({ ok: true }, 201);
  }
  return null;
}

async function rows(env: Env) {
  const { results } = await env.DB.prepare("SELECT day, answers FROM survey_response ORDER BY day").all<{ day: string; answers: string }>();
  return results.map((r) => ({ day: r.day, answers: JSON.parse(r.answers) as Answers }));
}

// With a session: the results (anyone signed in), the comments and the CSV (admins)
export async function surveyRoute(env: Env, path: string, method: string, admin: boolean): Promise<Response | null> {
  if (method !== "GET") return null;
  if (path === "/api/survey/results") {
    const all = await rows(env);
    return json({
      n: all.length, firstDay: all[0]?.day ?? null, lastDay: all.at(-1)?.day ?? null, results: summarise(all.map((r) => r.answers)),
      comments: admin ? all.filter((r) => r.answers.comment).map((r) => ({ day: r.day, text: r.answers.comment })) : null, admin,
    });
  }
  if (path === "/api/survey/results.csv") {
    if (!admin) return json({ error: "The answers one by one are for the people who run RightFit." }, 403);
    return new Response(toCsv(await rows(env)), {
      headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="rightfit-survey.csv"' },
    });
  }
  return null;
}
