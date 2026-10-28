# RightFit

AI-assisted product selection and MEP coordination for architects and interior designers.

IAAC MaAI01 · Operable Futures · 2026–27 · Team: Sahil Khan, Jeff El Khoury, Luca Obejdeanu

## What it does

An interior architect describes a product in words or with a reference image. RightFit finds products that match the look, checks them against the room's known MEP constraints, and explains the trade-offs with source evidence, while the design is still cheap to change.

- **First and only product family in the prototype:** kitchen extraction hoods.
- **AI** is used for visual and text matching and for reading data sheets.
- **Engineering checks** are deterministic and rule-based, with no AI.
- **The tool never certifies products or claims regulatory compliance.** The designer chooses and the MEP engineer signs off.

## Status (28 Oct 2026)

Project constitution and planning documents drafted (v0.1, pending team approval). No catalogue data collected, no model built or tested, no results yet.

## Where to start

| If you want to... | Read |
|---|---|
| Understand the problem, scope and principles | [`spec/constitution/mission.md`](spec/constitution/mission.md) |
| See milestones, features and responsibilities | [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md) |
| See tools, data sources and architecture | [`spec/constitution/tech_stack.md`](spec/constitution/tech_stack.md) |
| Work in this repo (people or AI agents) | [`AGENTS.md`](AGENTS.md) |
| See how the problem breaks down into tasks | [`docs/problem_segmentation.md`](docs/problem_segmentation.md) |
| See what data we need and have | [`docs/data_map.md`](docs/data_map.md) |
| See decisions made so far | [`docs/decisions.md`](docs/decisions.md) |

## Getting the project

```
git clone https://github.com/iaac-maai/RightFit.git
```

Then read `AGENTS.md` before making changes.

## Repository rules in short

- Never commit confidential client documents, client names, prices, personal data, secrets, or manufacturer images and PDFs.
- Every technical value needs a source; missing values are marked `unclear`, never guessed.
- Decisions go in `docs/decisions.md`, not only in chat.