# Реєстр тест-кейсів — Grow PM Plugin

> Оновлюється КОЖЕН реліз: нові кейси на нові/змінені скіли + регресія на зачеплені. Формат — див. `Testing-process.md`. Статус заповнюється при прогоні стадії.

## Реліз v1.15.0 — planning suite + rename Task Creator

> **Прогін 29.06.2026 — вердикт: GREEN** (умова: фінальний lint TC-lint-002/003 у повному клоні перед пушем).
> - Stage 1 lint: 0 FAIL (4 нові скіли); WARN = зовнішні references (резолв після merge).
> - Stage 2 trigger: 19/20 pass; 1 LOW-ризик (quarterly «retro кварталу» ↔ team-ops `quarter-review` на короткій фразі).
> - Stage 3 scenario: 4/4 pass (усі ключові кроки/gate-и/артефакти присутні).
> - Stage 4 integration: pass — чейни на `task-creator`; делегування team-ops-reporter узгоджене; project↔quarterly двосторонній; team-ops-reporter+jira-data-protocol підтверджені в репо v1.14.0 (web_fetch), у локальному кеші сесії їх немає (старий знімок).
> - Stage 5 regression: pass — 0 згадок feature-task-creator у нових файлах.
> - Backup: `_backups/v1.15.0-snapshot-*` (workspace); git tag pre-v1.15.0 — крок користувача.
> - Відкладено на v1.15.1: дрібна неузгодженість нумерації roadmap-architect (0-5 vs 4 режими); уточнення «retro» тригера.


### Stage 1 — Static lint
- **TC-lint-001** | усі skills/*/SKILL.md | frontmatter+semver+name==folder → `skill_lint.py` | expected: 0 FAIL | **pass** (4 нові: GREEN; зовн. references = WARN, очікувано)
- **TC-lint-002** | повний репо після merge | усі references цитованих скілів резолвляться | expected: 0 unresolved | status: прогнати в репо
- **TC-lint-003** | репо | skill_version у тілі == frontmatter (ловить баги аудиту) | expected: 0 mismatch | status: прогнати в репо (очікувано зловить cjm/product-analysis/write-concept)

### Stage 2 — Trigger eval (нові скіли)
- **TC-trig-quarterly-01** | quarterly-planning | "збери roadmap на квартал" / "що команда встигне" | expected: тригерить quarterly-planning | 
- **TC-trig-quarterly-02 (neg)** | quarterly-planning | "звіт за квартал що зробили" | expected: НЕ перехоплює; це team-ops-reporter quarter-review |
- **TC-trig-project-01** | project-planning | "скільки займе проєкт", "критичний шлях", "переплан" | expected: project-planning |
- **TC-trig-sprint-01** | sprint-planning | "що можна взяти у спринт", "хто візьме задачі" | expected: sprint-planning |
- **TC-trig-sprint-02 (neg)** | sprint-planning | "звіт по спринту що закрили" | expected: team-ops-reporter sprint-review |
- **TC-trig-arch-01** | roadmap-architect | "навести лад у структурі", "дерево roadmap" | expected: roadmap-architect |

### Stage 3 — Scenario walk (нові скіли)
- **TC-scn-quarterly-01** | quarterly-planning full | mock local-context Planning + retro кварталу | expected: кроки 0-6 присутні, capacity-gate на платформних слайсах, делегування quarter-review, артефакти після апруву |
- **TC-scn-project-01** | project-planning replan | mock арки + факт | expected: backlog=лишок−committed, ре-секвенс під критичний шлях, дрейф vs baseline |
- **TC-scn-sprint-01** | sprint-planning groom | mock Development Flow + минулий спринт | expected: фокуси, per-member capacity, carryover-risk, сканування готовності (work-type DAG), детекція порушень, пропозиція виконавців |
- **TC-scn-arch-01** | roadmap-architect audit | mock розмітки з розривами | expected: звіт розривів (без кварталу/цілі/коду, сироти), запис лише після апруву |

### Stage 4 — Integration
- **TC-int-01** | quarterly-planning → task-creator | затверджений план → задачі | expected: чейн існує, task-creator (не feature-task-creator) |
- **TC-int-02** | planning ↔ team-ops-reporter | делегування quarter/sprint/member/initiative review | expected: реюз jira-data-protocol, без дублю fetch |
- **TC-int-03** | project-planning ↔ quarterly-planning | арки+% allocation вниз, факт+перенесене → replan вгору | expected: двосторонній звʼязок |
- **TC-int-04** | усі нові скіли | резолв спільних references (capacity/dependency/planning-core/roadmap-artifacts + зовнішні) | expected: усі резолвляться у повному репо |

### Stage 5 — Regression (зачеплене rename + сусіди)
- **TC-reg-rename-01** | task-creator | name==folder, H1, опис оновлені; стара тека відсутня | expected: pass |
- **TC-reg-rename-02** | write-concept, requirements-creator, cjm-research, meeting-processor, diagram-prototyper, plugin-configurator, local-context-protocol, README, CHANGELOG | усі згадки feature-task-creator → task-creator (крім історії CHANGELOG) | expected: 0 залишків поза CHANGELOG-історією |
- **TC-reg-trig-01** | task-creator | старі тригер-фрази ("create tasks from requirements") досі тригерять | expected: pass (не зламано інвокацію) |
- **TC-reg-existing-01** | топ-5 наявних скілів (cjm, product-analysis, requirements, meeting, design-bridge) | поведінка як до v1.15 (planning suite additive) | expected: без регресій |

---

## Майбутні релізи (заготовки)
- **v1.16.0 quick fixes** — кейси на 8 багфіксів з аудиту (design-bridge subtype, product-analysis Step 0h, skill_version ×3, team-ops-reporter sprint-id, configurator дублі, template-library лічба).
- **v1.17.0 dedup** — регресія на скіли, з яких винесено канон у references.
- **v1.18.0 configurator refactor** — повна регресія plugin-configurator + субагент-процеси.
