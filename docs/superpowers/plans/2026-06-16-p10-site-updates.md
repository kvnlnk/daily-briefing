# P10 — Site/ Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Update the marketing site at `site/` (Vite static, deployed on Vercel) to reflect the product's new capabilities. English-only. Remove Hermes/WhatsApp claims, add plugin architecture section, add DE/EN demo toggle.

---

### Task 1: Remove Hermes/WhatsApp from hero + meta

**Files:**
- Modify: `site/index.html`

Changes:
1. Hero label: `"Open-source · Hermes Agent Skill"` → `"Open-source · Self-hosted · Extensible"`
2. Meta description: remove "WhatsApp message" → `"Weather, calendar, GitHub, news & Reddit — fetched in parallel, delivered to your phone."`
3. OG title/description: same treatment
4. OG subtitle on page: remove WhatsApp reference

- [ ] Step 1: Make changes to index.html
- [ ] Step 2: `grep -c "WhatsApp" site/index.html` → should be 0
- [ ] Step 3: `grep -c "Hermes Agent" site/index.html` → should be 0 (or only as optional mention)
- [ ] Step 4: Commit

---

### Task 2: Update "How It Works" section

**Files:**
- Modify: `site/index.html`

Step 3 changes:
```html
<div class="step">
  <span class="step__number">03</span>
  <h3 class="step__title">Pluggable Delivery</h3>
  <p class="step__desc">
    The summarized briefing is sent via stdout, ntfy push, email, or any
    configured delivery method — no external scheduler required.
  </p>
</div>
```

- [ ] Step 1-2: Rewrite step 3 → Commit

---

### Task 3: Add Plugin Architecture section

**Files:**
- Modify: `site/index.html`

New section between "How It Works" and "CTA":

```html
<section id="extend" class="extend">
  <h2 class="section-title">Extend It</h2>
  <p class="section-subtitle">Add any data source as a separate pip package. No fork needed.</p>

  <div class="extend__code">
<pre><code>class MySource(SourceProtocol):
    name = "my_source"
    def fetch(self, config):
        return SourceResult(name=self.name, ...)</code></pre>
  </div>

  <p class="extend__caption">
    Register via pyproject.toml entry point and it auto-appears in
    <code>daily-briefing --list-sources</code>.
    See the <a href="https://github.com/kvnlnk/daily-briefing/blob/main/docs/source-authoring.md" target="_blank">source-authoring guide</a>.
  </p>
</section>
```

Also update footer link to remove "Powered by Hermes Agent" → `"Works with Hermes Agent, among others"`.

- [ ] Step 1: Add HTML structure + styling to main.css
- [ ] Step 2: Commit

---

### Task 4: Update demo mockup — neutral data + DE/EN toggle

**Files:**
- Modify: `site/src/main.js`
- Modify: `site/index.html`

Replace hardcoded German Frankfurt briefing with two language versions:

```javascript
const BRIEFING_EN = `🌅 Good morning!

London: 18°C, ⛅ partly cloudy — High 20°C, Low 13°C. 60% rain chance.

📅 Today: 2 events — Sprint Review (10:30) + Team Lunch (12:30).

🐙 GitHub: 1 open PR, 1 assigned issue.

📰 Top News: Tech giants announce new AI chip partnership. Open-source framework reaches 100K stars.

Have a great day! ☕`;

const BRIEFING_DE = `☀🌅 Guten Morgen!

Berlin: 18°C, ⛅ teils bewölkt — Höchstwert 20°C, Tiefstwert 13°C. 60% Regenrisiko.

📅 Heute: 2 Termine — Sprint-Review (10:30) + Mittagessen (12:30).

🐙 GitHub: 1 offener PR, 1 Issue zugewiesen.

📰 Top-News: Tech-Giganten kündigen neue KI-Chip-Partnerschaft an. Open-Source-Framework erreicht 100.000 Sterne.

Schönen Tag! ☕`;
```

Add toggle buttons:
```html
<div class="demo__toggles">
  <button class="demo__toggle demo__toggle--active" data-lang="en">🇬🇧 EN</button>
  <button class="demo__toggle" data-lang="de">🇩🇪 DE</button>
</div>
```

**CSS for toggles and code section:**
```css
.extend { padding: 4rem 1rem; max-width: var(--content-max); margin: 0 auto; }
.extend__code pre { background: #111; color: #eee; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem; }
.extend__caption { text-align: center; color: #666; margin-top: 1rem; }
.demo__toggles { display: flex; gap: 0.5rem; justify-content: center; margin-bottom: 1rem; }
.demo__toggle { padding: 0.4rem 1rem; border: 1px solid var(--border); border-radius: 20px; background: transparent; color: var(--text); cursor: pointer; font-size: 0.85rem; }
.demo__toggle--active { background: var(--accent); color: white; border-color: var(--accent); }
```

**JS for toggling:**
```javascript
document.querySelectorAll('.demo__toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.demo__toggle').forEach(b => b.classList.remove('demo__toggle--active'));
    btn.classList.add('demo__toggle--active');
    const lang = btn.dataset.lang;
    const text = lang === 'de' ? BRIEFING_DE : BRIEFING_EN;
    typeMessage(demoContent, text);
  });
});
```

Add "Preview" label near the demo section subtitle.

- [ ] Step 1: Add EN/DE toggle HTML+CSS+JS
- [ ] Step 2: Verify typeMessage restart works on toggle
- [ ] Step 3: npm run build passes
- [ ] Step 4: Commit

---

### Task 5: Claims audit

- [ ] `grep -rn "WhatsApp" site/` → 0 results
- [ ] `grep -rn "Hermes" site/` → only in footer as optional note
- [ ] Feature cards match actual built-in sources (7 cards, no fake features)
- [ ] "deduplicated" claim: either implemented or softened to "collected"
- [ ] `npm run build` passes
- [ ] Demo text has no real personal data
