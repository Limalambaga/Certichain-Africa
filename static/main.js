/**
 * Certichain Africa — UI micro-interactions
 */

// ── Navbar scroll shadow ──────────────────────────────
const navbar = document.querySelector('.c-navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 8
      ? '0 2px 16px rgba(10,30,82,0.10)'
      : '0 1px 2px rgba(10,30,82,0.04)';
  }, { passive: true });
}

// ── Button ripple ─────────────────────────────────────
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn');
  if (!btn || btn.disabled) return;

  const rect   = btn.getBoundingClientRect();
  const size   = Math.max(rect.width, rect.height) * 2;
  const x      = e.clientX - rect.left - size / 2;
  const y      = e.clientY - rect.top  - size / 2;
  const ripple = document.createElement('span');

  ripple.style.cssText = `
    position:absolute; width:${size}px; height:${size}px;
    left:${x}px; top:${y}px; border-radius:50%;
    background:rgba(255,255,255,0.25);
    transform:scale(0); animation:cc-ripple 0.55s ease forwards;
    pointer-events:none;
  `;

  btn.style.position = 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
});

// ── Smooth scroll for anchor links ───────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// ── Fade-in on scroll (Intersection Observer) ─────────
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity    = '1';
        entry.target.style.transform  = 'none';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.feature-card, .step-card, .stat-card, .cert-card, .card--hover').forEach((el, i) => {
    el.style.opacity   = '0';
    el.style.transform = 'translateY(18px)';
    el.style.transition = `opacity 0.45s ease ${i * 0.06}s, transform 0.45s ease ${i * 0.06}s`;
    observer.observe(el);
  });
}

// ── Keyframes injection ───────────────────────────────
const style = document.createElement('style');
style.textContent = `
  @keyframes cc-ripple { to { transform: scale(1); opacity: 0; } }
`;
document.head.appendChild(style);

// ── Accessibility: skip reduced motion ───────────────
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.querySelectorAll('[style*="transition"], [style*="animation"]').forEach(el => {
    el.style.transition = 'none';
    el.style.animation  = 'none';
    el.style.opacity    = '1';
    el.style.transform  = 'none';
  });
}
