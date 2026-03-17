// Nav scroll
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
});

// Fade-in observer
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
    });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// Ripple ring touch handling for mobile
const rings = document.querySelectorAll('.ripple-ring');
const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

if (isTouchDevice) {
    rings.forEach(ring => {
        ring.addEventListener('touchstart', (e) => {
            // Remove touched class from all rings first
            rings.forEach(r => r.classList.remove('touched'));
            ring.classList.add('touched');
        }, { passive: true });
    });

    // Remove touched state when tapping outside
    document.addEventListener('touchstart', (e) => {
        if (!e.target.closest('.ripple-ring')) {
            rings.forEach(r => r.classList.remove('touched'));
        }
    }, { passive: true });
}

// Staggered entrance for ripple rings on scroll
const rippleObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const rings = entry.target.querySelectorAll('.ripple-ring');
            rings.forEach((ring, i) => {
                setTimeout(() => {
                    ring.style.opacity = '1';
                    ring.style.transform = 'scale(1)';
                }, i * 120);
            });
            rippleObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.2 });

const rippleVisual = document.querySelector('.ripple-visual');
if (rippleVisual) {
    // Set initial state for staggered entrance
    rings.forEach(ring => {
        ring.style.opacity = '0';
        ring.style.transform = 'scale(0.85)';
        ring.style.transition = 'opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.4s';
    });
    rippleObserver.observe(rippleVisual);
}

// Weight moments — one at a time, flash like intrusive thoughts
const weightMoments = document.querySelector('.weight-moments');
if (weightMoments) {
    const moments = weightMoments.querySelectorAll('.weight-moment');

    // Wrap words in spans, preserving colored spans
    moments.forEach(m => {
        let wordIndex = 0;
        const fragment = document.createDocumentFragment();
        m.childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                const parts = node.textContent.split(/(\s+)/);
                parts.forEach(part => {
                    if (part.trim()) {
                        const s = document.createElement('span');
                        s.className = 'wm-word';
                        s.textContent = part;
                        s.style.transitionDelay = (wordIndex * 0.12) + 's';
                        wordIndex++;
                        fragment.appendChild(s);
                    } else if (part) {
                        fragment.appendChild(document.createTextNode(part));
                    }
                });
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                const s = document.createElement('span');
                s.className = 'wm-word ' + node.className;
                s.textContent = node.textContent;
                s.style.transitionDelay = (wordIndex * 0.12) + 's';
                wordIndex++;
                fragment.appendChild(s);
            }
        });
        m.innerHTML = '';
        m.appendChild(fragment);
    });

    let currentMoment = -1;
    let cycleInterval = null;
    let momentCycles = 0;

    function flashNext() {
        moments.forEach(m => {
            m.classList.remove('active');
            m.querySelectorAll('.wm-word').forEach(w => { w.style.transitionDelay = '0s'; });
        });
        currentMoment = (currentMoment + 1) % moments.length;
        if (currentMoment === 0) momentCycles++;
        // Stop after one full cycle — show last thought + scroll cue
        if (momentCycles >= 1 && currentMoment === 0) {
            clearInterval(cycleInterval);
            // Show last thought and scroll cue
            const last = moments[moments.length - 1];
            last.querySelectorAll('.wm-word').forEach((w, i) => {
                w.style.transitionDelay = (i * 0.12) + 's';
            });
            last.classList.add('active');
            const cue = document.getElementById('weightScrollCue');
            if (cue) setTimeout(() => cue.classList.add('visible'), 1500);
            return;
        }
        const current = moments[currentMoment];
        current.querySelectorAll('.wm-word').forEach((w, i) => {
            w.style.transitionDelay = (i * 0.12) + 's';
        });
        current.classList.add('active');
    }

    const weightObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !cycleInterval) {
                flashNext();
                cycleInterval = setInterval(flashNext, 3000);
                weightObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });
    weightObserver.observe(weightMoments);
}

// Weight questions — word-by-word reveal, one question at a time
const weightQuestions = document.querySelector('.weight-questions');
if (weightQuestions) {
    const questions = weightQuestions.querySelectorAll('.weight-question');
    // Wrap each word in a span
    questions.forEach(q => {
        const text = q.textContent;
        const words = text.split(/\s+/);
        q.innerHTML = words.map(w => '<span class="wq-word">' + w + '</span>').join(' ');
    });

    let currentQ = -1;
    let qInterval = null;
    let qCycles = 0;

    function revealNextQuestion() {
        // Clear ALL questions first — prevents overlap from stale classes
        questions.forEach(q => {
            q.classList.remove('active', 'exiting');
            q.querySelectorAll('.wq-word').forEach(w => { w.style.transitionDelay = '0s'; });
        });

        currentQ = (currentQ + 1) % questions.length;
        if (currentQ === 0) qCycles++;
        // Stop after one full cycle — keep last question visible + scroll cue
        if (qCycles >= 1 && currentQ === 0) {
            clearInterval(qInterval);
            const last = questions[questions.length - 1];
            last.classList.add('active');
            last.querySelectorAll('.wq-word').forEach((w, i) => {
                w.style.transitionDelay = (i * 0.25) + 's';
            });
            const cue = document.getElementById('questionsScrollCue');
            if (cue) setTimeout(() => cue.classList.add('visible'), 2000);
            return;
        }

        const q = questions[currentQ];
        q.classList.add('active');
        q.querySelectorAll('.wq-word').forEach((w, i) => {
            w.style.transitionDelay = (i * 0.25) + 's';
        });
    }

    const qObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !qInterval) {
                revealNextQuestion();
                qInterval = setInterval(revealNextQuestion, 5500);
                qObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });
    qObserver.observe(weightQuestions);
}

// Mechanism beats — flow in one after another
const mechanismBeats = document.getElementById('mechanismBeats');
if (mechanismBeats) {
    const beats = mechanismBeats.querySelectorAll('.mechanism-beat');
    const mechObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                beats.forEach((beat, i) => {
                    setTimeout(() => beat.classList.add('visible'), i * 600);
                });
                mechObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });
    mechObserver.observe(mechanismBeats);
}


// Show confirmation if redirected back after form submit
if (new URLSearchParams(window.location.search).get('joined') === '1') {
    const msg = document.getElementById('waitlistMsg');
    msg.textContent = 'You are on the list. We will reach out.';
    document.getElementById('waitlist').scrollIntoView();
    window.history.replaceState({}, '', window.location.pathname);
}
