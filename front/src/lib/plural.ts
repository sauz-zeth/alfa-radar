export function channelCountLabel(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  const word =
    mod100 >= 11 && mod100 <= 14
      ? "каналов"
      : mod10 === 1
        ? "канал"
        : mod10 >= 2 && mod10 <= 4
          ? "канала"
          : "каналов";
  return `${count} ${word}`;
}
