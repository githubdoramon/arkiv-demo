import { useEffect, useRef } from 'react';

/** Reveal each item once and move artwork without rerendering the React tree. */
export function useLibraryMotion() {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const scope = ref.current;
    if (!scope) return;
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    let stop = () => {};
    function configure() {
      stop();
      if (!scope || preference.matches) return;
      const tracked = new Set<HTMLElement>();
      const reveal = (node: HTMLElement) => {
        node.classList.remove('motion-pending');
        node.classList.add('motion-visible');
      };
      const observer = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => {
        for (const entry of entries) if (entry.isIntersecting) {
          reveal(entry.target as HTMLElement);
          observer?.unobserve(entry.target);
        }
      }, {threshold: 0.06});
      function discover() {
        if (!observer || !scope) return;
        scope.querySelectorAll<HTMLElement>('[data-reveal]').forEach(node => {
          if (tracked.has(node)) return;
          tracked.add(node);
          node.classList.add('motion-pending');
          observer.observe(node);
        });
      }
      discover();
      const changes = new MutationObserver(discover);
      changes.observe(scope, {childList: true, subtree: true});
      const focus = (event: FocusEvent) => {
        const node = (event.target as Element).closest<HTMLElement>('[data-reveal]');
        if (node) { reveal(node); observer?.unobserve(node); }
      };
      scope.addEventListener('focusin', focus);
      let artwork: HTMLElement | null = null, frame = 0, x = 0, y = 0;
      const reset = () => {
        cancelAnimationFrame(frame); frame = 0;
        artwork?.style.removeProperty('--art-x');
        artwork?.style.removeProperty('--art-y');
        artwork = null;
      };
      const move = (event: PointerEvent) => {
        if (event.pointerType !== 'mouse') return;
        const target = (event.target as Element).closest<HTMLElement>('[data-art-depth]');
        if (target !== artwork) { reset(); artwork = target; }
        if (!artwork) return;
        const bounds = artwork.getBoundingClientRect();
        x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 12;
        y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 8;
        if (!frame) frame = requestAnimationFrame(() => {
          artwork?.style.setProperty('--art-x', `${x.toFixed(2)}px`);
          artwork?.style.setProperty('--art-y', `${y.toFixed(2)}px`);
          frame = 0;
        });
      };
      const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
      if (finePointer) scope.addEventListener('pointermove', move, {passive: true});
      scope.addEventListener('pointerleave', reset);
      window.addEventListener('blur', reset);
      stop = () => {
        observer?.disconnect(); changes.disconnect(); reset();
        scope.removeEventListener('focusin', focus);
        scope.removeEventListener('pointermove', move);
        scope.removeEventListener('pointerleave', reset);
        window.removeEventListener('blur', reset);
        for (const node of tracked) node.classList.remove('motion-pending', 'motion-visible');
      };
    }
    configure(); preference.addEventListener('change', configure);
    return () => { stop(); preference.removeEventListener('change', configure); };
  }, []);
  return ref;
}
