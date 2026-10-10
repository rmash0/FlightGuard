import "./BubbleBackground.css";

const BUBBLE_COUNT = 14;

// Deterministic spread (no Math.random) so renders stay pure and stable.
const BUBBLES = Array.from({ length: BUBBLE_COUNT }, (_, i) => ({
  left: `${(i * 37 + 5) % 100}%`,
  size: `${16 + ((i * 23) % 52)}px`,
  duration: `${18 + ((i * 7) % 15)}s`,
  // Negative delay starts each bubble mid-flight instead of all at the bottom.
  delay: `${-((i * 5) % 22)}s`,
}));

// Decorative full-screen layer: rising bubbles by day, stars by night.
function BubbleBackground() {
  return (
    <div className="bubble-background" aria-hidden="true">
      <div className="bubble-background__stars" />
      {BUBBLES.map((bubble, i) => (
        <span
          key={i}
          className="bubble-background__bubble"
          style={{
            left: bubble.left,
            width: bubble.size,
            height: bubble.size,
            animationDuration: bubble.duration,
            animationDelay: bubble.delay,
          }}
        />
      ))}
    </div>
  );
}

export default BubbleBackground;
