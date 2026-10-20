# Live Quiz Competition — Design Spec

## Product intent

Create a clear, lively interface for hosting and playing a timed quiz. The experience should feel responsive and social while keeping the current question, timer, answer state, and standings easy to understand. The server remains authoritative for time and scoring; the interface reflects those states and communicates transitions.

## Visual direction

Use the attached Aura design notes as a visual reference, adapted to the quiz product. Keep the interface light, spacious, and energetic, with a deep purple primary color and a restrained red accent. Prefer a distinctive question or leaderboard composition over a generic analytics dashboard or uniform card grid. Motion should reinforce live activity without competing with quiz content.

### Design tokens

| Role | Value |
| --- | --- |
| Primary | `#5B1E91` |
| Secondary | `#FFFFFF` |
| Accent | `#EB0000` |
| Background | `#FFFFFF` |
| Surface | `#BDB5E9` |
| Primary text | `#111827` |
| Secondary text | `#4B5563` |
| Border | `#AFAFB6` |

Use primary purple for key actions and active states. Reserve red for urgent or time-sensitive emphasis, and preserve readable contrast for all text and controls. Use the lavender surface selectively for panels and supporting content.

### Type

- Display and body: Plus Jakarta Sans, with a compatible sans-serif fallback.
- Technical labels and compact metadata: JetBrains Mono, with a monospace fallback.
- Use large display type sparingly for quiz prompts and key result moments. Keep instructions and answer text comfortably readable on mobile.

### Spacing and shape

- Base spacing unit: `8px`.
- Common gap: `16px`.
- Card padding: `24px`.
- Section spacing: `80px` on wide layouts; reduce responsively on smaller screens.
- Card radius: `32px`.
- Control radius: `24px`.
- Pill radius: `9999px`.

Use subtle borders and restrained shadows to separate nested surfaces. Do not use a shadow or color alone to communicate state.

## Information architecture and screens

### Host setup

Provide a focused, stepwise form for quiz title and question entry. Make question order, timer duration, answer choices, and correct-answer selection explicit. Show validation beside the relevant field and a clear path to review before launch. Explain that launching creates a participant join URL and a separate private host control URL.

### Host live control

Keep the current question, remaining time, participant count, and event state prominent. Provide a clear start action in the lobby and a clear close action when the event is complete. During play, show operational information such as answer progress and the next transition without letting controls compete with the question. Make the private nature of the host link clear at issuance.

### Participant join and lobby

Make the join code or join link immediately recognizable. Ask for the required name and unique display name with concise explanations. After joining, show that the participant is waiting and provide live confirmation when the host starts. If a display name is unavailable or the room is full, preserve entered values and explain the next step.

### Participant play

Give the question prompt and answer choices the strongest visual priority. Show the countdown as a persistent, legible element and indicate when an answer is selected or submitted. Communicate closed questions, late submissions, and connection recovery in plain language. Do not imply that an answer was accepted until the server confirms it.

### Results and leaderboard

After each question, show updated standings and each participant’s own outcome during the results interval. Reveal correct answers only after the final question. Give rank changes and score totals clear hierarchy without relying on color alone. Keep final results available until the host closes the event.

### Admin

Use a compact, utilitarian interface for authenticated super-admins to locate events and review identifying metadata before deletion. Make destructive deletion unmistakable and summarize that associated participants, answers, and results are removed.

## Layout and responsive behavior

- Establish a clear content width and consistent alignment across the host and participant flows.
- On wide screens, use space for supportive live context such as answer progress or standings while maintaining a single focal question.
- On narrow screens, stack content in task order; keep the timer and primary answer actions visible without horizontal scrolling.
- Preserve visual hierarchy and touch target size as layouts collapse. Avoid shrinking dense desktop panels into unreadable mobile cards.
- Use compact dashboard panels for live metrics, but keep question and answer surfaces distinct from supporting metrics.

## Interaction and motion

- Use restrained entrance transitions when entering a room or moving between question and results states.
- Animate timer progress smoothly and make the final seconds perceptible without flashing or relying only on color.
- Use small hover and press feedback for controls; respect reduced-motion preferences.
- Use staggered reveals only for secondary content such as leaderboard rows. Keep live updates stable so content movement does not make it hard to follow.
- Make reconnecting and resynchronizing visible, with a clear return to the current server state.

## Accessibility and state communication

- Support keyboard navigation and visible focus states for every interactive control.
- Associate labels and validation messages with form fields; announce important live state changes appropriately to assistive technology.
- Provide text or icon cues alongside color for selected, correct, incorrect, expired, and disconnected states.
- Maintain sufficient contrast and respect reduced-motion settings.
- Ensure countdown updates do not overwhelm screen readers; announce meaningful thresholds and state changes instead of every tick.

## UI states to design

- Loading, connecting, reconnecting, and connection lost.
- Empty quiz setup and invalid quiz content.
- Lobby waiting, event starting, active question, answer submitted, and question expired.
- Results interval and final results.
- Full room, duplicate display name, invalid or expired link, and rejected/late answer.
- Host closed event and admin deletion confirmation/result.

## Product constraints

- The server controls deadlines, accepted answers, session transitions, and scoring. Client visuals must not suggest otherwise.
- A participant may join between questions and scores only from questions they can answer.
- The participant view must never expose the private host credential or pre-final correct answers.
- Support the planned room size of up to 50 participants without making the participant or host views visually noisy.

