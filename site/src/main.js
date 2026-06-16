/* ── Scroll reveal + typing animation ── */

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

/* ── Smooth nav scroll (no-JS fallback via CSS already) ── */

document.addEventListener('DOMContentLoaded', () => {
  const demoContent = document.getElementById('demoContent');
  if (demoContent) {
    typeMessage(demoContent, BRIEFING_EN);
  }
  setupRevealAnimations();
  setupLanguageToggle();
});
