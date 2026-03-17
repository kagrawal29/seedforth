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

// Auto-scroll helper — only scrolls if section is still in view
function autoScrollToNext(currentSection, delay) {
    setTimeout(() => {
        const rect = currentSection.getBoundingClientRect();
        const inView = rect.top >= -100 && rect.top < window.innerHeight * 0.5;
        if (inView) {
            const next = currentSection.nextElementSibling;
            if (next) next.scrollIntoView({ behavior: 'smooth' });
        }
    }, delay);
}

// Ripple ring touch handling for mobile
const rings = document.querySelectorAll('.ripple-ring');
const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

if (isTouchDevice) {
    rings.forEach(ring => {
        ring.addEventListener('touchstart', (e) => {
            rings.forEach(r => r.classList.remove('touched'));
            ring.classList.add('touched');
        }, { passive: true });
    });

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
    rings.forEach(ring => {
        ring.style.opacity = '0';
        ring.style.transform = 'scale(0.85)';
        ring.style.transition = 'opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.4s';
    });
    rippleObserver.observe(rippleVisual);
}

// ---- WEIGHT MOMENTS (thoughts) ----
const weightMoments = document.querySelector('.weight-moments');
if (weightMoments) {
    const moments = weightMoments.querySelectorAll('.weight-moment');
    const weightSection = weightMoments.closest('.the-weight');

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
    let momentsDone = false;

    function flashNext() {
        moments.forEach(m => {
            m.classList.remove('active');
            m.querySelectorAll('.wm-word').forEach(w => { w.style.transitionDelay = '0s'; });
        });
        currentMoment = (currentMoment + 1) % moments.length;
        if (currentMoment === 0) momentCycles++;
        // Stop after one full cycle
        if (momentCycles >= 1 && currentMoment === 0) {
            clearInterval(cycleInterval);
            cycleInterval = null;
            momentsDone = true;
            const last = moments[moments.length - 1];
            last.querySelectorAll('.wm-word').forEach((w, i) => {
                w.style.transitionDelay = (i * 0.12) + 's';
            });
            last.classList.add('active');
            // Show scroll cue after cycle, then auto-scroll with generous pause
            const cue = document.getElementById('weightScrollCue');
            if (cue) setTimeout(() => cue.classList.add('visible'), 1500);
            if (weightSection) autoScrollToNext(weightSection, 5000);
            return;
        }
        const current = moments[currentMoment];
        current.querySelectorAll('.wm-word').forEach((w, i) => {
            w.style.transitionDelay = (i * 0.12) + 's';
        });
        current.classList.add('active');
    }

    // Only start when section is mostly in view; don't restart if done
    const weightObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !cycleInterval && !momentsDone) {
                flashNext();
                cycleInterval = setInterval(flashNext, 3000);
            }
        });
    }, { threshold: 0.7 });
    weightObserver.observe(weightSection || weightMoments);
}

// ---- WEIGHT QUESTIONS ----
const weightQuestions = document.querySelector('.weight-questions');
if (weightQuestions) {
    const questions = weightQuestions.querySelectorAll('.weight-question');
    const questionsSection = weightQuestions.closest('.weight-questions-section');

    questions.forEach(q => {
        const text = q.textContent;
        const words = text.split(/\s+/);
        q.innerHTML = words.map(w => '<span class="wq-word">' + w + '</span>').join(' ');
    });

    let currentQ = -1;
    let qInterval = null;
    let qCycles = 0;
    let questionsDone = false;

    function revealNextQuestion() {
        questions.forEach(q => {
            q.classList.remove('active', 'exiting');
            q.querySelectorAll('.wq-word').forEach(w => { w.style.transitionDelay = '0s'; });
        });

        currentQ = (currentQ + 1) % questions.length;
        if (currentQ === 0) qCycles++;
        // Stop after one full cycle
        if (qCycles >= 1 && currentQ === 0) {
            clearInterval(qInterval);
            qInterval = null;
            questionsDone = true;
            const last = questions[questions.length - 1];
            last.classList.add('active');
            last.querySelectorAll('.wq-word').forEach((w, i) => {
                w.style.transitionDelay = (i * 0.25) + 's';
            });
            // Show scroll cue after cycle, then auto-scroll with generous pause
            const cue = document.getElementById('questionsScrollCue');
            if (cue) setTimeout(() => cue.classList.add('visible'), 2000);
            if (questionsSection) autoScrollToNext(questionsSection, 6000);
            return;
        }

        const q = questions[currentQ];
        q.classList.add('active');
        q.querySelectorAll('.wq-word').forEach((w, i) => {
            w.style.transitionDelay = (i * 0.25) + 's';
        });
    }

    // Only start when section is mostly in view; don't restart if done
    const qObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !qInterval && !questionsDone) {
                revealNextQuestion();
                qInterval = setInterval(revealNextQuestion, 5500);
            }
        });
    }, { threshold: 0.7 });
    qObserver.observe(questionsSection || weightQuestions);
}

