import { readFileSync, statSync, unlinkSync } from "node:fs";

const noStore = { "Cache-Control": "no-store" };

export async function POST(request: Request) {
  const ticket = process.env.STUDIO_REVIEW_TICKET;
  const passwordFile = process.env.STUDIO_REVIEW_PASSWORD_FILE;
  if (
    process.env.NODE_ENV !== "development" ||
    !ticket ||
    !passwordFile ||
    request.headers.get("origin") !== "http://127.0.0.1:3014"
  ) {
    return new Response(null, { status: 404, headers: noStore });
  }

  const nonce = request.headers.get("x-studio-review-nonce");
  try {
    if (
      !nonce ||
      Date.now() - statSync(ticket).mtimeMs > 5 * 60 * 1000 ||
      nonce !== readFileSync(ticket, "utf8").trim()
    ) {
      return new Response(null, { status: 404, headers: noStore });
    }
    unlinkSync(ticket);
    const password = readFileSync(passwordFile, "utf8").trim();
    return Response.json({ email: "meta-read-qa@example.com", password }, { headers: noStore });
  } catch {
    return new Response(null, { status: 404, headers: noStore });
  }
}
