/**
 * Certichain Africa — Animation Engine
 */

const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ═══════════════════════════════════════════
   1. NAVBAR — glassmorphism on scroll
═══════════════════════════════════════════ */
const navbar = document.querySelector('.c-navbar');
if (navbar) {
  const onScroll = () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/* ═══════════════════════════════════════════
   2. SMOOTH SCROLL for anchor links
═══════════════════════════════════════════ */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

/* ═══════════════════════════════════════════
   3. BUTTON RIPPLE
═══════════════════════════════════════════ */
document.addEventListener('click', e => {
  const btn = e.target.closest('.btn');
  if (!btn || btn.disabled) return;
  const rect   = btn.getBoundingClientRect();
  const size   = Math.max(rect.width, rect.height) * 2.2;
  const x      = e.clientX - rect.left - size / 2;
  const y      = e.clientY - rect.top  - size / 2;
  const ripple = document.createElement('span');
  ripple.style.cssText = `position:absolute;width:${size}px;height:${size}px;left:${x}px;top:${y}px;border-radius:50%;background:rgba(255,255,255,0.22);transform:scale(0);animation:cc-ripple 0.6s ease forwards;pointer-events:none;`;
  btn.style.position = 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
});

/* ═══════════════════════════════════════════
   4. SCROLL REVEAL — IntersectionObserver
═══════════════════════════════════════════ */
if (!REDUCED && 'IntersectionObserver' in window) {

  /* Auto-tag landing page elements */
  const tagStagger = (selector, reveal = 'up') => {
    document.querySelectorAll(selector).forEach((el, i) => {
      if (!el.hasAttribute('data-reveal')) {
        el.setAttribute('data-reveal', reveal);
        el.setAttribute('data-delay', String(Math.min(i * 100, 500)));
      }
    });
  };

  tagStagger('.feature-card', 'up');
  tagStagger('.step-card',    'up');
  tagStagger('.stat-card',    'up');
  tagStagger('.cert-card',    'up');
  tagStagger('.card--hover',  'up');
  tagStagger('.lp-roi-card',  'up');
  tagStagger('.p-card',       'up');

  /* Tag section heads */
  document.querySelectorAll('.section-head').forEach(el => {
    if (!el.hasAttribute('data-reveal')) el.setAttribute('data-reveal', 'up');
  });

  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -48px 0px' });

  document.querySelectorAll('[data-reveal]').forEach(el => revealObserver.observe(el));
}

/* ═══════════════════════════════════════════
   5. CERTIFICATE MOCKUP — 3D tilt on mouse
═══════════════════════════════════════════ */
if (!REDUCED) {
  const wrapper = document.querySelector('.mockup-wrapper');
  const mockup  = document.querySelector('.cert-mockup');
  if (wrapper && mockup) {
    const MAX_TILT = 12;
    wrapper.addEventListener('mousemove', e => {
      const r   = wrapper.getBoundingClientRect();
      const cx  = r.left + r.width  / 2;
      const cy  = r.top  + r.height / 2;
      const dx  = (e.clientX - cx) / (r.width  / 2);
      const dy  = (e.clientY - cy) / (r.height / 2);
      const rx  = -dy * MAX_TILT;
      const ry  =  dx * MAX_TILT;
      mockup.style.transform = `perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.02)`;
    });
    wrapper.addEventListener('mouseleave', () => {
      mockup.style.transition = 'transform 0.5s cubic-bezier(0.25,0.46,0.45,0.94)';
      mockup.style.transform  = 'perspective(1200px) rotateY(-4deg) rotateX(3deg)';
      setTimeout(() => { mockup.style.transition = 'transform 0.08s linear'; }, 500);
    });
  }
}

/* ═══════════════════════════════════════════
   6. CURSOR GLOW (landing page only)
═══════════════════════════════════════════ */
if (!REDUCED && document.body.classList.contains('landing-body')) {
  const glow = document.createElement('div');
  glow.className = 'cursor-glow';
  document.body.appendChild(glow);
  let mx = -999, my = -999;
  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
  let raf;
  const moveGlow = () => {
    glow.style.left = mx + 'px';
    glow.style.top  = my + 'px';
    raf = requestAnimationFrame(moveGlow);
  };
  raf = requestAnimationFrame(moveGlow);
}

/* ═══════════════════════════════════════════
   7. HERO BLOBS — parallax on mouse
═══════════════════════════════════════════ */
if (!REDUCED) {
  const blobs = document.querySelectorAll('.hero-blob');
  if (blobs.length) {
    document.addEventListener('mousemove', e => {
      const cx = window.innerWidth  / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;
      blobs.forEach((b, i) => {
        const depth = (i + 1) * 8;
        b.style.transform = `translate(${dx * depth}px, ${dy * depth}px) scale(${1 + Math.abs(dx) * 0.02})`;
      });
    }, { passive: true });
  }
}

/* ═══════════════════════════════════════════
   8. CANVAS PARTICLES (hero section)
═══════════════════════════════════════════ */
if (!REDUCED) {
  const hero = document.querySelector('.hero');
  if (hero) {
    const canvas  = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:0;opacity:0.55;';
    hero.insertBefore(canvas, hero.firstChild);

    const ctx = canvas.getContext('2d');
    let w, h, particles = [];

    const resize = () => {
      w = canvas.width  = hero.offsetWidth;
      h = canvas.height = hero.offsetHeight;
    };

    const createParticle = () => ({
      x: Math.random() * w, y: Math.random() * h,
      r: Math.random() * 1.5 + 0.4,
      vx: (Math.random() - 0.5) * 0.22,
      vy: (Math.random() - 0.5) * 0.22,
      alpha: Math.random() * 0.5 + 0.1,
    });

    const init = () => {
      resize();
      particles = Array.from({ length: 60 }, createParticle);
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(37,99,235,${p.alpha})`;
        ctx.fill();
      });
      // Draw connecting lines for nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 90) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(37,99,235,${0.07 * (1 - dist / 90)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    };

    window.addEventListener('resize', resize, { passive: true });
    init();
    draw();
  }
}

/* ═══════════════════════════════════════════
   9. COUNTER ANIMATION for stat numbers
═══════════════════════════════════════════ */
if (!REDUCED && 'IntersectionObserver' in window) {
  const easeOut = t => 1 - Math.pow(1 - t, 3);
  const animateCounter = el => {
    const target  = parseFloat(el.dataset.count);
    const suffix  = el.dataset.suffix || '';
    const duration = 1800;
    const start   = performance.now();
    const step = now => {
      const progress = Math.min((now - start) / duration, 1);
      const value    = target * easeOut(progress);
      el.textContent = (Number.isInteger(target) ? Math.round(value) : value.toFixed(1)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const counterObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('[data-count]').forEach(el => counterObserver.observe(el));
}

/* ═══════════════════════════════════════════
   10. HERO CTA — add glow class
═══════════════════════════════════════════ */
const heroCta = document.querySelector('.hero__actions .btn-primary');
if (heroCta && !REDUCED) heroCta.classList.add('btn-glow');
