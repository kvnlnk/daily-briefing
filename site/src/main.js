/* ── Scroll reveal + typing animation + pipeline ── */

import './styles/main.css';

const BRIEFING_EN = `🌅 Good morning!

London: 18°C, ⛅ partly cloudy — High 20°C, Low 13°C. 60% rain chance.

📅 Today: 2 events — Sprint Review (10:30) + Team Lunch (12:30).

🐙 GitHub: 1 open PR, 1 assigned issue.

📰 Top News: Tech giants announce new AI chip partnership. Open-source framework reaches 100K stars.

Have a great day! ☕`;

const BRIEFING_DE = `🌅 Guten Morgen!

Berlin: 18°C, ⛅ teils bewölkt — Höchstwert 20°C, Tiefstwert 13°C. 60% Regenrisiko.

📅 Heute: 2 Termine — Sprint-Review (10:30) + Mittagessen (12:30).

🐙 GitHub: 1 offener PR, 1 Issue zugewiesen.

📰 Top-News: Tech-Giganten kündigen neue KI-Chip-Partnerschaft an. Open-Source-Framework erreicht 100.000 Sterne.

Schönen Tag! ☕`;

/* ── Typing effect ── */

function typeMessage(element, text, speed = 12) {
  const typingIndicator = document.getElementById('demoTyping');
  let index = 0;
  let result = '';

  // Reset display
  if (typingIndicator) typingIndicator.style.display = 'inline-block';

  // Hide typing indicator after a moment
  setTimeout(() => {
    if (typingIndicator) typingIndicator.style.display = 'none';
  }, 600);

  function type() {
    if (index < text.length) {
      result += text[index];
      element.textContent = result;
      index++;
      // Speed varies for natural feel
      const delay = text[index] === '\n' ? speed * 3 : speed;
      setTimeout(type, delay + (Math.random() * 8 - 4));
    }
  }

  setTimeout(type, 800);
}

/* ── Pipeline animation orchestration ── */

let pipelineTimeout = null;
let pipelineLoopTimeout = null;

function animatePipeline() {
  const stages = document.querySelectorAll('.pipeline__stage');
  const arrows = document.querySelectorAll('.pipeline__arrow');
  const all = [];

  // Interleave stages and arrows: stage0, arrow0, stage1, arrow1, ...
  stages.forEach((s, i) => {
    all.push(s);
    if (arrows[i]) all.push(arrows[i]);
  });

  // Reset all first
  all.forEach(el => el.classList.remove('visible'));
  stages.forEach(s => {
    const icons = s.querySelectorAll('.pipeline__icon');
    icons.forEach(ic => {
      ic.style.animation = 'none';
      ic.offsetHeight; // trigger reflow
      ic.style.animation = '';
    });
  });

  // Clear any running timeouts
  if (pipelineTimeout) {
    clearTimeout(pipelineTimeout);
    pipelineTimeout = null;
  }
  if (pipelineLoopTimeout) {
    clearTimeout(pipelineLoopTimeout);
    pipelineLoopTimeout = null;
  }

  let delay = 0;
  const STAGE_DELAY = 1400; // ms between each stage reveal

  all.forEach((el, idx) => {
    pipelineTimeout = setTimeout(() => {
      el.classList.add('visible');

      // For stage 3 (summarize), re-trigger spinner animation
      if (el.classList.contains('pipeline__stage') && el.dataset.stage === '3') {
        const spinner = el.querySelector('.pipeline__spinner');
        if (spinner) {
          spinner.style.animation = 'none';
          spinner.offsetHeight;
          spinner.style.animation = 'spin 0.8s linear infinite';
        }
      }
    }, delay);

    // Each pair (stage + arrow) gets the same delay, then next adds STAGE_DELAY
    if (idx % 2 === 1) {
      delay += STAGE_DELAY;
    }
  });

  // After all stages have appeared, wait and then trigger phone typing
  const totalDuration = (stages.length * 2 - 1) * STAGE_DELAY / 2 + STAGE_DELAY;
  pipelineLoopTimeout = setTimeout(() => {
    // Scroll demo into view and start typing
    const demoSection = document.getElementById('demo');
    if (demoSection) {
      demoSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    // Start the existing phone typing
    const demoContent = document.getElementById('demoContent');
    if (demoContent) {
      // Check if language toggle is already set
      const activeToggle = document.querySelector('.demo__toggle--active');
      const lang = activeToggle ? activeToggle.dataset.lang : 'en';
      const text = lang === 'de' ? BRIEFING_DE : BRIEFING_EN;
      // Small delay for scroll
      setTimeout(() => typeMessage(demoContent, text), 600);
    }

    // Schedule auto-loop: after typing finishes (~8s) + idle buffer, replay pipeline
    pipelineLoopTimeout = setTimeout(() => {
      // Scroll back to pipeline
      const pipelineSection = document.getElementById('pipeline');
      if (pipelineSection) {
        pipelineSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      setTimeout(animatePipeline, 800);
    }, 10000);
  }, totalDuration + 500);
}

/* ── Intersection Observer for scroll reveals ── */

function setupRevealAnimations() {
  const cards = document.querySelectorAll('.card, .step');
  if (cards.length === 0) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  cards.forEach((card) => observer.observe(card));
}

/* ── Pipeline start on scroll into view ── */

let pipelineStarted = false;

function setupPipelineTrigger() {
  const pipelineSection = document.getElementById('pipeline');
  if (!pipelineSection) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !pipelineStarted) {
          pipelineStarted = true;
          animatePipeline();
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );

  observer.observe(pipelineSection);
}

/* ── Replay button ── */

function setupReplayButton() {
  const replayBtn = document.getElementById('pipelineReplay');
  if (!replayBtn) return;

  replayBtn.addEventListener('click', () => {
    if (pipelineLoopTimeout) {
      clearTimeout(pipelineLoopTimeout);
      pipelineLoopTimeout = null;
    }
    animatePipeline();
  });
}

/* ── Language toggle ── */

function setupLanguageToggle() {
  const demoContent = document.getElementById('demoContent');
  if (!demoContent) return;

  document.querySelectorAll('.demo__toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.demo__toggle').forEach(b => b.classList.remove('demo__toggle--active'));
      btn.classList.add('demo__toggle--active');
      const lang = btn.dataset.lang;
      const text = lang === 'de' ? BRIEFING_DE : BRIEFING_EN;
      typeMessage(demoContent, text);
    });
  });
}

/* ── Init ── */

document.addEventListener('DOMContentLoaded', () => {
  const demoContent = document.getElementById('demoContent');
  if (demoContent) {
    typeMessage(demoContent, BRIEFING_EN);
  }
  setupRevealAnimations();
  setupLanguageToggle();
  setupPipelineTrigger();
  setupReplayButton();
});
