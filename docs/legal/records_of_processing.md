# Records of processing activities (GDPR Article 30)

RightFit online. Kept by the operator named in `web/src/pages/Legal.tsx`. Last updated 20 Nov 2026.

## A. As controller (Article 30(1))

| Activity | Purposes | Data subjects | Personal data | Recipients | Transfers | Erasure | Security |
|---|---|---|---|---|---|---|---|
| Accounts and sign-in | create and run accounts, sign users in | users | name, email, verification flag, picture (Google), password hash, sessions with IP address and user agent | Cloudflare (processor); Google (independent controller, if chosen) | United States: Data Privacy Framework, SCCs | account: on deletion; sessions: 7 days | Annex II of the data processing agreement |
| Projects and invitations | let project parties invite each other and see their team | users; invited persons | role, company, inviter, joining date; invitee's email, role, company | other members of the project, by role; Cloudflare | as above | with the membership or the project | as above |
| Terms records | prove acceptance of the terms | users | terms version, date | Cloudflare | as above | with the account | as above |
| Activity log | accountability and security | users | user id, action, project, time | Management; Cloudflare | as above | 12 months | as above |
| Correspondence | answer requests and support | users, invited persons | contact details, content of messages | email provider used by the operator | depends on that provider | up to the limitation period | as above |

## B. As processor (Article 30(2))

| Controller | Processing | Sub-processors | Transfers | Security |
|---|---|---|---|---|
| each organisation that opened a project (consultant's organisation), as recorded with the accepted data processing agreement | hosting and processing of project content, as in Annex I of the data processing agreement | Cloudflare; Render (when the checks run online) | United States: Data Privacy Framework, SCCs | Annex II of the data processing agreement |
