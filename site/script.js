(() => {
    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        }
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.fade-in').forEach((el) => observer.observe(el));

    const btn = document.querySelector('.back-to-top');
    if (btn) {
        const toggle = () => btn.classList.toggle('visible', window.scrollY > 300);
        toggle();
        window.addEventListener('scroll', toggle, { passive: true });
        btn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Active navbar link indicator
    const navLinks = Array.from(document.querySelectorAll('.navbar a'));
    if (navLinks.length) {
        const path = location.pathname.split('/').pop() || 'index.html';
        const isIndex = path === '' || path === 'index.html';

        const clearCurrent = () => navLinks.forEach((a) => a.removeAttribute('aria-current'));
        const setCurrentByHref = (predicate) => {
            clearCurrent();
            const match = navLinks.find(predicate);
            if (match) match.setAttribute('aria-current', 'page');
        };

        if (!isIndex) {
            setCurrentByHref((a) => {
                const href = a.getAttribute('href') || '';
                return href === path;
            });
        } else {
            // On index, track sections via IntersectionObserver
            const sections = ['accueil', 'about', 'credits']
                .map((id) => document.getElementById(id))
                .filter(Boolean);

            const hashFor = (id) => `#${id}`;
            const highlight = (id) => {
                setCurrentByHref((a) => (a.getAttribute('href') || '') === hashFor(id));
            };

            highlight('accueil');

            if (sections.length) {
                const sectionObserver = new IntersectionObserver((entries) => {
                    const visible = entries
                        .filter((e) => e.isIntersecting)
                        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
                    if (visible) highlight(visible.target.id);
                }, { threshold: [0.35, 0.6], rootMargin: '-80px 0px -40% 0px' });
                sections.forEach((s) => sectionObserver.observe(s));
            }
        }
    }
})();
