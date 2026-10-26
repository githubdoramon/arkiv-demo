import { useEffect } from 'react';

/** Shared decorative backdrop and input feedback for primary actions. */
export function Atmosphere() {
  useEffect(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const selector = '.primary-btn,.connect-btn,.quest-button';
    const press = (event: PointerEvent | KeyboardEvent) => {
      if (reduced.matches || !(event.target instanceof Element)) return;
      if (event instanceof KeyboardEvent && (event.repeat || !['Enter', ' '].includes(event.key))) return;
      const button = event.target.closest<HTMLButtonElement>(selector);
      if (!button || button.disabled) return;
      const bounds = button.getBoundingClientRect();
      const x = event instanceof PointerEvent ? event.clientX - bounds.left : bounds.width / 2;
      const y = event instanceof PointerEvent ? event.clientY - bounds.top : bounds.height / 2;
      button.style.setProperty('--press-x', `${x}px`);
      button.style.setProperty('--press-y', `${y}px`);
      const burst = button.getAnimations({subtree: true}).find(animation =>
        animation instanceof CSSAnimation && animation.animationName === 'button-burst');
      if (burst) { burst.currentTime = 0; burst.play(); }
      else button.classList.add('button-burst');
    };
    document.addEventListener('pointerdown', press);
    document.addEventListener('keydown', press);
    return () => {
      document.removeEventListener('pointerdown', press);
      document.removeEventListener('keydown', press);
    };
  }, []);
  return <div className="page-atmosphere" aria-hidden="true">
    <div className="ambient-light"/>
    <div className="ambient-grid"/>
    <div className="ambient-streak"/>
  </div>;
}
