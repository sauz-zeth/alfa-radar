const GLYPHS: Record<string, string[]> = {
  "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
  "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
  "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
  "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
  "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
  "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
};

const DOT_RADIUS = 0.22;

type DotDigitsProps = {
  value: number;
};

export function DotDigits({ value }: DotDigitsProps) {
  const digits = String(Math.round(value)).split("");
  const fallback = GLYPHS["0"]!;

  return (
    <span className="dot-digits" role="img" aria-label={`${Math.round(value)} из 100`}>
      {digits.map((digit, index) => (
        <svg key={`${digit}-${index}`} className="dot-digits__glyph" viewBox="0 0 5 7" aria-hidden="true">
          {(GLYPHS[digit] ?? fallback).map((row, y) =>
            [...row].map((cell, x) =>
              cell === "1" ? (
                <circle key={`${x}-${y}`} cx={x + 0.5} cy={y + 0.5} r={DOT_RADIUS} />
              ) : null,
            ),
          )}
        </svg>
      ))}
    </span>
  );
}