// ---- COLLAPSE STAGE (Before → Transform → After) ----
// Replays every time user scrolls into view
const collapseStage = document.getElementById('collapseStage');
if (collapseStage) {
    const mechanismSection = collapseStage.closest('.the-mechanism');
    const beforePhase = collapseStage.querySelector('.collapse-before-phase');
    const transformPhase = collapseStage.querySelector('.collapse-transform-phase');
    const afterPhase = collapseStage.querySelector('.collapse-after-phase');
    let collapseTimeouts = [];
    let collapseRunning = false;

    function resetCollapseStage() {
        // Clear pending timeouts
        collapseTimeouts.forEach(t => clearTimeout(t));
        collapseTimeouts = [];
        collapseRunning = false;

        // Reset all phases
        [beforePhase, transformPhase, afterPhase].forEach(phase => {
            phase.classList.remove('active', 'dissolving');
            phase.querySelectorAll('.vflow-node, .vflow-connector').forEach(el => {
                el.classList.remove('revealed');
            });
        });

        // Force reflow so CSS animations can replay
        void collapseStage.offsetHeight;

        // Hide scroll cue
        const cue = document.getElementById('mechanismScrollCue');
        if (cue) cue.classList.remove('visible');
    }

    function revealVflowItems(phase, baseDelay) {
        const items = phase.querySelectorAll('.vflow-node, .vflow-connector');
        items.forEach((item, i) => {
            const t = setTimeout(() => item.classList.add('revealed'), baseDelay + i * 400);
            collapseTimeouts.push(t);
        });
        return baseDelay + items.length * 400;
    }

    function runCollapseAnimation() {
        if (collapseRunning) return;
        resetCollapseStage();
        collapseRunning = true;

        // Step 1: Show Before, stagger vertical items
        beforePhase.classList.add('active');
        const beforeEnd = revealVflowItems(beforePhase, 300);

        // Step 2: Dissolve Before
        const dissolveAt = beforeEnd + 1200;
        collapseTimeouts.push(setTimeout(() => {
            beforePhase.classList.remove('active');
            beforePhase.classList.add('dissolving');
        }, dissolveAt));

        // Step 3: Launch transformation
        const launchAt = dissolveAt + 1000;
        collapseTimeouts.push(setTimeout(() => {
            transformPhase.classList.add('active');
        }, launchAt));

        // Step 4: Dissolve transformation
        const launchEnd = launchAt + 3000;
        collapseTimeouts.push(setTimeout(() => {
            transformPhase.classList.remove('active');
            transformPhase.classList.add('dissolving');
        }, launchEnd));

        // Step 5: Show After
        const afterAt = launchEnd + 800;
        collapseTimeouts.push(setTimeout(() => {
            afterPhase.classList.add('active');
            revealVflowItems(afterPhase, 200);
        }, afterAt));

        // Step 6: Scroll cue + auto-scroll
        const cueAt = afterAt + 2000;
        collapseTimeouts.push(setTimeout(() => {
            const cue = document.getElementById('mechanismScrollCue');
            if (cue) cue.classList.add('visible');
            collapseRunning = false;
        }, cueAt));

        collapseTimeouts.push(setTimeout(() => {
            if (mechanismSection) autoScrollToNext(mechanismSection, 0);
        }, cueAt + 3000));
    }

    // Re-observe: replay on every entry, reset on exit
    const collapseObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                runCollapseAnimation();
            } else {
                resetCollapseStage();
            }
        });
    }, { threshold: 0.6 });
    collapseObserver.observe(collapseStage);
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
