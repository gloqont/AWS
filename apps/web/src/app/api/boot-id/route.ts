const BOOT_ID = Date.now().toString();

export function GET() {
  return Response.json({ bootId: BOOT_ID });
}
