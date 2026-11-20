# Personal data breach procedure (GDPR Articles 33 and 34)

RightFit online. 20 Nov 2026. A personal data breach is a breach of security leading to the accidental or unlawful destruction, loss, alteration, unauthorised disclosure of, or access to, personal data.

## In the first hour

1. Contain it: revoke the sessions involved (Management, People, Sign out), rotate the secrets that may be exposed (`npx wrangler secret put BETTER_AUTH_SECRET`, Google's client secret), withdraw pending invitations, or take the Worker offline if needed.
2. Keep the evidence: the activity log in Management, the Cloudflare logs, and what was noticed, by whom and when.

## Within 24 hours

3. Assess: what data, whose, how many people and records, whether it was encrypted or hashed, and the likely consequences for the people affected.
4. If the breach touches the content of a project, notify the controller (the organisation that opened the project) within 48 hours, as clause 8 of the data processing agreement promises, through the consultants of that project.

## Within 72 hours of becoming aware

5. As controller, notify the Agencia Española de Protección de Datos through its electronic office (sedeagpd.gob.es), unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons. If not everything is known yet, notify what is known and complete it later (Article 33(4)).
6. If the breach is likely to result in a high risk to the people affected, tell them without undue delay, in clear language: what happened, the likely consequences, what was done, what they can do, and whom to contact (Article 34).

## Always

7. Record every breach, including those not notified, with the facts, effects and remedial action (Article 33(5)), in a file kept outside the public repository.
8. Review what allowed it, and change the measures in Annex II of the data processing agreement if needed.
