/* ── Scroll reveal + WhatsApp typing animation ── */

import './styles/main.css';

const BRIEFING_TEXT = `☀🌅 Guten Morgen!

Frankfurt: 18°C, ⛅ teils bewölkt — Höchstwert 20°C, Tiefstwert 13°C. 60% Regenrisiko.

📅 Heute: 2 Termine — Sprint-Review (10:30) + Mittagessen mit Team (12:30).

🐙 GitHub: 1 offener PR (Update filter logic), 1 Issue assigned. 3 Repos aktiv: glitch, glitch-site, snapshot-cli.

📰 Top-News: Intel „Raptor Lake Next" — DDR4 und angeblich Anfang 2027 fertig. VW setzt auf die Telekom: T-Systems baut weltweite Cloud.

Schönen Tag! ☕`;

/* ── WhatsApp typing effect ── */

function typeMessage(element, text, speed = 12) {
  const typingIndicator = document.getElementById('demoTyping');
  let index = 0;
  let result = '';

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

/* ── Smooth nav scroll (no-JS fallback via CSS already) ── */

document.addEventListener('DOMContentLoaded', () => {
  const demoContent = document.getElementById('demoContent');
  if (demoContent) {
    typeMessage(demoContent, BRIEFING_TEXT);
  }
  setupRevealAnimations();
});
