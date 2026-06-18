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

let typingTimer = null;
let typingTimeouts = [];

function cancelTyping() {
  if (typingTimer) { clearTimeout(typingTimer); typingTimer = null; }
  typingTimeouts.forEach(t => clearTimeout(t));
  typingTimeouts = [];
}

function typeMessage(element, text, speed = 12) {
  // Cancel any running animation first
  cancelTyping();

  const typingIndicator = document.getElementById('demoTyping');
  let index = 0;
  let result = '';

  // Reset display
  element.textContent = '';
  if (typingIndicator) typingIndicator.style.display = 'inline-block';

  // Hide typing indicator after a moment
  typingTimer = setTimeout(() => {
    if (typingIndicator) typingIndicator.style.display = 'none';
    typingTimer = null;
  }, 600);

  function type() {
    if (index < text.length) {
      result += text[index];
      element.textContent = result;
      index++;
      const delay = text[index] === '\n' ? speed * 3 : speed;
      const t = setTimeout(type, delay + (Math.random() * 8 - 4));
      typingTimeouts.push(t);
    }
  }

  const start = setTimeout(type, 800);
  typingTimeouts.push(start);
}

/* ── Pipeline animation orchestration ── */

let pipelineTimeout = null;
let pipelineAnimationActive = false;

function animatePipeline() {
  const stages = document.querySelectorAll('.pipeline__stage');
  const arrows = document.querySelectorAll('.pipeline__arrow');
  const all = [];

  // Don't restart if already playing
  if (pipelineAnimationActive) return;
  pipelineAnimationActive = true;

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

  if (pipelineTimeout) {
    clearTimeout(pipelineTimeout);
    pipelineTimeout = null;
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

  // After all stages have appeared, show the phone typing but DON'T auto-scroll
  const totalDuration = (stages.length * 2 - 1) * STAGE_DELAY / 2 + STAGE_DELAY;
  setTimeout(() => {
    const demoContent = document.getElementById('demoContent');
    if (demoContent) {
      const activeToggle = document.querySelector('.demo__toggle--active');
      const lang = activeToggle ? activeToggle.dataset.lang : 'en';
      const text = lang === 'de' ? BRIEFING_DE : BRIEFING_EN;
      setTimeout(() => typeMessage(demoContent, text), 600);
    }
    pipelineAnimationActive = false; // allow replay
  }, totalDuration + 500);
}

/* ── Intersection Observer for scroll reveals ── */

function setupRevealAnimations() {
  const cards = document.querySelectorAll('.card');
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

/* ── Replay on tap ── */

function setupPipelineTapReplay() {
  const pipelineSection = document.getElementById('pipeline');
  if (!pipelineSection) return;

  pipelineSection.addEventListener('click', (e) => {
    // Don't trigger if clicking a link inside the pipeline
    if (e.target.closest('a')) return;
    pipelineAnimationActive = false;
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

/* ── Carousel dots for Run It Your Way ── */

function setupCarouselDots() {
  const grid = document.getElementById('integrationsGrid');
  const dots = document.getElementById('integrationsDots');
  if (!grid || !dots) return;

  const cards = grid.querySelectorAll('.integrations__card');
  if (cards.length === 0) return;

  // Build snap-position map once (cards can only reflow on resize)
  let snapPositions = [];

  function recomputeSnapPositions() {
    const gridRect = grid.getBoundingClientRect();
    snapPositions = Array.from(cards).map(c => {
      const rect = c.getBoundingClientRect();
      // Position relative to grid's scrollable content area
      return rect.left - gridRect.left + grid.scrollLeft;
    });
  }
  recomputeSnapPositions();

  // Refresh on resize (layout may shift)
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(recomputeSnapPositions, 150);
  });

  // Create dot for each card
  cards.forEach(() => {
    const dot = document.createElement('span');
    dots.appendChild(dot);
  });
  const allDots = dots.querySelectorAll('span');
  if (allDots.length > 0) allDots[0].classList.add('active');

  // Hide dots entirely when there's no overflow (desktop)
  function updateDotsVisibility() {
    const hasOverflow = grid.scrollWidth > grid.clientWidth;
    dots.style.display = hasOverflow ? '' : 'none';
  }
  updateDotsVisibility();
  window.addEventListener('resize', updateDotsVisibility);

  // Update active dot on scroll — find the nearest snap position
  let ticking = false;
  grid.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const left = grid.scrollLeft;
        // Find the card whose offsetLeft is closest to scrollLeft
        let bestIdx = 0;
        let bestDist = Infinity;
        snapPositions.forEach((pos, i) => {
          const dist = Math.abs(pos - left);
          if (dist < bestDist) { bestDist = dist; bestIdx = i; }
        });
        allDots.forEach((d, i) => d.classList.toggle('active', i === bestIdx));
        ticking = false;
      });
      ticking = true;
    }
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
  setupPipelineTapReplay();
  setupCarouselDots();

  /* ── Burger menu toggle ── */
  const burger = document.getElementById('navBurger');
  const overlay = document.getElementById('navOverlay');
  if (burger && overlay) {
    burger.addEventListener('click', () => {
      const isOpen = overlay.classList.toggle('visible');
      burger.setAttribute('aria-expanded', isOpen);
      overlay.setAttribute('aria-hidden', !isOpen);
    });
    // Close menu on any overlay tap (link or background)
    overlay.addEventListener('click', () => {
      overlay.classList.remove('visible');
      burger.setAttribute('aria-expanded', 'false');
      overlay.setAttribute('aria-hidden', 'true');
    });
  }
});
