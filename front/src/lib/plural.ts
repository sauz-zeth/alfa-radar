export function pluralRu(count: number, forms: [string, string, string]): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  const word =
    mod100 >= 11 && mod100 <= 14
      ? forms[2]
      : mod10 === 1
        ? forms[0]
        : mod10 >= 2 && mod10 <= 4
          ? forms[1]
          : forms[2];
  return `${count} ${word}`;
}

export function channelCountLabel(count: number): string {
  return pluralRu(count, ["канал", "канала", "каналов"]);
}
