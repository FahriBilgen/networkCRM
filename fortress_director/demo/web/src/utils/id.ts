const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";

export function nanoid(size = 8): string {
  let id = "";
  for (let i = 0; i < size; i += 1) {
    const index = Math.floor(Math.random() * alphabet.length);
    id += alphabet[index];
  }
  return id;
}
